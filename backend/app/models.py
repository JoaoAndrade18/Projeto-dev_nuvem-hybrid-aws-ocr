from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
from .db import Base

class OcrResult(Base):
    __tablename__ = "ocr_results"
    job_id = Column(String, primary_key=True, index=True)
    object_key = Column(String, nullable=False)   # caminho do arquivo no MinIO
    text = Column(Text, nullable=True)
    status = Column(String, nullable=False)       # QUEUED/PROCESSING/DONE/FAILED
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
