import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class QuestionOccurrence(Base):
    __tablename__ = "question_occurrences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id: Mapped[str] = mapped_column(String(36), ForeignKey("structured_questions.id"), index=True)
    raw_document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("raw_question_documents.id"), nullable=True, index=True)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    question = relationship("StructuredQuestion", back_populates="occurrences")
