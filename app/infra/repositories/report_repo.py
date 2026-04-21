from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.report import Report


class ReportRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        interview_id: str,
        overall_score: int,
        dimension_scores_json: str,
        strengths_json: str,
        weaknesses_json: str,
        next_actions_json: str,
        hire_recommendation: str,
        raw_llm_output: str,
    ) -> Report:
        report = Report(
            interview_id=interview_id,
            overall_score=overall_score,
            dimension_scores_json=dimension_scores_json,
            strengths_json=strengths_json,
            weaknesses_json=weaknesses_json,
            next_actions_json=next_actions_json,
            hire_recommendation=hire_recommendation,
            raw_llm_output=raw_llm_output,
        )
        self.db.add(report)
        self.db.flush()
        return report

    def get_by_interview_id(self, interview_id: str) -> Report | None:
        return self.db.query(Report).filter(Report.interview_id == interview_id).first()
