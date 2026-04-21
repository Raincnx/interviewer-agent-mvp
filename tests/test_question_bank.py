from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_question_bank_service
from app.db.base import Base
from app.db.session import get_db
from app.domain.schemas.question_bank import InterviewQuestion
from app.domain.services.question_bank_service import QuestionBankService
from app.infra.repositories.question_bank_repo import QuestionBankRepository
from app.main import app
from app.core.config import Settings


class StubExtractor:
    def extract(self, **kwargs):
        return [
            InterviewQuestion(
                title="如何设计线程安全的 LRU 缓存？",
                category="系统设计",
                difficulty="中等",
                content="请你设计一个支持线程安全的 LRU 缓存，并解释关键数据结构选择。",
                standard_answer="核心是哈希表加双向链表，并说明并发控制策略。",
                follow_up_suggestions=[
                    "如果读多写少，你会如何优化锁？",
                    "如果缓存容量非常大，会有哪些额外问题？",
                ],
                tags=["缓存", "并发"],
            ),
            InterviewQuestion(
                title="如何设计线程安全的 LRU 缓存？",
                category="系统设计",
                difficulty="中等",
                content="请你设计一个支持线程安全的 LRU 缓存，并解释关键数据结构选择。",
                standard_answer="核心是哈希表加双向链表，并说明并发控制策略。",
                follow_up_suggestions=[
                    "如果读多写少，你会如何优化锁？",
                    "如果缓存容量非常大，会有哪些额外问题？",
                ],
                tags=["缓存", "并发"],
            ),
        ]


def build_question_service(db: Session) -> QuestionBankService:
    return QuestionBankService(
        db=db,
        settings=Settings(llm_provider="mock", llm_model="mock-interviewer-v1"),
        repo=QuestionBankRepository(db),
        extractor=StubExtractor(),
    )


@pytest.fixture
def client(tmp_path) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "question-bank.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    testing_session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        class_=Session,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    def override_question_service() -> QuestionBankService:
        db = testing_session_local()
        try:
            return build_question_service(db)
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_question_bank_service] = override_question_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_collect_question_bank_from_markdown_dedupes_items(client: TestClient) -> None:
    response = client.post(
        "/api/question-bank/collect",
        json={
            "raw_markdown": "# 示例题库\n\n请设计线程安全的 LRU 缓存。",
            "source_title": "示例题库",
            "category_hint": "系统设计",
        },
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["extracted_count"] == 2
    assert payload["inserted_count"] == 1
    assert payload["skipped_count"] == 1
    assert payload["questions"][0]["category"] == "系统设计"
    assert payload["questions"][0]["source_title"] == "示例题库"

    list_response = client.get("/api/question-bank")
    assert list_response.status_code == 200

    items = list_response.json()
    assert len(items) == 1
    assert items[0]["title"] == "如何设计线程安全的 LRU 缓存？"
    assert "缓存" in items[0]["tags"]
