from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from app.db.models.question_collection_job import QuestionCollectionJob
from app.db.models.question_occurrence import QuestionOccurrence
from app.db.models.question_source import QuestionSource
from app.db.models.raw_question_document import RawQuestionDocument
from app.db.models.structured_question import StructuredQuestion


class QuestionBankRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create_source(
        self,
        *,
        name: str,
        source_type: str = "web",
        base_url: str | None = None,
        language: str = "zh-CN",
        crawl_strategy: str = "http",
        enabled: bool = True,
        config_json: str | None = None,
    ) -> QuestionSource:
        source = None
        if base_url:
            source = self.db.query(QuestionSource).filter(QuestionSource.base_url == base_url).first()
        if source is None:
            source = QuestionSource(
                name=name,
                source_type=source_type,
                base_url=base_url,
                language=language,
                crawl_strategy=crawl_strategy,
                enabled=enabled,
                config_json=config_json,
            )
            self.db.add(source)
            self.db.flush()
            return source

        source.name = name or source.name
        source.source_type = source_type or source.source_type
        source.language = language or source.language
        source.crawl_strategy = crawl_strategy or source.crawl_strategy
        source.enabled = enabled
        if config_json is not None:
            source.config_json = config_json
        self.db.add(source)
        self.db.flush()
        return source

    def list_sources(self) -> list[QuestionSource]:
        return self.db.query(QuestionSource).order_by(QuestionSource.created_at.desc()).all()

    def create_job(
        self,
        *,
        source_id: str | None,
        request_url: str | None,
        source_title: str | None,
        category_hint: str | None,
        max_questions: int,
        use_firecrawl: bool,
    ) -> QuestionCollectionJob:
        job = QuestionCollectionJob(
            source_id=source_id,
            status="running",
            trigger_mode="manual",
            request_url=request_url,
            source_title=source_title,
            category_hint=category_hint,
            use_firecrawl="true" if use_firecrawl else "false",
            requested_max_questions=max_questions,
        )
        self.db.add(job)
        self.db.flush()
        return job

    def complete_job(
        self,
        job: QuestionCollectionJob,
        *,
        fetched_chars: int,
        extracted_count: int,
        inserted_count: int,
        skipped_count: int,
        versioned_count: int,
    ) -> QuestionCollectionJob:
        job.status = "completed"
        job.fetched_chars = fetched_chars
        job.extracted_count = extracted_count
        job.inserted_count = inserted_count
        job.skipped_count = skipped_count
        job.versioned_count = versioned_count
        job.finished_at = datetime.utcnow()
        self.db.add(job)
        self.db.flush()
        return job

    def fail_job(self, job: QuestionCollectionJob, error_message: str) -> QuestionCollectionJob:
        job.status = "failed"
        job.error_message = error_message
        job.finished_at = datetime.utcnow()
        self.db.add(job)
        self.db.flush()
        return job

    def list_jobs(self) -> list[QuestionCollectionJob]:
        return self.db.query(QuestionCollectionJob).order_by(QuestionCollectionJob.started_at.desc()).all()

    def get_latest_raw_document_by_url(self, source_url: str | None) -> RawQuestionDocument | None:
        if not source_url:
            return None
        return (
            self.db.query(RawQuestionDocument)
            .filter(RawQuestionDocument.source_url == source_url, RawQuestionDocument.is_latest.is_(True))
            .first()
        )

    def create_raw_document(
        self,
        *,
        source_id: str | None,
        job_id: str | None,
        source_url: str | None,
        source_title: str | None,
        markdown: str,
        content_hash: str,
        document_version: int,
    ) -> RawQuestionDocument:
        if source_url:
            (
                self.db.query(RawQuestionDocument)
                .filter(RawQuestionDocument.source_url == source_url, RawQuestionDocument.is_latest.is_(True))
                .update({"is_latest": False}, synchronize_session=False)
            )

        document = RawQuestionDocument(
            source_id=source_id,
            job_id=job_id,
            source_url=source_url,
            source_title=source_title,
            markdown=markdown,
            content_hash=content_hash,
            document_version=document_version,
            is_latest=True,
        )
        self.db.add(document)
        self.db.flush()
        return document

    def list_raw_documents(self) -> list[RawQuestionDocument]:
        return self.db.query(RawQuestionDocument).order_by(RawQuestionDocument.fetched_at.desc()).all()

    def get_active_question_by_canonical_hash(self, canonical_hash: str) -> StructuredQuestion | None:
        return (
            self.db.query(StructuredQuestion)
            .options(joinedload(StructuredQuestion.occurrences))
            .filter(
                StructuredQuestion.canonical_hash == canonical_hash,
                StructuredQuestion.is_active.is_(True),
            )
            .first()
        )

    def get_by_fingerprint(self, fingerprint: str) -> StructuredQuestion | None:
        return self.get_active_question_by_canonical_hash(fingerprint)

    def get_question_by_id(self, item_id: str) -> StructuredQuestion | None:
        return (
            self.db.query(StructuredQuestion)
            .options(joinedload(StructuredQuestion.occurrences))
            .filter(StructuredQuestion.id == item_id, StructuredQuestion.is_active.is_(True))
            .first()
        )

    def get_next_question_version(self, canonical_hash: str) -> int:
        latest = (
            self.db.query(StructuredQuestion)
            .filter(StructuredQuestion.canonical_hash == canonical_hash)
            .order_by(StructuredQuestion.version.desc())
            .first()
        )
        if latest is None:
            return 1
        return latest.version + 1

    def deactivate_active_question_versions(self, canonical_hash: str) -> None:
        (
            self.db.query(StructuredQuestion)
            .filter(StructuredQuestion.canonical_hash == canonical_hash, StructuredQuestion.is_active.is_(True))
            .update({"is_active": False}, synchronize_session=False)
        )

    def create_structured_question(
        self,
        *,
        raw_document_id: str | None,
        title: str,
        category: str,
        difficulty: str,
        content: str,
        standard_answer: str,
        follow_up_suggestions_json: str,
        tags_json: str,
        source_url: str | None,
        source_title: str | None,
        canonical_hash: str,
        content_hash: str,
        version: int,
    ) -> StructuredQuestion:
        question = StructuredQuestion(
            raw_document_id=raw_document_id,
            title=title,
            category=category,
            difficulty=difficulty,
            content=content,
            standard_answer=standard_answer,
            follow_up_suggestions_json=follow_up_suggestions_json,
            tags_json=tags_json,
            source_url=source_url,
            source_title=source_title,
            canonical_hash=canonical_hash,
            content_hash=content_hash,
            version=version,
            is_active=True,
        )
        self.db.add(question)
        self.db.flush()
        return question

    def ensure_occurrence(
        self,
        *,
        question_id: str,
        raw_document_id: str | None,
        source_url: str | None,
        source_title: str | None,
    ) -> QuestionOccurrence:
        query = self.db.query(QuestionOccurrence).filter(QuestionOccurrence.question_id == question_id)
        if raw_document_id:
            query = query.filter(QuestionOccurrence.raw_document_id == raw_document_id)
        else:
            query = query.filter(QuestionOccurrence.raw_document_id.is_(None), QuestionOccurrence.source_url == source_url)

        occurrence = query.first()
        if occurrence is not None:
            return occurrence

        occurrence = QuestionOccurrence(
            question_id=question_id,
            raw_document_id=raw_document_id,
            source_url=source_url,
            source_title=source_title,
        )
        self.db.add(occurrence)
        self.db.flush()
        return occurrence

    def list_all(self) -> list[StructuredQuestion]:
        return (
            self.db.query(StructuredQuestion)
            .options(joinedload(StructuredQuestion.occurrences))
            .filter(StructuredQuestion.is_active.is_(True))
            .order_by(StructuredQuestion.created_at.desc())
            .all()
        )

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
    ) -> StructuredQuestion:
        existing = self.get_active_question_by_canonical_hash(fingerprint)
        if existing is not None:
            return existing

        question = self.create_structured_question(
            raw_document_id=None,
            title=title,
            category=category,
            difficulty=difficulty,
            content=content,
            standard_answer=standard_answer,
            follow_up_suggestions_json=follow_up_suggestions_json,
            tags_json=tags_json,
            source_url=source_url,
            source_title=source_title,
            canonical_hash=fingerprint,
            content_hash=fingerprint,
            version=1,
        )
        self.ensure_occurrence(
            question_id=question.id,
            raw_document_id=None,
            source_url=source_url,
            source_title=source_title,
        )
        return question
