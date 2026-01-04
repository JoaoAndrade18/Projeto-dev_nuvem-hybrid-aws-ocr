import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from decimal import Decimal

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .settings import (
    AWS_REGION,
    DYNAMODB_TABLE,
    MINIO_ENDPOINT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    MINIO_BUCKET,
)
from .db import Base, engine, SessionLocal
from .models import Job, JobFile
from .tasks import process_ocr_file

app = FastAPI(title="Hybrid OCR API")
Base.metadata.create_all(bind=engine)

_s3_config = Config(signature_version="s3v4")

s3 = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    region_name=AWS_REGION,
    config=_s3_config,
)

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
jobs_table = dynamodb.Table(DYNAMODB_TABLE)

def db_session() -> Session:
    return SessionLocal()

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def ensure_minio_bucket() -> None:
    try:
        s3.head_bucket(Bucket=MINIO_BUCKET)
    except ClientError:
        s3.create_bucket(Bucket=MINIO_BUCKET)

def presigned_get_url(object_key: str, expires: int = 3600) -> str:
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": MINIO_BUCKET, "Key": object_key},
        ExpiresIn=expires,
    )

def _to_plain(v: Any) -> Any:
    if isinstance(v, Decimal):
        return int(v) if v % 1 == 0 else float(v)
    return v

def _normalize_job_item(item: Dict[str, Any]) -> Dict[str, Any]:
    out = {k: _to_plain(v) for k, v in (item or {}).items()}
    out.setdefault("job_id", "")
    out.setdefault("name", "Sem nome")
    out.setdefault("status", "UNKNOWN")
    out.setdefault("created_at", None)
    out.setdefault("queued_at", None)
    out.setdefault("started_at", None)
    out.setdefault("finished_at", None)
    out["total_files"] = int(out.get("total_files") or 0)
    out["processed_files"] = int(out.get("processed_files") or 0)
    out["failed_files"] = int(out.get("failed_files") or 0)
    return out

@app.on_event("startup")
def _startup():
    ensure_minio_bucket()

class CreateJobReq(BaseModel):
    name: str = "Sem nome"

class CreateJobResp(BaseModel):
    job_id: str
    name: str
    status: str
    created_at: str

class JobListItem(BaseModel):
    job_id: str
    name: str
    status: str
    created_at: Optional[str] = None
    queued_at: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    total_files: int = 0
    processed_files: int = 0
    failed_files: int = 0

class JobFileItem(BaseModel):
    file_id: str
    filename: str
    object_key: str
    status: str
    queued_at: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    ocr_text: Optional[str] = None
    error_message: Optional[str] = None
    url: Optional[str] = None

class JobDetailResp(BaseModel):
    job: JobListItem
    files: List[JobFileItem]

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/jobs", response_model=CreateJobResp)
def create_job(payload: CreateJobReq):
    job_uuid = uuid.uuid4()
    created_at = utc_now()

    db = db_session()
    try:
        job = Job(
            job_id=job_uuid,
            name=payload.name,
            status="CREATED",
            created_at=created_at,
            total_files=0,
            processed_files=0,
            failed_files=0,
        )
        db.add(job)
        db.commit()
    finally:
        db.close()

    jobs_table.put_item(
        Item={
            "job_id": str(job_uuid),
            "name": payload.name,
            "status": "CREATED",
            "created_at": created_at.isoformat(),
            "total_files": 0,
            "processed_files": 0,
            "failed_files": 0,
        }
    )

    return {
        "job_id": str(job_uuid),
        "name": payload.name,
        "status": "CREATED",
        "created_at": created_at.isoformat(),
    }

@app.post("/jobs/{job_id}/files")
async def add_files(job_id: str, files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(400, "Nenhum arquivo enviado.")

    job_item = jobs_table.get_item(Key={"job_id": job_id}).get("Item")
    if not job_item:
        raise HTTPException(404, "Job não encontrado.")

    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(400, "job_id inválido.")

    now_iso = utc_now().isoformat()
    jobs_table.update_item(
        Key={"job_id": job_id},
        UpdateExpression=(
            "SET #s = if_not_exists(#s, :queued), "
            "queued_at = if_not_exists(queued_at, :qa), "
            "updated_at = :ua "
            "ADD total_files :n"
        ),
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":queued": "QUEUED", ":qa": now_iso, ":ua": now_iso, ":n": len(files)},
    )

    created = []
    for f in files:
        content = await f.read()
        if not content:
            continue

        file_uuid = uuid.uuid4()
        object_key = f"{job_id}/{file_uuid}/{f.filename}"
        s3.put_object(Bucket=MINIO_BUCKET, Key=object_key, Body=content)
        queued_at = utc_now()
        db = db_session()
        try:
            jf = JobFile(
                file_id=file_uuid,
                job_id=job_uuid,
                filename=f.filename,
                object_key=object_key,
                status="QUEUED",
                queued_at=queued_at,
            )
            db.add(jf)

            job = db.get(Job, job_uuid)
            if job:
                job.total_files = int(job.total_files or 0) + 1
                if job.status in ("CREATED", None):
                    job.status = "QUEUED"
                if job.queued_at is None:
                    job.queued_at = queued_at

            db.commit()
        finally:
            db.close()

        process_ocr_file.delay(job_id, str(file_uuid), object_key)
        created.append({"file_id": str(file_uuid), "filename": f.filename, "object_key": object_key})

    if not created:
        raise HTTPException(400, "Todos os arquivos estavam vazios.")

    return {"job_id": job_id, "files_created": created, "count": len(created)}

@app.get("/jobs", response_model=List[JobListItem])
def list_jobs():
    resp = jobs_table.scan()
    items = resp.get("Items", []) or []
    normalized = [_normalize_job_item(it) for it in items]
    normalized.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return [JobListItem(**it).model_dump() for it in normalized]

@app.get("/jobs/{job_id}", response_model=JobDetailResp)
def get_job(job_id: str):
    job_item = jobs_table.get_item(Key={"job_id": job_id}).get("Item")
    if not job_item:
        raise HTTPException(404, "Job não encontrado.")

    job_item_norm = _normalize_job_item(job_item)

    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(400, "job_id inválido.")

    db = db_session()
    try:
        rows = db.execute(select(JobFile).where(JobFile.job_id == job_uuid)).scalars().all()
        files_out: List[JobFileItem] = []
        for r in rows:
            files_out.append(
                JobFileItem(
                    file_id=str(r.file_id),
                    filename=r.filename,
                    object_key=r.object_key,
                    status=r.status,
                    queued_at=r.queued_at.isoformat() if r.queued_at else None,
                    started_at=r.started_at.isoformat() if r.started_at else None,
                    finished_at=r.finished_at.isoformat() if r.finished_at else None,
                    ocr_text=r.ocr_text,
                    error_message=r.error_message,
                    url=presigned_get_url(r.object_key),
                )
            )
    finally:
        db.close()

    return JobDetailResp(job=JobListItem(**job_item_norm), files=files_out)
