from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.domain.schemas.report import ReportRead
from app.infra.repositories.report_repo import ReportRepository


class ReportService:
    def __init__(self, db: Session, report_repo: ReportRepository) -> None:
        self.db = db
        self.report_repo = report_repo

    def create_report(self, interview_id: str, payload: dict) -> ReportRead:
        report = self.report_repo.create(
            interview_id=interview_id,
            overall_score=int(payload["overall_score"]),
            dimension_scores_json=json.dumps(payload["dimension_scores"], ensure_ascii=False),
            strengths_json=json.dumps(payload["strengths"], ensure_ascii=False),
            weaknesses_json=json.dumps(payload["weaknesses"], ensure_ascii=False),
            next_actions_json=json.dumps(payload["next_actions"], ensure_ascii=False),
            hire_recommendation=payload["hire_recommendation"],
            raw_llm_output=json.dumps(payload, ensure_ascii=False),
        )
        self.db.commit()
        self.db.refresh(report)
        return self.to_read_model(report)

    def get_report(self, interview_id: str) -> ReportRead | None:
        report = self.report_repo.get_by_interview_id(interview_id)
        if not report:
            return None
        return self.to_read_model(report)

    @staticmethod
    def to_read_model(report) -> ReportRead:
        raw = json.loads(report.raw_llm_output)
        return ReportRead(
            id=report.id,
            interview_id=report.interview_id,
            overall_score=report.overall_score,
            dimension_scores=raw["dimension_scores"],
            strengths=raw["strengths"],
            weaknesses=raw["weaknesses"],
            next_actions=raw["next_actions"],
            hire_recommendation=raw["hire_recommendation"],
            created_at=report.created_at,
        )
