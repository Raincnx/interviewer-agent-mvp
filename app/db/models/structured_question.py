import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StructuredQuestion(Base):
    __tablename__ = "structured_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    raw_document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("raw_question_documents.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(64), index=True)
    difficulty: Mapped[str] = mapped_column(String(32), index=True)
    content: Mapped[str] = mapped_column(Text)
    standard_answer: Mapped[str] = mapped_column(Text)
    follow_up_suggestions_json: Mapped[str] = mapped_column(Text)
    tags_json: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True, index=True)
    source_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    canonical_hash: Mapped[str] = mapped_column(String(64), index=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    raw_document = relationship("RawQuestionDocument", back_populates="extracted_questions")
    occurrences = relationship("QuestionOccurrence", back_populates="question", cascade="all, delete-orphan")
