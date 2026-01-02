import os

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "ocr_jobs")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "images")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://ocr:ocr@postgres:5432/ocr")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
