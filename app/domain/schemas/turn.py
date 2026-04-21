from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TurnRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    turn_index: int
    question_text: str
    question_kind: str
    followup_reason: str | None = None
    candidate_answer: str | None = None
    created_at: datetime
