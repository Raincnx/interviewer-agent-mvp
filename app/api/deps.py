from typing import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.domain.services.interview_service import InterviewService
from app.domain.services.report_service import ReportService
from app.domain.services.scoring_service import ScoringService
from app.infra.llm.registry import get_llm_provider
from app.infra.repositories.interview_repo import InterviewRepository
from app.infra.repositories.report_repo import ReportRepository
from app.infra.repositories.turn_repo import TurnRepository


def get_interview_service(db: Session = Depends(get_db)) -> InterviewService:
    settings = get_settings()
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
