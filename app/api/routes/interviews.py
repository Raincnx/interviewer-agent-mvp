from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_interview_service
from app.domain.schemas.interview import (
    FinishInterviewResponse,
    InterviewCreateRequest,
    InterviewCreateResponse,
    InterviewDetailResponse,
    ReplyRequest,
    ReplyResponse,
)
from app.domain.services.interview_service import InterviewService

router = APIRouter()


@router.post("", response_model=InterviewCreateResponse)
def create_interview(
    payload: InterviewCreateRequest,
    service: InterviewService = Depends(get_interview_service),
) -> InterviewCreateResponse:
    return service.create_interview(payload)


@router.get("/{interview_id}", response_model=InterviewDetailResponse)
def get_interview(
    interview_id: str,
    service: InterviewService = Depends(get_interview_service),
) -> InterviewDetailResponse:
    interview = service.get_interview_detail(interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    return interview


@router.post("/{interview_id}/reply", response_model=ReplyResponse)
def reply(
    interview_id: str,
    payload: ReplyRequest,
    service: InterviewService = Depends(get_interview_service),
) -> ReplyResponse:
    return service.reply(interview_id=interview_id, answer=payload.answer)


@router.post("/{interview_id}/finish", response_model=FinishInterviewResponse)
def finish(
    interview_id: str,
    service: InterviewService = Depends(get_interview_service),
) -> FinishInterviewResponse:
    return service.finish(interview_id)
