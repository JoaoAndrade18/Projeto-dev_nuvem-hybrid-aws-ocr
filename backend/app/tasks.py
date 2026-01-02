import io
import boto3
from celery import Celery
import easyocr
from sqlalchemy.orm import Session

from .settings import (
    AWS_REGION, DYNAMODB_TABLE,
    MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET,
    REDIS_URL
)
from .db import SessionLocal
from .models import OcrResult

celery_app = Celery("worker", broker=REDIS_URL, backend=REDIS_URL)

s3 = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
)
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
jobs_table = dynamodb.Table(DYNAMODB_TABLE)

_reader = None

def get_reader():
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(["pt", "en"], gpu=True)
    return _reader

@celery_app.task(name="process_ocr")
def process_ocr(job_id: str, object_key: str):
    db: Session = SessionLocal()
    try:
        jobs_table.update_item(
            Key={"job_id": job_id},
            UpdateExpression="SET #s = :s",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "PROCESSING"},
        )

        obj = s3.get_object(Bucket=MINIO_BUCKET, Key=object_key)
        content = obj["Body"].read()

        reader = get_reader()
        result = reader.readtext(content)
        text = "\n".join([r[1] for r in result]) if result else ""

        row = db.get(OcrResult, job_id)
        if row:
            row.text = text
            row.status = "DONE"
        else:
            row = OcrResult(job_id=job_id, object_key=object_key, text=text, status="DONE")
            db.add(row)
        db.commit()

        jobs_table.update_item(
            Key={"job_id": job_id},
            UpdateExpression="SET #s = :s",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "DONE"},
        )

        return {"job_id": job_id, "status": "DONE"}

    except Exception as e:
        db.rollback()
        jobs_table.update_item(
            Key={"job_id": job_id},
            UpdateExpression="SET #s = :s, error = :e",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "FAILED", ":e": str(e)[:900]},
        )
        raise
    finally:
        db.close()
