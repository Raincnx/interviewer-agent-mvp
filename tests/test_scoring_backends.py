import sys
import types

import pytest

from app.core.config import Settings
from app.domain.schemas.scoring import InterviewScorePayload
from app.domain.services.scoring_service import ScoringService
from app.infra.llm.base import BaseLLMProvider
from app.infra.scoring.pydanticai_backend import PydanticAIScoringBackend


class StubProvider(BaseLLMProvider):
    def __init__(self, json_payload: dict) -> None:
        self.json_payload = json_payload
        self.last_system_prompt = None
        self.last_user_prompt = None
        self.last_schema = None

    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError

    def generate_json(self, system_prompt: str, user_prompt: str, schema: dict):
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        self.last_schema = schema
        return self.json_payload


def _sample_payload(score: int) -> dict:
    return {
        "overall_score": score,
        "dimension_scores": {
            "基础知识": 4,
            "项目深度": 4,
            "追问应对": 3,
            "表达沟通": 4,
        },
        "strengths": ["回答清晰"],
        "weaknesses": ["边界条件还可以更细"],
        "next_actions": ["继续补充项目复盘"],
        "hire_recommendation": "建议继续推进",
    }


def test_scoring_service_uses_provider_backend_by_default() -> None:
    provider = StubProvider(_sample_payload(80))
    service = ScoringService(Settings(scoring_backend="provider"), provider=provider)

    payload = service.generate_report_payload(
        transcript="Q: 介绍项目\nA: 我负责后端。",
        meta={
            "target_role": "后端工程师",
            "level": "高级",
        },
    )

    assert payload["overall_score"] == 80
    assert provider.last_schema is not None
    assert "级别：高级" in provider.last_user_prompt


def test_scoring_service_falls_back_to_provider_when_pydanticai_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = StubProvider(_sample_payload(79))
    service = ScoringService(Settings(scoring_backend="pydanticai"), provider=provider)
    monkeypatch.setattr(
        service.pydanticai_backend,
        "generate_report_payload",
        lambda system_prompt, user_prompt: (_ for _ in ()).throw(RuntimeError("missing pydantic-ai")),
    )

    payload = service.generate_report_payload(
        transcript="Q: 介绍项目\nA: 我负责订单系统改造。",
        meta={
            "target_role": "后端工程师",
            "level": "高级",
        },
    )

    assert payload["overall_score"] == 79
    assert provider.last_schema is not None


@pytest.mark.skipif(sys.version_info >= (3, 10), reason="Only relevant on Python 3.9")
def test_pydanticai_backend_raises_clear_error_on_python39() -> None:
    backend = PydanticAIScoringBackend(
        Settings(
            llm_provider="openai",
            llm_model="gpt-4.1-mini",
            openai_api_key="test-key",
            scoring_backend="pydanticai",
        )
    )

    with pytest.raises(RuntimeError, match="Python 3.10\\+"):
        backend.generate_report_payload("system", "user")


def test_pydanticai_backend_can_build_openai_model_with_fake_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    pydantic_ai_module = types.ModuleType("pydantic_ai")
    openai_model_module = types.ModuleType("pydantic_ai.models.openai")
    openai_provider_module = types.ModuleType("pydantic_ai.providers.openai")

    captured = {}

    class FakeOpenAIProvider:
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key

    class FakeOpenAIChatModel:
        def __init__(self, model_name: str, provider) -> None:
            self.model_name = model_name
            self.provider = provider

    class FakeResult:
        def __init__(self) -> None:
            self.output = InterviewScorePayload(**_sample_payload(88))

    class FakeAgent:
        def __init__(self, *, model, instructions: str, output_type) -> None:
            captured["model"] = model
            captured["instructions"] = instructions
            captured["output_type"] = output_type

        def run_sync(self, prompt: str) -> FakeResult:
            captured["prompt"] = prompt
            return FakeResult()

    pydantic_ai_module.Agent = FakeAgent
    pydantic_ai_module.PromptedOutput = lambda output_type: output_type
    openai_model_module.OpenAIChatModel = FakeOpenAIChatModel
    openai_provider_module.OpenAIProvider = FakeOpenAIProvider

    monkeypatch.setitem(sys.modules, "pydantic_ai", pydantic_ai_module)
    monkeypatch.setitem(sys.modules, "pydantic_ai.models.openai", openai_model_module)
    monkeypatch.setitem(sys.modules, "pydantic_ai.providers.openai", openai_provider_module)
    monkeypatch.setattr("app.infra.scoring.pydanticai_backend.sys.version_info", (3, 10, 0))

    backend = PydanticAIScoringBackend(
        Settings(
            llm_provider="openai",
            llm_model="gpt-4.1-mini",
            openai_api_key="test-key",
            scoring_backend="pydanticai",
        )
    )

    payload = backend.generate_report_payload("评分系统提示词", "请输出结构化报告")

    assert payload["overall_score"] == 88
    assert captured["output_type"] is InterviewScorePayload
    assert captured["model"].model_name == "gpt-4.1-mini"
    assert captured["model"].provider.api_key == "test-key"
    assert captured["prompt"] == "请输出结构化报告"


