from __future__ import annotations

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


def main() -> int:
    settings = Settings()
    db = build_session(settings)
    try:
        service = QuestionBankService(db=db, settings=settings, repo=QuestionBankRepository(db))
        result = service.bootstrap_default_sources()
        print(f"已创建来源: {result.created_count}")
        print(f"已更新来源: {result.updated_count}")
        print(f"当前注册来源总数: {len(result.sources)}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
