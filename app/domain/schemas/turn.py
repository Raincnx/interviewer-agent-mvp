from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TurnRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    turn_index: int
    question_text: str
    question_kind: str
    followup_reason: Optional[str] = None
    candidate_answer: Optional[str] = None
    created_at: datetime
