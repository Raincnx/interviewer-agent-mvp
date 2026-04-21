from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_question_bank_service
from app.domain.schemas.question_bank import (
    QuestionBankItemRead,
    QuestionCollectRequest,
    QuestionCollectResponse,
)
from app.domain.services.question_bank_service import QuestionBankService

router = APIRouter(prefix="/api/question-bank", tags=["question-bank"])


@router.get("", response_model=list[QuestionBankItemRead])
def list_questions(
    service: QuestionBankService = Depends(get_question_bank_service),
) -> list[QuestionBankItemRead]:
    return service.list_questions()


@router.get("/{item_id}", response_model=QuestionBankItemRead)
def get_question(
    item_id: str,
    service: QuestionBankService = Depends(get_question_bank_service),
) -> QuestionBankItemRead:
    item = service.get_question(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return item


@router.post("/collect", response_model=QuestionCollectResponse)
def collect_questions(
    payload: QuestionCollectRequest,
    service: QuestionBankService = Depends(get_question_bank_service),
) -> QuestionCollectResponse:
    try:
        return service.collect(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
