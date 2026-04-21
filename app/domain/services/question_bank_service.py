from __future__ import annotations

import hashlib
import json

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.schemas.question_bank import (
    InterviewQuestion,
    QuestionBankItemRead,
    QuestionCollectRequest,
    QuestionCollectResponse,
)
from app.infra.question_bank.crawler import build_question_crawler
from app.infra.question_bank.extractor import QuestionCollectorExtractor
from app.infra.repositories.question_bank_repo import QuestionBankRepository


class QuestionBankService:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        repo: QuestionBankRepository,
        extractor: QuestionCollectorExtractor | None = None,
    ) -> None:
        self.db = db
        self.settings = settings
        self.repo = repo
        self.extractor = extractor or QuestionCollectorExtractor(settings)

    def collect(self, payload: QuestionCollectRequest) -> QuestionCollectResponse:
        if payload.raw_markdown:
            markdown = payload.raw_markdown
            source_url = payload.source_url
            source_title = payload.source_title
        else:
            crawler = build_question_crawler(self.settings, payload.use_firecrawl)
            document = crawler.fetch(payload.source_url or "")
            markdown = document.markdown
            source_url = document.source_url
            source_title = payload.source_title or document.source_title

        extracted_questions = self.extractor.extract(
            markdown=markdown,
            source_url=source_url,
            source_title=source_title,
            category_hint=payload.category_hint,
            max_questions=payload.max_questions,
        )

        inserted: list[QuestionBankItemRead] = []
        skipped_count = 0

        for question in extracted_questions:
            normalized = self._normalize_question(
                question=question,
                source_url=source_url,
                source_title=source_title,
                category_hint=payload.category_hint,
            )
            fingerprint = self._build_fingerprint(normalized)
            existing = self.repo.get_by_fingerprint(fingerprint)
            if existing:
                skipped_count += 1
                inserted.append(self.to_read_model(existing))
                continue

            created = self.repo.create(
                title=normalized.title,
                category=normalized.category,
                difficulty=normalized.difficulty,
                content=normalized.content,
                standard_answer=normalized.standard_answer,
                follow_up_suggestions_json=json.dumps(normalized.follow_up_suggestions, ensure_ascii=False),
                tags_json=json.dumps(normalized.tags, ensure_ascii=False),
                source_url=normalized.source_url,
                source_title=normalized.source_title,
                fingerprint=fingerprint,
            )
            inserted.append(self.to_read_model(created))

        self.db.commit()

        return QuestionCollectResponse(
            source_url=source_url,
            source_title=source_title,
            fetched_chars=len(markdown),
            extracted_count=len(extracted_questions),
            inserted_count=len(extracted_questions) - skipped_count,
            skipped_count=skipped_count,
            questions=inserted,
        )

    def list_questions(self) -> list[QuestionBankItemRead]:
        return [self.to_read_model(item) for item in self.repo.list_all()]

    def get_question(self, item_id: str) -> QuestionBankItemRead | None:
        item = self.repo.get_by_id(item_id)
        if item is None:
            return None
        return self.to_read_model(item)

    def _normalize_question(
        self,
        *,
        question: InterviewQuestion,
        source_url: str | None,
        source_title: str | None,
        category_hint: str | None,
    ) -> InterviewQuestion:
        tags = [tag.strip() for tag in question.tags if tag.strip()]
        if question.category.strip():
            tags.append(question.category.strip())
        if category_hint and category_hint.strip():
            tags.append(category_hint.strip())
        if question.difficulty.strip():
            tags.append(question.difficulty.strip())

        unique_tags = list(dict.fromkeys(tags))

        return InterviewQuestion(
            title=question.title.strip(),
            category=(question.category or category_hint or "通用技术面试").strip(),
            difficulty=(question.difficulty or "中等").strip(),
            content=question.content.strip(),
            standard_answer=question.standard_answer.strip(),
            follow_up_suggestions=[item.strip() for item in question.follow_up_suggestions if item.strip()],
            tags=unique_tags,
            source_url=question.source_url or source_url,
            source_title=question.source_title or source_title,
        )

    @staticmethod
    def _build_fingerprint(question: InterviewQuestion) -> str:
        raw = "|".join(
            [
                question.title.strip().lower(),
                question.category.strip().lower(),
                question.content.strip().lower(),
            ]
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def to_read_model(item) -> QuestionBankItemRead:
        return QuestionBankItemRead(
            id=item.id,
            title=item.title,
            category=item.category,
            difficulty=item.difficulty,
            content=item.content,
            standard_answer=item.standard_answer,
            follow_up_suggestions=json.loads(item.follow_up_suggestions_json),
            tags=json.loads(item.tags_json),
            source_url=item.source_url,
            source_title=item.source_title,
            fingerprint=item.fingerprint,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
