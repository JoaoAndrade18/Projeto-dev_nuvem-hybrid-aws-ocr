import uuid
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .db import Base


class Job(Base):
    __tablename__ = "jobs"

    job_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name = Column(String(200), nullable=False, default="Sem nome")
    status = Column(String(30), nullable=False, default="CREATED")

    created_at = Column(DateTime(timezone=True), nullable=False)
    queued_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    total_files = Column(Integer, nullable=False, default=0)
    processed_files = Column(Integer, nullable=False, default=0)
    failed_files = Column(Integer, nullable=False, default=0)

    files = relationship(
        "JobFile",
        back_populates="job",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

class JobFile(Base):
    __tablename__ = "job_files"
    file_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jobs.job_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    filename = Column(String(255), nullable=False)
    object_key = Column(String(512), nullable=False)

    status = Column(String(30), nullable=False, default="QUEUED")

    queued_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    ocr_text = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    job = relationship("Job", back_populates="files")
