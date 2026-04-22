import hashlib
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import (  # noqa: F401
    QuestionBankItem,
    QuestionOccurrence,
    QuestionSource,
    StructuredQuestion,
    interview,
    question_bank_item,
    question_collection_job,
    question_occurrence,
    question_source,
    raw_question_document,
    report,
    structured_question,
    turn,
)
from app.db.session import engine


def ensure_runtime_schema() -> None:
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    if "interviews" not in table_names:
        return

    statements: list[str] = []
    interview_columns = {column["name"] for column in inspector.get_columns("interviews")}

    if "prompt_version" not in interview_columns:
        statements.append("ALTER TABLE interviews ADD COLUMN prompt_version VARCHAR(64) NOT NULL DEFAULT 'v1'")
    if "resume_filename" not in interview_columns:
        statements.append("ALTER TABLE interviews ADD COLUMN resume_filename VARCHAR(255)")
    if "resume_text" not in interview_columns:
        statements.append("ALTER TABLE interviews ADD COLUMN resume_text TEXT")

    if "turns" in table_names:
        turn_columns = {column["name"] for column in inspector.get_columns("turns")}
        if "knowledge_refs_json" not in turn_columns:
            statements.append("ALTER TABLE turns ADD COLUMN knowledge_refs_json TEXT")
        if "resume_refs_json" not in turn_columns:
            statements.append("ALTER TABLE turns ADD COLUMN resume_refs_json TEXT")
        if "updated_at" not in turn_columns:
            statements.append("ALTER TABLE turns ADD COLUMN updated_at DATETIME")

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def backfill_legacy_question_bank() -> int:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "question_bank_items" not in table_names or "structured_questions" not in table_names:
        return 0

    migrated = 0
    with Session(engine) as session:
        legacy_items = session.query(QuestionBankItem).order_by(QuestionBankItem.created_at.asc()).all()
        for item in legacy_items:
            canonical_hash = hashlib.sha256(
                "|".join([item.title.strip().lower(), item.category.strip().lower()]).encode("utf-8")
            ).hexdigest()
            content_hash = hashlib.sha256(
                json.dumps(
                    {
                        "title": item.title,
                        "category": item.category,
                        "difficulty": item.difficulty,
                        "content": item.content,
                        "standard_answer": item.standard_answer,
                        "follow_up_suggestions": json.loads(item.follow_up_suggestions_json or "[]"),
                        "tags": json.loads(item.tags_json or "[]"),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest()

            existing = (
                session.query(StructuredQuestion)
                .filter(
                    StructuredQuestion.canonical_hash == canonical_hash,
                    StructuredQuestion.is_active.is_(True),
                )
                .first()
            )
            if existing is not None:
                continue

            source = None
            if item.source_url:
                source = session.query(QuestionSource).filter(QuestionSource.base_url == item.source_url).first()
                if source is None:
                    source = QuestionSource(
                        name=item.source_title or item.title,
                        source_type="legacy",
                        base_url=item.source_url,
                        language="zh-CN",
                        crawl_strategy="legacy",
                        config_json=None,
                        enabled=True,
                    )
                    session.add(source)
                    session.flush()

            question = StructuredQuestion(
                raw_document_id=None,
                title=item.title,
                category=item.category,
                difficulty=item.difficulty,
                content=item.content,
                standard_answer=item.standard_answer,
                follow_up_suggestions_json=item.follow_up_suggestions_json,
                tags_json=item.tags_json,
                source_url=item.source_url,
                source_title=item.source_title,
                canonical_hash=canonical_hash,
                content_hash=content_hash,
                version=1,
                is_active=True,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            session.add(question)
            session.flush()

            occurrence = QuestionOccurrence(
                question_id=question.id,
                raw_document_id=None,
                source_url=item.source_url,
                source_title=item.source_title,
                created_at=item.created_at,
            )
            session.add(occurrence)
            migrated += 1

        if migrated:
            session.commit()
        else:
            session.rollback()
    return migrated


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema()
    backfill_legacy_question_bank()
    yield
