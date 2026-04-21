import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid.uuid4()))
    interview_id: Mapped[str] = mapped_column(ForeignKey("interviews.id"), unique=True, index=True)
    overall_score: Mapped[int] = mapped_column(Integer)
    dimension_scores_json: Mapped[str] = mapped_column(Text)
    strengths_json: Mapped[str] = mapped_column(Text)
    weaknesses_json: Mapped[str] = mapped_column(Text)
    next_actions_json: Mapped[str] = mapped_column(Text)
    hire_recommendation: Mapped[str] = mapped_column(String(32))
    raw_llm_output: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    interview = relationship("Interview", back_populates="report")
