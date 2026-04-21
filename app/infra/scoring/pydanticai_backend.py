from __future__ import annotations

import json
import sys
import time
from typing import Any

from app.core.config import Settings
from app.domain.schemas.scoring import InterviewScorePayload


class PydanticAIScoringBackend:
    """Optional structured-scoring backend powered by PydanticAI."""

    _retry_delays_seconds = (1.5, 3.0, 6.0)

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_report_payload(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        self._ensure_runtime_supported()

        try:
            from pydantic_ai import Agent, PromptedOutput
        except ImportError as exc:
            raise RuntimeError(
                "当前环境未安装 `pydantic-ai`。请在 Python 3.10+ 环境中安装依赖后再启用 `SCORING_BACKEND=pydanticai`。"
            ) from exc

        model = self._build_model()
        agent = Agent(
            model=model,
            instructions=system_prompt,
            output_type=PromptedOutput(InterviewScorePayload),
        )

        output = None
        last_error: Exception | None = None

        for attempt_index, delay_seconds in enumerate((0.0, *self._retry_delays_seconds), start=1):
            if delay_seconds:
                time.sleep(delay_seconds)

            try:
                result = agent.run_sync(user_prompt)
                output = result.output
                break
            except Exception as exc:
                last_error = exc
                if not self._is_retryable_error(exc) or attempt_index == len(self._retry_delays_seconds) + 1:
                    raise RuntimeError(f"PydanticAI 评分失败：{exc}") from exc

        if output is None:
            raise RuntimeError(f"PydanticAI 评分失败：{last_error}")

        if hasattr(output, "model_dump"):
            return output.model_dump()

        return dict(output)

    def _ensure_runtime_supported(self) -> None:
        if sys.version_info < (3, 10):
            current_version = f"{sys.version_info.major}.{sys.version_info.minor}"
            raise RuntimeError(
                f"PydanticAI 官方要求 Python 3.10+，当前环境是 Python {current_version}。"
            )

    def _build_model(self) -> Any:
        provider_name = self.settings.llm_provider.lower()

        if provider_name == "mock":
            return self._build_mock_model()

        if provider_name == "openai":
            if not self.settings.openai_api_key:
                raise RuntimeError("启用 PydanticAI OpenAI 评分前，需要配置 OPENAI_API_KEY。")

            from pydantic_ai.models.openai import OpenAIChatModel
            from pydantic_ai.providers.openai import OpenAIProvider

            return OpenAIChatModel(
                self.settings.llm_model,
                provider=OpenAIProvider(api_key=self.settings.openai_api_key),
            )

        if provider_name == "gemini":
            if not self.settings.gemini_api_key:
                raise RuntimeError("启用 PydanticAI Gemini 评分前，需要配置 GEMINI_API_KEY。")

            from pydantic_ai.models.google import GoogleModel
            from pydantic_ai.providers.google import GoogleProvider

            return GoogleModel(
                self.settings.llm_model,
                provider=GoogleProvider(api_key=self.settings.gemini_api_key),
            )

        raise RuntimeError(
            "PydanticAI 评分后端当前只支持 `mock`、`openai` 或 `gemini` provider。"
        )

    @staticmethod
    def _is_retryable_error(exc: Exception) -> bool:
        message = str(exc).lower()
        retry_signals = ("503", "429", "unavailable", "timeout", "temporarily", "rate limit")
        return any(signal in message for signal in retry_signals)

    def _build_mock_model(self) -> Any:
        from pydantic_ai import ModelResponse, TextPart
        from pydantic_ai.models.function import FunctionModel

        async def mock_model(messages: list[Any], info: Any) -> Any:
            payload = InterviewScorePayload(
                overall_score=82,
                dimension_scores={
                    "基础知识": 4,
                    "项目深度": 4,
                    "追问应对": 4,
                    "表达沟通": 4,
                },
                strengths=[
                    "能够围绕项目背景、职责和结果进行完整表述。",
                    "回答中体现出一定的工程权衡意识。",
                    "面对追问时能够继续补充关键细节。",
                ],
                weaknesses=[
                    "部分实现细节还不够量化。",
                    "异常场景与边界条件覆盖可以更完整。",
                    "回答结构仍有进一步压缩和提炼空间。",
                ],
                next_actions=[
                    "继续准备 2 到 3 个项目的关键技术决策与复盘细节。",
                    "加强高并发、一致性和故障处理相关案例表达。",
                    "练习用更清晰的结构组织开放性问题回答。",
                ],
                hire_recommendation="建议进入下一轮",
            )
            return ModelResponse(parts=[TextPart(json.dumps(payload.model_dump(), ensure_ascii=False))])

        return FunctionModel(mock_model, model_name="function:mock-scoring")
