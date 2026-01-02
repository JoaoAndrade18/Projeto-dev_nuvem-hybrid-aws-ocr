import uuid
import boto3
from fastapi import FastAPI, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from .settings import (
    AWS_REGION, DYNAMODB_TABLE,
    MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET,
)
from .db import Base, engine, SessionLocal
from .models import OcrResult
from .tasks import process_ocr

app = FastAPI(title="Hybrid OCR API")

Base.metadata.create_all(bind=engine)

s3 = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
)
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
jobs_table = dynamodb.Table(DYNAMODB_TABLE)

def db_session() -> Session:
    return SessionLocal()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/jobs")
async def create_job(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    object_key = f"{job_id}/{file.filename}"

    content = await file.read()
    if not content:
        raise HTTPException(400, "Arquivo vazio.")

    s3.put_object(Bucket=MINIO_BUCKET, Key=object_key, Body=content)

    jobs_table.put_item(Item={"job_id": job_id, "status": "QUEUED", "object_key": object_key})

    db = db_session()
    try:
        db.add(OcrResult(job_id=job_id, object_key=object_key, status="QUEUED", text=None))
        db.commit()
    finally:
        db.close()

    process_ocr.delay(job_id, object_key)

    return {"job_id": job_id, "status": "QUEUED"}

@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    db = db_session()
    try:
        row = db.get(OcrResult, job_id)
        if not row:
            raise HTTPException(404, "Job não encontrado.")
        return {
            "job_id": row.job_id,
            "status": row.status,
            "text": row.text,
            "object_key": row.object_key,
        }
    finally:
        db.close()
