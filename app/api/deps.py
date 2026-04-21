from typing import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.runtime_settings import RuntimeSettingsStore
from app.db.session import get_db
from app.domain.schemas.runtime import RuntimeConfigRead
from app.domain.services.interview_service import InterviewService
from app.domain.services.question_bank_service import QuestionBankService
from app.domain.services.report_service import ReportService
from app.domain.services.scoring_service import ScoringService
from app.infra.llm.registry import get_llm_provider
from app.infra.repositories.question_bank_repo import QuestionBankRepository
from app.infra.repositories.interview_repo import InterviewRepository
from app.infra.repositories.report_repo import ReportRepository
from app.infra.repositories.turn_repo import TurnRepository

runtime_settings_store = RuntimeSettingsStore(get_settings())


def get_runtime_settings_store() -> RuntimeSettingsStore:
    return runtime_settings_store


def get_runtime_settings(store: RuntimeSettingsStore = Depends(get_runtime_settings_store)):
    return store.get()


def get_runtime_config_read(
    settings=Depends(get_runtime_settings),
) -> RuntimeConfigRead:
    return RuntimeConfigRead(
        provider=settings.llm_provider,
        model_name=settings.llm_model,
        prompt_version=settings.prompt_version,
        scoring_backend=settings.scoring_backend,
        api_key_configured=bool(settings.gemini_api_key or settings.openai_api_key),
    )


def get_interview_service(
    db: Session = Depends(get_db),
    settings=Depends(get_runtime_settings),
) -> InterviewService:
    provider = get_llm_provider(settings)

    return InterviewService(
        db=db,
        settings=settings,
        provider=provider,
        interview_repo=InterviewRepository(db),
        turn_repo=TurnRepository(db),
        scoring_service=ScoringService(settings=settings, provider=provider),
        report_service=ReportService(db=db, report_repo=ReportRepository(db)),
    )


def get_question_bank_service(
    db: Session = Depends(get_db),
    settings=Depends(get_runtime_settings),
) -> QuestionBankService:
    return QuestionBankService(
        db=db,
        settings=settings,
        repo=QuestionBankRepository(db),
    )
