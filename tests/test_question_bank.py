from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_question_bank_service
from app.core.config import Settings
from app.db.base import Base
from app.db.session import get_db
from app.domain.schemas.question_bank import InterviewQuestion
from app.domain.services.question_bank_service import QuestionBankService
from app.infra.repositories.question_bank_repo import QuestionBankRepository
from app.main import app


class StubExtractor:
    def __init__(self) -> None:
        self.calls = 0

    def extract(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
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

        return [
            InterviewQuestion(
                title="如何设计线程安全的 LRU 缓存？",
                category="系统设计",
                difficulty="困难",
                content="请你设计一个支持线程安全与热点隔离的 LRU 缓存，并解释锁粒度取舍。",
                standard_answer="除了哈希表和双向链表，还要说明分段锁、热点 key 与扩展策略。",
                follow_up_suggestions=[
                    "如果要支持 TTL，你会怎么扩展？",
                ],
                tags=["缓存", "并发", "高并发"],
            )
        ]


def build_question_service(db: Session, extractor: StubExtractor) -> QuestionBankService:
    return QuestionBankService(
        db=db,
        settings=Settings(llm_provider="mock", llm_model="mock-interviewer-v1"),
        repo=QuestionBankRepository(db),
        extractor=extractor,
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

    extractor = StubExtractor()

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    def override_question_service() -> QuestionBankService:
        db = testing_session_local()
        try:
            return build_question_service(db, extractor)
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_question_bank_service] = override_question_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_collect_question_bank_persists_source_job_document_and_dedupes(client: TestClient) -> None:
    response = client.post(
        "/api/question-bank/collect",
        json={
            "raw_markdown": "# 示例题库\n\n请设计线程安全的 LRU 缓存。",
            "source_title": "示例题库",
            "category_hint": "系统设计",
            "source_url": "https://example.com/lru",
        },
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["job_id"]
    assert payload["source_id"]
    assert payload["extracted_count"] == 2
    assert payload["inserted_count"] == 1
    assert payload["skipped_count"] == 1
    assert payload["versioned_count"] == 0
    assert payload["questions"][0]["category"] == "系统设计"
    assert payload["questions"][0]["source_title"] == "示例题库"
    assert payload["questions"][0]["occurrence_count"] == 1

    list_response = client.get("/api/question-bank")
    assert list_response.status_code == 200
    items = list_response.json()
    assert len(items) == 1
    assert items[0]["title"] == "如何设计线程安全的 LRU 缓存？"
    assert "缓存" in items[0]["tags"]
    assert items[0]["version"] == 1

    source_response = client.get("/api/question-bank/sources")
    assert source_response.status_code == 200
    assert source_response.json()[0]["name"] == "示例题库"

    job_response = client.get("/api/question-bank/jobs")
    assert job_response.status_code == 200
    assert job_response.json()[0]["status"] == "completed"

    document_response = client.get("/api/question-bank/raw-documents")
    assert document_response.status_code == 200
    assert document_response.json()[0]["document_version"] == 1
    assert document_response.json()[0]["is_latest"] is True


def test_collect_question_bank_versions_question_when_content_changes(client: TestClient) -> None:
    first = client.post(
        "/api/question-bank/collect",
        json={
            "raw_markdown": "# 示例题库\n\n请设计线程安全的 LRU 缓存。",
            "source_title": "示例题库",
            "category_hint": "系统设计",
            "source_url": "https://example.com/lru",
        },
    )
    assert first.status_code == 200

    second = client.post(
        "/api/question-bank/collect",
        json={
            "raw_markdown": "# 示例题库 v2\n\n请设计线程安全与热点隔离的 LRU 缓存。",
            "source_title": "示例题库",
            "category_hint": "系统设计",
            "source_url": "https://example.com/lru",
        },
    )
    assert second.status_code == 200
    payload = second.json()

    assert payload["inserted_count"] == 1
    assert payload["versioned_count"] == 1
    assert payload["questions"][0]["version"] == 2
    assert payload["questions"][0]["difficulty"] == "困难"

    list_response = client.get("/api/question-bank")
    items = list_response.json()
    assert len(items) == 1
    assert items[0]["version"] == 2

    document_response = client.get("/api/question-bank/raw-documents")
    documents = document_response.json()
    assert len(documents) == 2
    assert documents[0]["document_version"] == 2
