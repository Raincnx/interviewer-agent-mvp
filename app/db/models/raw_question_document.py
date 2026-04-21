import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RawQuestionDocument(Base):
    __tablename__ = "raw_question_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("question_sources.id"), nullable=True, index=True)
    job_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("question_collection_jobs.id"), nullable=True, index=True)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True, index=True)
    source_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    markdown: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    document_version: Mapped[int] = mapped_column(Integer, default=1)
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    source = relationship("QuestionSource", back_populates="raw_documents")
    job = relationship("QuestionCollectionJob", back_populates="raw_documents")
    extracted_questions = relationship("StructuredQuestion", back_populates="raw_document")
