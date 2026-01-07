import io
import uuid
from datetime import datetime, timezone
import fcntl
import os

import boto3
from botocore.exceptions import ClientError
from celery import Celery
import easyocr
from sqlalchemy.orm import Session

from .settings import (
    AWS_REGION,
    DYNAMODB_TABLE,
    MINIO_ENDPOINT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    MINIO_BUCKET,
    RABBITMQ_URL,
)
from .db import SessionLocal
from .models import Job, JobFile  

celery_app = Celery("worker", broker=RABBITMQ_URL, backend="rpc://")

s3 = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    region_name=AWS_REGION,
)
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
jobs_table = dynamodb.Table(DYNAMODB_TABLE)

_reader = None
def utc_now() -> datetime:
    return datetime.now(timezone.utc)
def utc_now_iso() -> str:
    return utc_now().isoformat()
def ensure_minio_bucket():
    try:
        s3.head_bucket(Bucket=MINIO_BUCKET)
    except ClientError:
        s3.create_bucket(Bucket=MINIO_BUCKET)

_reader = None
def get_reader():
    global _reader
    if _reader is not None:
        return _reader

    os.makedirs("/root/.EasyOCR", exist_ok=True)

    lock_path = "/root/.EasyOCR/.init.lock"
    with open(lock_path, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        if _reader is None:
            _reader = easyocr.Reader(["pt", "en"], gpu=True)
        fcntl.flock(f, fcntl.LOCK_UN)

    return _reader


def _update_dynamodb_job(job_id: str, job: Job):
    """
    Espelha o estado agregado do Job no DynamoDB.
    Observação: DynamoDB não aceita None; então só seta finished_at se existir.
    """
    expr_names = {"#s": "status"}
    expr_vals = {
        ":s": job.status,
        ":p": int(job.processed_files or 0),
        ":f": int(job.failed_files or 0),
        ":t": int(job.total_files or 0),
        ":st": (job.started_at.isoformat() if job.started_at else utc_now_iso()),
    }

    update_expr = "SET #s=:s, processed_files=:p, failed_files=:f, total_files=:t, started_at=if_not_exists(started_at,:st)"

    if job.finished_at:
        update_expr += ", finished_at=:ft"
        expr_vals[":ft"] = job.finished_at.isoformat()

    jobs_table.update_item(
        Key={"job_id": job_id},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_vals,
    )


@celery_app.task(name="process_ocr_file")
def process_ocr_file(job_id: str, file_id: str, object_key: str):
    """
    Processa OCR de 1 arquivo:
    - Atualiza JobFile (Postgres): PROCESSING -> DONE/FAILED + timestamps + texto/erro
    - Atualiza Job (Postgres): processed_files/failed_files + status + started/finished
    - Espelha agregados no DynamoDB (status/progresso/timestamps)
    """
    ensure_minio_bucket()

    try:
        job_uuid = uuid.UUID(job_id)
        file_uuid = uuid.UUID(file_id)
    except ValueError:
        return {"job_id": job_id, "file_id": file_id, "status": "FAILED", "error": "invalid uuid"}

    started_at = utc_now()

    db: Session = SessionLocal()
    try:
        job: Job | None = db.get(Job, job_uuid)
        jf: JobFile | None = db.get(JobFile, file_uuid)

        if not job or not jf:
            return {"job_id": job_id, "file_id": file_id, "status": "FAILED", "error": "job/file not found"}

        jf.status = "PROCESSING"
        jf.started_at = started_at

        if job.started_at is None:
            job.started_at = started_at
        job.status = "PROCESSING"

        db.commit()

        jobs_table.update_item(
            Key={"job_id": job_id},
            UpdateExpression="SET #s=:s, started_at=if_not_exists(started_at,:st)",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "PROCESSING", ":st": started_at.isoformat()},
        )
        obj = s3.get_object(Bucket=MINIO_BUCKET, Key=object_key)
        content = obj["Body"].read()

        reader = get_reader()
        try:
            from PIL import Image
            import numpy as np
            img = Image.open(io.BytesIO(content)).convert("RGB")
            img_np = np.array(img)
            result = reader.readtext(img_np)
        except Exception:
            result = reader.readtext(content)

        text = "\n".join([r[1] for r in result]) if result else ""
        finished_at = utc_now()

        jf.status = "DONE"
        jf.ocr_text = text
        jf.finished_at = finished_at

        job.processed_files = int(job.processed_files or 0) + 1

        if int(job.total_files or 0) > 0 and int(job.processed_files or 0) >= int(job.total_files or 0):
            job.finished_at = finished_at
            job.status = "DONE" if int(job.failed_files or 0) == 0 else "PARTIAL"
        else:
            job.status = "PROCESSING"

        db.commit()
        _update_dynamodb_job(job_id, job)

        return {"job_id": job_id, "file_id": file_id, "status": jf.status}

    except Exception as e:
        db.rollback()

        finished_at = utc_now()
        err = str(e)[:900]
        try:
            job: Job | None = db.get(Job, job_uuid)
            jf: JobFile | None = db.get(JobFile, file_uuid)
            if jf:
                jf.status = "FAILED"
                jf.error_message = err
                jf.finished_at = finished_at

            if job:
                job.processed_files = int(job.processed_files or 0) + 1
                job.failed_files = int(job.failed_files or 0) + 1

                if int(job.total_files or 0) > 0 and int(job.processed_files or 0) >= int(job.total_files or 0):
                    job.finished_at = finished_at
                else:
                    job.status = "PROCESSING"

            db.commit()

            if job:
                _update_dynamodb_job(job_id, job)

        except Exception:
            db.rollback()
            jobs_table.update_item(
                Key={"job_id": job_id},
                UpdateExpression="SET #s=:s, error=:e",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":s": "FAILED", ":e": err},
            )
        raise

    finally:
        db.close()
