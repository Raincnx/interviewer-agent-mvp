from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.question_bank_item import QuestionBankItem


class QuestionBankRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        title: str,
        category: str,
        difficulty: str,
        content: str,
        standard_answer: str,
        follow_up_suggestions_json: str,
        tags_json: str,
        source_url: str | None,
        source_title: str | None,
        fingerprint: str,
    ) -> QuestionBankItem:
        item = QuestionBankItem(
            title=title,
            category=category,
            difficulty=difficulty,
            content=content,
            standard_answer=standard_answer,
            follow_up_suggestions_json=follow_up_suggestions_json,
            tags_json=tags_json,
            source_url=source_url,
            source_title=source_title,
            fingerprint=fingerprint,
        )
        self.db.add(item)
        self.db.flush()
        return item

    def get_by_id(self, item_id: str) -> QuestionBankItem | None:
        return self.db.query(QuestionBankItem).filter(QuestionBankItem.id == item_id).first()

    def get_by_fingerprint(self, fingerprint: str) -> QuestionBankItem | None:
        return self.db.query(QuestionBankItem).filter(QuestionBankItem.fingerprint == fingerprint).first()

    def list_all(self) -> list[QuestionBankItem]:
        return self.db.query(QuestionBankItem).order_by(QuestionBankItem.created_at.desc()).all()
