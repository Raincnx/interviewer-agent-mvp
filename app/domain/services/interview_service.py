from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.schemas.interview import (
    FinishInterviewResponse,
    InterviewCreateRequest,
    InterviewCreateResponse,
    InterviewDetailResponse,
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
        self.db = db
        self.settings = settings
        self.provider = provider
        self.interview_repo = interview_repo
        self.turn_repo = turn_repo
        self.scoring_service = scoring_service
        self.report_service = report_service
        self.prompts_dir = Path(__file__).resolve().parents[2] / "prompts"

    def create_interview(self, payload: InterviewCreateRequest) -> InterviewCreateResponse:
        interview = self.interview_repo.create(
            target_role=payload.target_role,
            level=payload.level,
            round_type=payload.round_type,
            status="running",
            provider=self.settings.llm_provider,
            model_name=self.settings.llm_model,
            max_turns=self.settings.max_turns,
        )

        opening_question = self._generate_opening_question(payload)
        self.turn_repo.create(
            interview_id=interview.id,
            turn_index=1,
            question_text=opening_question,
            question_kind="opening",
        )
        self.db.commit()

        return InterviewCreateResponse(
            interview_id=interview.id,
            status=interview.status,
            question=opening_question,
            max_turns=interview.max_turns,
            provider=interview.provider,
            model_name=interview.model_name,
        )

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
            max_turns=interview.max_turns,
            created_at=interview.created_at,
            updated_at=interview.updated_at,
            turns=turns,
            report=report,
        )

    def reply(self, interview_id: str, answer: str) -> ReplyResponse:
        interview = self.interview_repo.get_by_id(interview_id)
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")

        if interview.status == "finished":
            report = self.report_service.get_report(interview_id)
            if not report:
                raise HTTPException(status_code=404, detail="Report not found")
            return ReplyResponse(done=True, report=report)

        latest_turn = self.turn_repo.get_latest_turn(interview_id)
        if latest_turn is None:
            raise HTTPException(status_code=400, detail="No active turn found")

        if latest_turn.candidate_answer:
            raise HTTPException(status_code=400, detail="Latest turn already answered")

        self.turn_repo.set_answer(latest_turn, answer)
        self.db.flush()

        answered_count = self.turn_repo.count_answered_turns(interview_id)
        if answered_count >= interview.max_turns:
            return self.finish(interview_id)

        transcript = self._build_transcript(interview_id)
        next_question = self._generate_followup_question(
            transcript=transcript,
            target_role=interview.target_role,
            level=interview.level,
            round_type=interview.round_type,
        )

        self.turn_repo.create(
            interview_id=interview_id,
            turn_index=answered_count + 1,
            question_text=next_question,
            question_kind="followup",
            followup_reason="Continue probing based on the previous answer.",
        )
        self.db.commit()

        return ReplyResponse(
            done=False,
            question=next_question,
            remaining_turns=interview.max_turns - answered_count,
        )

    def finish(self, interview_id: str) -> FinishInterviewResponse:
        interview = self.interview_repo.get_by_id(interview_id)
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")

        existing_report = self.report_service.get_report(interview_id)
        if existing_report:
            self.interview_repo.update_status(interview, "finished")
            self.db.commit()
            return FinishInterviewResponse(done=True, report=existing_report)

        transcript = self._build_transcript(interview_id)
        payload = self.scoring_service.generate_report_payload(
            transcript=transcript,
            meta={
                "target_role": interview.target_role,
                "level": interview.level,
                "round_type": interview.round_type,
            },
        )
        report = self.report_service.create_report(interview_id, payload)
        self.interview_repo.update_status(interview, "finished")
        self.db.commit()
        return FinishInterviewResponse(done=True, report=report)

    def get_report(self, interview_id: str):
        return self.report_service.get_report(interview_id)

    def _generate_opening_question(self, payload: InterviewCreateRequest) -> str:
        system_prompt = (self.prompts_dir / "interviewer_system.txt").read_text(encoding="utf-8")
        user_prompt = f"""
Start a new interview for the following candidate profile.
Role: {payload.target_role}
Level: {payload.level}
Round type: {payload.round_type}

Ask the first interview question only. Do not include a greeting or any explanation.
        """.strip()
        return self.provider.generate_text(system_prompt=system_prompt, user_prompt=user_prompt)

    def _generate_followup_question(
        self,
        transcript: str,
        target_role: str,
        level: str,
        round_type: str,
    ) -> str:
        system_prompt = (self.prompts_dir / "interviewer_system.txt").read_text(encoding="utf-8")
        user_prompt = f"""
Role: {target_role}
Level: {level}
Round type: {round_type}

Here is the full interview transcript so far:
{transcript}

Ask the next interviewer question only. Prefer a follow-up based on the candidate's latest answer.
If the latest answer is already complete, move to the next relevant question.
        """.strip()
        return self.provider.generate_text(system_prompt=system_prompt, user_prompt=user_prompt)

    def _build_transcript(self, interview_id: str) -> str:
        turns = self.turn_repo.list_by_interview_id(interview_id)
        lines: list[str] = []
        for turn in turns:
            lines.append(f"Interviewer: {turn.question_text}")
            if turn.candidate_answer:
                lines.append(f"Candidate: {turn.candidate_answer}")
        return "\n".join(lines)
