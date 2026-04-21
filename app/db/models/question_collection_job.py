import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class QuestionCollectionJob(Base):
    __tablename__ = "question_collection_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("question_sources.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="running", index=True)
    trigger_mode: Mapped[str] = mapped_column(String(32), default="manual")
    request_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category_hint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    use_firecrawl: Mapped[str] = mapped_column(String(8), default="false")
    requested_max_questions: Mapped[int] = mapped_column(Integer, default=20)
    fetched_chars: Mapped[int] = mapped_column(Integer, default=0)
    extracted_count: Mapped[int] = mapped_column(Integer, default=0)
    inserted_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    versioned_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    source = relationship("QuestionSource", back_populates="crawl_jobs")
    raw_documents = relationship("RawQuestionDocument", back_populates="job")
