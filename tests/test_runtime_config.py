from fastapi.testclient import TestClient

from app.main import app


def test_runtime_llm_config_defaults_to_mock() -> None:
    client = TestClient(app)
    response = client.get("/api/runtime/llm")
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "mock"
    assert payload["model_name"] == "mock-interviewer-v1"
    assert payload["prompt_version"] == "v1"
    assert payload["scoring_backend"] == "provider"
    assert payload["api_key_configured"] is False


def test_runtime_llm_config_can_switch_to_gemini() -> None:
    client = TestClient(app)
    response = client.put(
        "/api/runtime/llm",
        json={
            "provider": "gemini",
            "model_name": "gemini-2.5-flash",
            "prompt_version": "v1",
            "scoring_backend": "provider",
            "api_key": "test-gemini-key",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "gemini"
    assert payload["model_name"] == "gemini-2.5-flash"
    assert payload["scoring_backend"] == "provider"
    assert payload["api_key_configured"] is True

    health_response = client.get("/health")
    assert health_response.status_code == 200
    assert health_response.json()["provider"] == "gemini"
    assert health_response.json()["scoring_backend"] == "provider"
    assert health_response.json()["api_key_configured"] is True

    client.put(
        "/api/runtime/llm",
        json={
            "provider": "mock",
            "model_name": "mock-interviewer-v1",
            "prompt_version": "v1",
            "scoring_backend": "provider",
        },
    )


def test_runtime_llm_config_rejects_real_provider_without_key() -> None:
    client = TestClient(app)
    response = client.put(
        "/api/runtime/llm",
        json={
            "provider": "openai",
            "model_name": "gpt-4.1-mini",
            "prompt_version": "v1",
            "scoring_backend": "provider",
        },
    )
    assert response.status_code == 400
    assert "OPENAI_API_KEY" in response.json()["detail"]

    current = client.get("/api/runtime/llm")
    assert current.status_code == 200
    assert current.json()["provider"] == "mock"
