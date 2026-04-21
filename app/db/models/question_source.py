import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class QuestionSource(Base):
    __tablename__ = "question_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), index=True)
    source_type: Mapped[str] = mapped_column(String(32), default="web")
    base_url: Mapped[str | None] = mapped_column(String(1024), nullable=True, unique=True)
    language: Mapped[str] = mapped_column(String(32), default="zh-CN")
    crawl_strategy: Mapped[str] = mapped_column(String(32), default="http")
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    crawl_jobs = relationship("QuestionCollectionJob", back_populates="source")
    raw_documents = relationship("RawQuestionDocument", back_populates="source")
