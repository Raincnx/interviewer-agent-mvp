from pydantic import BaseModel, Field


class InterviewScorePayload(BaseModel):
    """Structured evaluation report returned by the interviewer agent."""

    overall_score: int = Field(ge=0, le=100)
    dimension_scores: dict[str, int]
    strengths: list[str]
    weaknesses: list[str]
    next_actions: list[str]
    hire_recommendation: str
