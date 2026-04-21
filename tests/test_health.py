from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["provider"] == "mock"
    assert payload["prompt_version"] == "v1"
    assert payload["scoring_backend"] == "provider"
    assert payload["api_key_configured"] is False


def test_index_page() -> None:
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "面试智能体控制台" in response.text
    assert "历史面试" in response.text
    assert "运行时模型配置" in response.text
    assert "题库浏览" in response.text
    assert "候选人简历" in response.text
