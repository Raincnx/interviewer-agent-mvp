import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Turn(Base):
    __tablename__ = "turns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    interview_id: Mapped[str] = mapped_column(String(36), ForeignKey("interviews.id"), index=True)
    turn_index: Mapped[int] = mapped_column(Integer)
    question_text: Mapped[str] = mapped_column(Text)
    question_kind: Mapped[str] = mapped_column(String(32), default="question")
    followup_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    candidate_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    knowledge_refs_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resume_refs_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    interview = relationship("Interview", back_populates="turns")
