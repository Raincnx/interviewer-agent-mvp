from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.domain.schemas.report import ReportRead
from app.domain.schemas.turn import TurnRead


class InterviewCreateRequest(BaseModel):
    target_role: str = Field(default="后端工程师")
    level: str = Field(default="中级")
    round_type: str = Field(default="项目深挖")


class InterviewCreateResponse(BaseModel):
    interview_id: str
    status: str
    question: str
    max_turns: int
    provider: str
    model_name: str
    prompt_version: str


class InterviewHistoryItem(BaseModel):
    id: str
    target_role: str
    level: str
    round_type: str
    status: str
    provider: str
    model_name: str
    prompt_version: str
    max_turns: int
    answered_turns: int
    created_at: datetime
    updated_at: datetime
    overall_score: Optional[int] = None
    hire_recommendation: Optional[str] = None


class ReplyRequest(BaseModel):
    answer: str = Field(min_length=1)


class ReplyResponse(BaseModel):
    done: bool
    question: Optional[str] = None
    report: Optional[ReportRead] = None
    remaining_turns: Optional[int] = None


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
    prompt_version: str
    max_turns: int
    created_at: datetime
    updated_at: datetime
    turns: list[TurnRead] = []
    report: Optional[ReportRead] = None
