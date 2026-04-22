from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_question_bank_service
from app.domain.schemas.question_bank import (
    QuestionBankItemRead,
    QuestionBatchCollectResponse,
    QuestionCollectRequest,
    QuestionCollectResponse,
    QuestionCollectionJobRead,
    QuestionSourceBootstrapResponse,
    QuestionSourceCreateRequest,
    QuestionSourceRead,
    RawQuestionDocumentRead,
)
from app.domain.services.question_bank_service import QuestionBankService

router = APIRouter(prefix="/api/question-bank", tags=["question-bank"])


@router.get("", response_model=list[QuestionBankItemRead])
def list_questions(
    service: QuestionBankService = Depends(get_question_bank_service),
) -> list[QuestionBankItemRead]:
    return service.list_questions()


@router.get("/sources", response_model=list[QuestionSourceRead])
def list_sources(
    service: QuestionBankService = Depends(get_question_bank_service),
) -> list[QuestionSourceRead]:
    return service.list_sources()


@router.post("/sources", response_model=QuestionSourceRead)
def create_source(
    payload: QuestionSourceCreateRequest,
    service: QuestionBankService = Depends(get_question_bank_service),
) -> QuestionSourceRead:
    return service.create_source(payload)


@router.post("/sources/bootstrap", response_model=QuestionSourceBootstrapResponse)
def bootstrap_sources(
    job_track: list[str] | None = None,
    service: QuestionBankService = Depends(get_question_bank_service),
) -> QuestionSourceBootstrapResponse:
    return service.bootstrap_default_sources(job_track)


@router.get("/jobs", response_model=list[QuestionCollectionJobRead])
def list_jobs(
    service: QuestionBankService = Depends(get_question_bank_service),
) -> list[QuestionCollectionJobRead]:
    return service.list_jobs()


@router.get("/raw-documents", response_model=list[RawQuestionDocumentRead])
def list_raw_documents(
    service: QuestionBankService = Depends(get_question_bank_service),
) -> list[RawQuestionDocumentRead]:
    return service.list_raw_documents()


@router.post("/collect", response_model=QuestionCollectResponse)
def collect_questions(
    payload: QuestionCollectRequest,
    service: QuestionBankService = Depends(get_question_bank_service),
) -> QuestionCollectResponse:
    try:
        return service.collect(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/collect/enabled", response_model=QuestionBatchCollectResponse)
def collect_enabled_sources(
    job_track: list[str] | None = None,
    service: QuestionBankService = Depends(get_question_bank_service),
) -> QuestionBatchCollectResponse:
    return service.collect_enabled_sources(job_track)


@router.get("/{item_id}", response_model=QuestionBankItemRead)
def get_question(
    item_id: str,
    service: QuestionBankService = Depends(get_question_bank_service),
) -> QuestionBankItemRead:
    item = service.get_question(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return item
