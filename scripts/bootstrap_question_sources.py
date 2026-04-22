from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import Settings
from app.db.base import Base
from app.domain.services.question_bank_service import QuestionBankService
from app.infra.repositories.question_bank_repo import QuestionBankRepository


def build_session(settings: Settings) -> Session:
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    engine = create_engine(settings.database_url, future=True, connect_args=connect_args)
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        class_=Session,
    )
    return session_local()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="批量注册默认题库来源。")
    parser.add_argument(
        "--job-track",
        action="append",
        dest="job_tracks",
        help="按岗位方向筛选来源，可重复传入，如 ai-agent / backend / ml-engineer。",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = Settings()
    db = build_session(settings)
    try:
        service = QuestionBankService(db=db, settings=settings, repo=QuestionBankRepository(db))
        result = service.bootstrap_default_sources(args.job_tracks)
        print(f"已创建来源: {result.created_count}")
        print(f"已更新来源: {result.updated_count}")
        print(f"当前返回来源总数: {len(result.sources)}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
