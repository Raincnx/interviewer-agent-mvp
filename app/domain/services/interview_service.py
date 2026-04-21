from __future__ import annotations

from sqlalchemy.orm import Session

from app.agent.loop import InterviewerAgent
from app.agent.tools import InterviewAgentToolkit
from app.core.config import Settings
from app.domain.schemas.interview import (
    FinishInterviewResponse,
    InterviewCreateRequest,
    InterviewCreateResponse,
    InterviewDetailResponse,
    InterviewHistoryItem,
    ReplyResponse,
)
from app.domain.schemas.turn import TurnRead
from app.domain.services.report_service import ReportService
from app.domain.services.scoring_service import ScoringService
from app.infra.llm.base import BaseLLMProvider
from app.infra.repositories.interview_repo import InterviewRepository
from app.infra.repositories.turn_repo import TurnRepository


class InterviewService:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        provider: BaseLLMProvider,
        interview_repo: InterviewRepository,
        turn_repo: TurnRepository,
        scoring_service: ScoringService,
        report_service: ReportService,
    ) -> None:
        self.interview_repo = interview_repo
        self.report_service = report_service
        self.agent = InterviewerAgent(
            InterviewAgentToolkit.build(
                db=db,
                settings=settings,
                provider=provider,
                interview_repo=interview_repo,
                turn_repo=turn_repo,
                scoring_service=scoring_service,
                report_service=report_service,
            )
        )

    def create_interview(self, payload: InterviewCreateRequest) -> InterviewCreateResponse:
        return self.agent.start_interview(payload)

    def list_interviews(self) -> list[InterviewHistoryItem]:
        interviews = self.interview_repo.list_all()
        items: list[InterviewHistoryItem] = []
        for interview in interviews:
            answered_turns = sum(1 for turn in interview.turns if turn.candidate_answer)
            items.append(
                InterviewHistoryItem(
                    id=interview.id,
                    target_role=interview.target_role,
                    level=interview.level,
                    round_type=interview.round_type,
                    status=interview.status,
                    provider=interview.provider,
                    model_name=interview.model_name,
                    prompt_version=interview.prompt_version,
                    max_turns=interview.max_turns,
                    answered_turns=answered_turns,
                    created_at=interview.created_at,
                    updated_at=interview.updated_at,
                    overall_score=interview.report.overall_score if interview.report else None,
                    hire_recommendation=interview.report.hire_recommendation if interview.report else None,
                )
            )
        return items

    def get_interview_detail(self, interview_id: str) -> InterviewDetailResponse | None:
        interview = self.interview_repo.get_by_id(interview_id)
        if not interview:
            return None

        report = self.report_service.get_report(interview_id)
        turns = [
            TurnRead.model_validate(turn)
            for turn in sorted(interview.turns, key=lambda item: item.turn_index)
        ]

        return InterviewDetailResponse(
            id=interview.id,
            target_role=interview.target_role,
            level=interview.level,
            round_type=interview.round_type,
            status=interview.status,
            provider=interview.provider,
            model_name=interview.model_name,
            prompt_version=interview.prompt_version,
            max_turns=interview.max_turns,
            created_at=interview.created_at,
            updated_at=interview.updated_at,
            turns=turns,
            report=report,
        )

    def reply(self, interview_id: str, answer: str) -> ReplyResponse:
        return self.agent.handle_reply(interview_id, answer)

    def finish(self, interview_id: str) -> FinishInterviewResponse:
        return self.agent.finish_interview(interview_id)

    def get_report(self, interview_id: str):
        return self.report_service.get_report(interview_id)
