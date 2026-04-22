from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import MetaData, Table, create_engine, delete, inspect, select
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.base import Base
from app.db.models import (  # noqa: F401
    Interview,
    QuestionBankItem,
    QuestionCollectionJob,
    QuestionOccurrence,
    QuestionSource,
    RawQuestionDocument,
    Report,
    StructuredQuestion,
    Turn,
)


TABLE_ORDER = [
    "interviews",
    "question_bank_items",
    "question_sources",
    "question_collection_jobs",
    "raw_question_documents",
    "structured_questions",
    "question_occurrences",
    "turns",
    "reports",
]


def build_engine(url: str) -> Engine:
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, future=True, connect_args=connect_args)


def copy_table(source_engine: Engine, target_engine: Engine, table_name: str) -> int:
    source_inspector = inspect(source_engine)
    if table_name not in source_inspector.get_table_names():
        return 0

    source_metadata = MetaData()
    target_metadata = MetaData()
    source_table = Table(table_name, source_metadata, autoload_with=source_engine)
    target_table = Table(table_name, target_metadata, autoload_with=target_engine)
    target_columns = {column.name: column for column in target_table.columns}

    with source_engine.connect() as source_conn, target_engine.begin() as target_conn:
        rows = source_conn.execute(select(source_table)).mappings().all()
        if not rows:
            return 0
        payload = [
            {
                key: _normalize_value(value, target_columns[key])
                for key, value in row.items()
                if key in target_columns
            }
            for row in rows
        ]
        target_conn.execute(target_table.insert(), payload)
        return len(payload)


def _normalize_value(value, column):
    if value is None:
        return None
    try:
        python_type = column.type.python_type
    except Exception:
        return value

    if python_type is datetime and isinstance(value, str):
        return datetime.fromisoformat(value)
    return value


def truncate_target_tables(target_engine: Engine) -> None:
    metadata = MetaData()
    metadata.reflect(bind=target_engine)
    with target_engine.begin() as connection:
        for table_name in reversed(TABLE_ORDER):
            if table_name in metadata.tables:
                connection.execute(delete(metadata.tables[table_name]))


def main() -> int:
    parser = argparse.ArgumentParser(description="将 SQLite 数据迁移到 PostgreSQL 或其他 SQLAlchemy 目标库。")
    parser.add_argument("--source-url", default="sqlite:///./app.db", help="源数据库 URL，默认当前项目 app.db")
    parser.add_argument("--target-url", required=True, help="目标数据库 URL，例如 postgresql+psycopg://postgres:postgres@localhost:5432/interviewer_agent")
    parser.add_argument("--truncate-target", action="store_true", help="迁移前清空目标库中已有数据")
    args = parser.parse_args()

    source_engine = build_engine(args.source_url)
    target_engine = build_engine(args.target_url)

    Base.metadata.create_all(bind=target_engine)
    if args.truncate_target:
        truncate_target_tables(target_engine)

    copied_counts: dict[str, int] = {}
    for table_name in TABLE_ORDER:
        copied_counts[table_name] = copy_table(source_engine, target_engine, table_name)

    print("迁移完成：")
    for table_name in TABLE_ORDER:
        print(f"- {table_name}: {copied_counts[table_name]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
