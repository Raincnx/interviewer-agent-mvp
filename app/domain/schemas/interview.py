from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.schemas.report import ReportRead
from app.domain.schemas.turn import TurnRead


class InterviewCreateRequest(BaseModel):
    target_role: str = Field(default="后端开发")
    level: str = Field(default="校招")
    round_type: str = Field(default="项目面")


class InterviewCreateResponse(BaseModel):
    interview_id: str
    status: str
    question: str
    max_turns: int
    provider: str
    model_name: str


class ReplyRequest(BaseModel):
    answer: str = Field(min_length=1)


class ReplyResponse(BaseModel):
    done: bool
    question: str | None = None
    report: ReportRead | None = None
    remaining_turns: int | None = None


class FinishInterviewResponse(BaseModel):
    done: bool
    report: ReportRead


class InterviewDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    target_role: str
    level: str
    round_type: str
    status: str
    provider: str
    model_name: str
    max_turns: int
    created_at: datetime
    updated_at: datetime
    turns: list[TurnRead] = []
    report: ReportRead | None = None