@pytest.mark.skipif(sys.version_info < (3, 10), reason="PydanticAI requires Python 3.10+")
def test_pydanticai_backend_retries_on_transient_error(monkeypatch: pytest.MonkeyPatch) -> None:
    pydantic_ai_module = types.ModuleType("pydantic_ai")
    call_count = {"value": 0}

    class FakePromptedOutput:
        def __init__(self, output_type) -> None:
            self.output_type = output_type

    class FakeResult:
        def __init__(self) -> None:
            self.output = InterviewScorePayload(**_sample_payload(86))

    class FakeAgent:
        def __init__(self, *, model, instructions: str, output_type) -> None:
            self.model = model
            self.instructions = instructions
            self.output_type = output_type

        def run_sync(self, prompt: str) -> FakeResult:
            call_count["value"] += 1
            if call_count["value"] < 3:
                raise RuntimeError("503 UNAVAILABLE")
            return FakeResult()

    pydantic_ai_module.Agent = FakeAgent
    pydantic_ai_module.PromptedOutput = FakePromptedOutput

    monkeypatch.setitem(sys.modules, "pydantic_ai", pydantic_ai_module)
    monkeypatch.setattr("app.infra.scoring.pydanticai_backend.sys.version_info", (3, 11, 0))
    monkeypatch.setattr(PydanticAIScoringBackend, "_build_model", lambda self: object())
    monkeypatch.setattr("app.infra.scoring.pydanticai_backend.time.sleep", lambda _: None)

    backend = PydanticAIScoringBackend(
        Settings(
            llm_provider="mock",
            llm_model="mock-interviewer-v1",
            scoring_backend="pydanticai",
        )
    )

    payload = backend.generate_report_payload("评分规则", "请输出结构化报告")

    assert payload["overall_score"] == 86
    assert call_count["value"] == 3


@pytest.mark.skipif(sys.version_info < (3, 10), reason="PydanticAI requires Python 3.10+")
def test_pydanticai_backend_supports_mock_provider_with_real_package() -> None:
    backend = PydanticAIScoringBackend(
        Settings(
            llm_provider="mock",
            llm_model="mock-interviewer-v1",
            scoring_backend="pydanticai",
        )
    )

    payload = backend.generate_report_payload("评分规则", "请输出结构化报告")

    assert payload["overall_score"] == 82
    assert payload["dimension_scores"]["基础知识"] == 4
    assert payload["hire_recommendation"] == "建议进入下一轮"


@pytest.mark.skipif(sys.version_info < (3, 10), reason="PydanticAI requires Python 3.10+")
def test_scoring_service_can_use_pydanticai_backend_with_mock_provider() -> None:
    provider = StubProvider({})
    service = ScoringService(
        Settings(
            llm_provider="mock",
            llm_model="mock-interviewer-v1",
            scoring_backend="pydanticai",
        ),
        provider=provider,
    )

    payload = service.generate_report_payload(
        transcript="Q: 请介绍一个项目。\nA: 我负责后端系统。",
        meta={
            "target_role": "后端工程师",
            "level": "高级",
        },
    )

    assert payload["overall_score"] == 82
    assert provider.last_schema is None
