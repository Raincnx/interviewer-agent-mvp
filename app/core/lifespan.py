from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import inspect, text

from app.db.base import Base
from app.db.models import interview, question_bank_item, report, turn  # noqa: F401
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

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema()
    yield
