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
        max_turns: int,
    ) -> Interview:
        interview = Interview(
            target_role=target_role,
            level=level,
            round_type=round_type,
            status=status,
            provider=provider,
            model_name=model_name,
            max_turns=max_turns,
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

    def update_status(self, interview: Interview, status: str) -> Interview:
        interview.status = status
        self.db.add(interview)
        self.db.flush()
        return interview
