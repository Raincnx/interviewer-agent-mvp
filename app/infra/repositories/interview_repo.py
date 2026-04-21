from __future__ import annotations

from sqlalchemy.orm import Session, selectinload

from app.db.models.interview import Interview


class InterviewRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        target_role: str,
        level: str,
        round_type: str,
        status: str,
        provider: str,
        model_name: str,
        prompt_version: str,
        max_turns: int,
        resume_filename: str | None = None,
        resume_text: str | None = None,
    ) -> Interview:
        interview = Interview(
            target_role=target_role,
            level=level,
            round_type=round_type,
            status=status,
            provider=provider,
            model_name=model_name,
            prompt_version=prompt_version,
            max_turns=max_turns,
            resume_filename=resume_filename,
            resume_text=resume_text,
        )
        self.db.add(interview)
        self.db.flush()
        return interview

    def get_by_id(self, interview_id: str) -> Interview | None:
        return (
            self.db.query(Interview)
            .options(selectinload(Interview.turns), selectinload(Interview.report))
            .filter(Interview.id == interview_id)
            .first()
        )

    def list_all(self) -> list[Interview]:
        return (
            self.db.query(Interview)
            .options(selectinload(Interview.turns), selectinload(Interview.report))
            .order_by(Interview.created_at.desc())
            .all()
        )

    def update_status(self, interview: Interview, status: str) -> Interview:
        interview.status = status
        self.db.add(interview)
        self.db.flush()
        return interview
