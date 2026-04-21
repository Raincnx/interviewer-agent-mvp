from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture
def client(tmp_path) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "test.db"
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

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_interview_flow_generates_report_at_max_turns(client: TestClient) -> None:
    create_response = client.post(
        "/api/interviews",
        json={
            "target_role": "Backend Engineer",
            "level": "Senior",
            "round_type": "Project Deep Dive",
        },
    )
    assert create_response.status_code == 200

    payload = create_response.json()
    interview_id = payload["interview_id"]
    assert payload["status"] == "running"
    assert payload["max_turns"] == 5
    assert payload["question"]

    for index in range(4):
        reply_response = client.post(
            f"/api/interviews/{interview_id}/reply",
            json={"answer": f"My answer #{index + 1}"},
        )
        assert reply_response.status_code == 200
        reply_payload = reply_response.json()
        assert reply_payload["done"] is False
        assert reply_payload["question"]
        assert reply_payload["remaining_turns"] == 4 - index

    final_reply = client.post(
        f"/api/interviews/{interview_id}/reply",
        json={"answer": "My final answer"},
    )
    assert final_reply.status_code == 200
    final_payload = final_reply.json()
    assert final_payload["done"] is True
    assert final_payload["report"]["overall_score"] == 78
    assert final_payload["report"]["dimension_scores"]["Technical Knowledge"] == 4

    detail_response = client.get(f"/api/interviews/{interview_id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["status"] == "finished"
    assert len(detail_payload["turns"]) == 5
    assert detail_payload["report"]["hire_recommendation"] == "Hold"


def test_report_endpoint_returns_existing_report(client: TestClient) -> None:
    create_response = client.post("/api/interviews", json={})
    interview_id = create_response.json()["interview_id"]

    finish_response = client.post(f"/api/interviews/{interview_id}/finish")
    assert finish_response.status_code == 200
    assert finish_response.json()["done"] is True

    report_response = client.get(f"/api/interviews/{interview_id}/report")
    assert report_response.status_code == 200
    report_payload = report_response.json()
    assert report_payload["overall_score"] == 78
    assert report_payload["hire_recommendation"] == "Hold"
