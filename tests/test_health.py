from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["provider"] == "mock"
    assert response.json()["prompt_version"] == "v1"
    assert response.json()["scoring_backend"] == "provider"
    assert response.json()["api_key_configured"] is False


def test_index_page() -> None:
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "面试智能体控制台" in response.text
    assert "历史面试" in response.text
    assert "运行时模型配置" in response.text
    assert "评分后端" in response.text
