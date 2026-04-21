from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.infra.repositories.question_bank_repo import QuestionBankRepository
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

    seed_db = testing_session_local()
    try:
        QuestionBankRepository(seed_db).create(
            title="什么是 Agent？",
            category="AI Agent 概念与架构",
            difficulty="中等",
            content="请解释 Agent 的规划、记忆和工具调用。",
            standard_answer="需要说明闭环、自主决策和工具调用。",
            follow_up_suggestions_json='["如何设计记忆？", "如何接工具？"]',
            tags_json='["agent", "memory", "tool-use"]',
            source_url="https://example.com/agent",
            source_title="示例来源",
            fingerprint="seed-agent-question",
        )
        seed_db.commit()
    finally:
        seed_db.close()

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
            "target_role": "后端工程师",
            "level": "高级",
            "round_type": "项目深挖",
        },
    )
    assert create_response.status_code == 200

    payload = create_response.json()
    interview_id = payload["interview_id"]
    assert payload["status"] == "running"
    assert payload["max_turns"] == 5
    assert payload["prompt_version"] == "v1"
    assert payload["question"]
    assert "Agent" in payload["question"] or "Tools" in payload["question"] or "项目" in payload["question"]

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
        json={"answer": "这是我的最后一轮回答"},
    )
    assert final_reply.status_code == 200
    final_payload = final_reply.json()
    assert final_payload["done"] is True
    assert final_payload["report"]["overall_score"] == 78
    assert final_payload["report"]["dimension_scores"]["基础知识"] == 4

    detail_response = client.get(f"/api/interviews/{interview_id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["status"] == "finished"
    assert detail_payload["prompt_version"] == "v1"
    assert len(detail_payload["turns"]) == 5
    assert all(turn["candidate_answer"] for turn in detail_payload["turns"])
    assert detail_payload["turns"][0]["knowledge_refs"]
    assert detail_payload["turns"][0]["knowledge_refs"][0]["title"] == "什么是 Agent？"
    assert detail_payload["report"]["hire_recommendation"] == "建议保留"


def test_resume_driven_interview_uses_resume_refs(client: TestClient) -> None:
    create_response = client.post(
        "/api/interviews",
        json={
            "target_role": "AI Agent 开发工程师",
            "level": "中级",
            "round_type": "项目深挖",
            "resume_filename": "resume.txt",
            "resume_text": "项目经历\n负责多智能体编排平台开发，落地了工具调用、记忆管理与链路观测。",
        },
    )
    assert create_response.status_code == 200
    payload = create_response.json()
    assert payload["resume_attached"] is True
    assert "简历" in payload["question"]

    detail_response = client.get(f"/api/interviews/{payload['interview_id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["has_resume"] is True
    assert detail["resume_filename"] == "resume.txt"
    assert detail["turns"][0]["resume_refs"]
    assert "多智能体编排平台开发" in detail["turns"][0]["resume_refs"][0]["excerpt"]


def test_resume_parse_endpoint_accepts_txt_file(client: TestClient) -> None:
    response = client.post(
        "/api/resume/parse",
        files={
            "file": (
                "resume.txt",
                "项目经历\n负责 AI Agent 平台开发与线上观测。\n技能栈\nPython、FastAPI、RAG。",
                "text/plain",
            )
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["filename"] == "resume.txt"
    assert payload["char_count"] > 20
    assert "AI Agent 平台开发" in payload["text"]


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
    assert report_payload["hire_recommendation"] == "建议保留"


def test_history_endpoint_lists_saved_interviews(client: TestClient) -> None:
    first = client.post(
        "/api/interviews",
        json={
            "target_role": "后端工程师",
            "level": "高级",
            "round_type": "项目深挖",
            "resume_filename": "resume.txt",
            "resume_text": "项目经历\n负责后端系统重构。",
        },
    ).json()
    second = client.post(
        "/api/interviews",
        json={
            "target_role": "AI Agent 开发工程师",
            "level": "中级",
            "round_type": "系统设计",
        },
    ).json()

    client.post(f"/api/interviews/{first['interview_id']}/finish")

    history_response = client.get("/api/interviews")
    assert history_response.status_code == 200

    history = history_response.json()
    assert len(history) == 2
    assert {item["id"] for item in history} == {first["interview_id"], second["interview_id"]}

    finished_item = next(item for item in history if item["id"] == first["interview_id"])
    running_item = next(item for item in history if item["id"] == second["interview_id"])

    assert finished_item["status"] == "finished"
    assert finished_item["prompt_version"] == "v1"
    assert finished_item["overall_score"] == 78
    assert finished_item["hire_recommendation"] == "建议保留"
    assert finished_item["has_resume"] is True
    assert finished_item["resume_filename"] == "resume.txt"

    assert running_item["status"] == "running"
    assert running_item["answered_turns"] == 0
    assert running_item["has_resume"] is False
