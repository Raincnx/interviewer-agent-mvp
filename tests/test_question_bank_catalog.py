import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.base import Base
from app.domain.services.question_bank_catalog import iter_source_catalog
from app.domain.services.question_bank_service import QuestionBankService
from app.infra.repositories.question_bank_repo import QuestionBankRepository


def test_iter_source_catalog_can_filter_by_job_track() -> None:
    backend_catalog = iter_source_catalog(["backend"])
    assert backend_catalog
    assert all(
        "backend" in (item.get("config") or {}).get("job_tracks", [])
        for item in backend_catalog
    )
    assert all(
        "ai-agent" not in (item.get("config") or {}).get("job_tracks", [])
        or "backend" in (item.get("config") or {}).get("job_tracks", [])
        for item in backend_catalog
    )


def test_bootstrap_default_sources_can_scope_by_job_track(tmp_path) -> None:
    db_path = tmp_path / "catalog-filter.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        class_=Session,
    )
    Base.metadata.create_all(bind=engine)

    db = session_local()
    try:
        service = QuestionBankService(
            db=db,
            settings=Settings(llm_provider="mock", llm_model="mock-interviewer-v1"),
            repo=QuestionBankRepository(db),
        )
        response = service.bootstrap_default_sources(["ml-engineer"])
        assert response.created_count >= 1
        assert response.sources

        raw_sources = QuestionBankRepository(db).list_sources()
        assert raw_sources
        for source in raw_sources:
            config = json.loads(source.config_json or "{}")
            assert "ml-engineer" in config.get("job_tracks", [])
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
