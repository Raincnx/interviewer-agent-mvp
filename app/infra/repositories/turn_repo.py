from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.turn import Turn


class TurnRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        interview_id: str,
        turn_index: int,
        question_text: str,
        question_kind: str = "question",
        followup_reason: str | None = None,
        knowledge_refs_json: str | None = None,
        resume_refs_json: str | None = None,
    ) -> Turn:
        turn = Turn(
            interview_id=interview_id,
            turn_index=turn_index,
            question_text=question_text,
            question_kind=question_kind,
            followup_reason=followup_reason,
            knowledge_refs_json=knowledge_refs_json,
            resume_refs_json=resume_refs_json,
        )
        self.db.add(turn)
        self.db.flush()
        return turn

    def get_latest_turn(self, interview_id: str) -> Turn | None:
        return (
            self.db.query(Turn)
            .filter(Turn.interview_id == interview_id)
            .order_by(Turn.turn_index.desc())
            .first()
        )

    def set_answer(self, turn: Turn, answer: str) -> Turn:
        turn.candidate_answer = answer
        self.db.add(turn)
        self.db.flush()
        return turn

    def list_by_interview_id(self, interview_id: str) -> list[Turn]:
        return (
            self.db.query(Turn)
            .filter(Turn.interview_id == interview_id)
            .order_by(Turn.turn_index.asc())
            .all()
        )

    def count_answered_turns(self, interview_id: str) -> int:
        count = (
            self.db.query(func.count(Turn.id))
            .filter(Turn.interview_id == interview_id, Turn.candidate_answer.isnot(None))
            .scalar()
        )
        return int(count or 0)
