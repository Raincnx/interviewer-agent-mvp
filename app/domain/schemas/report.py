from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    interview_id: str
    overall_score: int
    dimension_scores: dict[str, int]
    strengths: list[str]
    weaknesses: list[str]
    next_actions: list[str]
    hire_recommendation: str
    created_at: datetime
