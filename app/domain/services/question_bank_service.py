from __future__ import annotations

import hashlib
import json
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.schemas.question_bank import (
    InterviewQuestion,
    QuestionBankItemRead,
    QuestionCollectRequest,
    QuestionCollectResponse,
    QuestionCollectionJobRead,
    QuestionSourceCreateRequest,
    QuestionSourceRead,
    RawQuestionDocumentRead,
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
        source = self._resolve_source(payload)
        job = self.repo.create_job(
            source_id=source.id if source else None,
            request_url=payload.source_url,
            source_title=payload.source_title,
            category_hint=payload.category_hint,
            max_questions=payload.max_questions,
            use_firecrawl=payload.use_firecrawl,
        )
        self.db.commit()

        try:
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

            if source_url and source is None:
                source = self._create_source_from_url(source_url=source_url, source_title=source_title, use_firecrawl=payload.use_firecrawl)
                job.source_id = source.id
                self.db.add(job)
                self.db.flush()

            raw_document = self._persist_raw_document(
                source=source,
                job_id=job.id,
                source_url=source_url,
                source_title=source_title,
                markdown=markdown,
            )

            extracted_questions = self.extractor.extract(
                markdown=markdown,
                source_url=source_url,
                source_title=source_title,
                category_hint=payload.category_hint,
                max_questions=payload.max_questions,
            )

            inserted: list[QuestionBankItemRead] = []
            skipped_count = 0
            versioned_count = 0
            inserted_count = 0

            for question in extracted_questions:
                normalized = self._normalize_question(
                    question=question,
                    source_url=source_url,
                    source_title=source_title,
                    category_hint=payload.category_hint,
                )
                canonical_hash = self._build_canonical_hash(normalized)
                content_hash = self._build_content_hash(normalized)
                existing = self.repo.get_active_question_by_canonical_hash(canonical_hash)

                if existing is not None and existing.content_hash == content_hash:
                    self.repo.ensure_occurrence(
                        question_id=existing.id,
                        raw_document_id=raw_document.id if raw_document else None,
                        source_url=normalized.source_url,
                        source_title=normalized.source_title,
                    )
                    skipped_count += 1
                    inserted.append(self.to_read_model(existing))
                    continue

                if existing is not None:
                    self.repo.deactivate_active_question_versions(canonical_hash)
                    version = self.repo.get_next_question_version(canonical_hash)
                    versioned_count += 1
                else:
                    version = 1

                created = self.repo.create_structured_question(
                    raw_document_id=raw_document.id if raw_document else None,
                    title=normalized.title,
                    category=normalized.category,
                    difficulty=normalized.difficulty,
                    content=normalized.content,
                    standard_answer=normalized.standard_answer,
                    follow_up_suggestions_json=json.dumps(normalized.follow_up_suggestions, ensure_ascii=False),
                    tags_json=json.dumps(normalized.tags, ensure_ascii=False),
                    source_url=normalized.source_url,
                    source_title=normalized.source_title,
                    canonical_hash=canonical_hash,
                    content_hash=content_hash,
                    version=version,
                )
                self.repo.ensure_occurrence(
                    question_id=created.id,
                    raw_document_id=raw_document.id if raw_document else None,
                    source_url=normalized.source_url,
                    source_title=normalized.source_title,
                )
                inserted.append(self.to_read_model(created))
                inserted_count += 1

            self.repo.complete_job(
                job,
                fetched_chars=len(markdown),
                extracted_count=len(extracted_questions),
                inserted_count=inserted_count,
                skipped_count=skipped_count,
                versioned_count=versioned_count,
            )
            self.db.commit()

            return QuestionCollectResponse(
                job_id=job.id,
                source_id=source.id if source else None,
                source_url=source_url,
                source_title=source_title,
                fetched_chars=len(markdown),
                extracted_count=len(extracted_questions),
                inserted_count=inserted_count,
                skipped_count=skipped_count,
                versioned_count=versioned_count,
                questions=inserted,
            )
        except Exception as exc:
            self.db.rollback()
            persisted_job = self.db.get(type(job), job.id)
            if persisted_job is not None:
                self.repo.fail_job(persisted_job, str(exc))
                self.db.commit()
            raise

    def create_source(self, payload: QuestionSourceCreateRequest) -> QuestionSourceRead:
        source = self.repo.get_or_create_source(
            name=payload.name,
            source_type=payload.source_type,
            base_url=payload.base_url,
            language=payload.language,
            crawl_strategy=payload.crawl_strategy,
            enabled=payload.enabled,
            config_json=payload.config_json,
        )
        self.db.commit()
        return QuestionSourceRead.model_validate(source)

    def list_sources(self) -> list[QuestionSourceRead]:
        return [QuestionSourceRead.model_validate(item) for item in self.repo.list_sources()]

    def list_jobs(self) -> list[QuestionCollectionJobRead]:
        return [QuestionCollectionJobRead.model_validate(item) for item in self.repo.list_jobs()]

    def list_raw_documents(self) -> list[RawQuestionDocumentRead]:
        return [RawQuestionDocumentRead.model_validate(item) for item in self.repo.list_raw_documents()]

    def list_questions(self) -> list[QuestionBankItemRead]:
        return [self.to_read_model(item) for item in self.repo.list_all()]

    def get_question(self, item_id: str) -> QuestionBankItemRead | None:
        item = self.repo.get_question_by_id(item_id)
        if item is None:
            return None
        return self.to_read_model(item)

    def _resolve_source(self, payload: QuestionCollectRequest):
        if payload.source_url:
            return self._create_source_from_url(
                source_url=payload.source_url,
                source_title=payload.source_title,
                use_firecrawl=payload.use_firecrawl,
            )
        if payload.source_title:
            return self.repo.get_or_create_source(
                name=payload.source_title,
                source_type="manual",
                base_url=None,
                language="zh-CN",
                crawl_strategy="manual",
                enabled=True,
                config_json=None,
            )
        return None

    def _create_source_from_url(self, *, source_url: str, source_title: str | None, use_firecrawl: bool):
        parsed = urlparse(source_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else source_url
        crawl_strategy = "firecrawl" if use_firecrawl else "http"
        name = source_title or parsed.netloc or source_url
        return self.repo.get_or_create_source(
            name=name,
            source_type="web",
            base_url=base_url,
            language="zh-CN",
            crawl_strategy=crawl_strategy,
            enabled=True,
            config_json=None,
        )

    def _persist_raw_document(
        self,
        *,
        source,
        job_id: str,
        source_url: str | None,
        source_title: str | None,
        markdown: str,
    ):
        content_hash = hashlib.sha256(markdown.strip().encode("utf-8")).hexdigest()
        existing = self.repo.get_latest_raw_document_by_url(source_url)
        if existing is not None and existing.content_hash == content_hash:
            existing.job_id = job_id
            self.db.add(existing)
            self.db.flush()
            return existing

        next_version = 1 if existing is None else existing.document_version + 1
        return self.repo.create_raw_document(
            source_id=source.id if source else None,
            job_id=job_id,
            source_url=source_url,
            source_title=source_title,
            markdown=markdown,
            content_hash=content_hash,
            document_version=next_version,
        )

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
    def _build_canonical_hash(question: InterviewQuestion) -> str:
        raw = "|".join(
            [
                question.title.strip().lower(),
                question.category.strip().lower(),
            ]
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _build_fingerprint(question: InterviewQuestion) -> str:
        return QuestionBankService._build_canonical_hash(question)

    @staticmethod
    def _build_content_hash(question: InterviewQuestion) -> str:
        raw = json.dumps(
            {
                "title": question.title,
                "category": question.category,
                "difficulty": question.difficulty,
                "content": question.content,
                "standard_answer": question.standard_answer,
                "follow_up_suggestions": question.follow_up_suggestions,
                "tags": question.tags,
            },
            ensure_ascii=False,
            sort_keys=True,
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
            canonical_hash=item.canonical_hash,
            content_hash=item.content_hash,
            version=item.version,
            occurrence_count=len(getattr(item, "occurrences", []) or []),
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
