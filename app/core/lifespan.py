from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import inspect, text

from app.db.base import Base
from app.db.models import interview, report, turn  # noqa: F401
from app.db.session import engine


def ensure_runtime_schema() -> None:
    inspector = inspect(engine)
    if "interviews" not in inspector.get_table_names():
        return

    interview_columns = {column["name"] for column in inspector.get_columns("interviews")}
    statements: list[str] = []

    if "prompt_version" not in interview_columns:
        statements.append("ALTER TABLE interviews ADD COLUMN prompt_version VARCHAR(64) NOT NULL DEFAULT 'v1'")

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
