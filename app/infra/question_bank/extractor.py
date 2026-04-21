from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.core.prompts import PromptStore
from app.domain.schemas.question_bank import InterviewQuestion, QuestionExtractionResult


class QuestionCollectorExtractor:
    _retry_delays_seconds = (1.5, 3.0, 6.0)

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        prompts_dir = Path(__file__).resolve().parents[2] / "prompts"
        self.prompt_store = PromptStore(prompts_dir, settings.prompt_version)

    def extract(
        self,
        *,
        markdown: str,
        source_url: str | None,
        source_title: str | None,
        category_hint: str | None,
        max_questions: int,
    ) -> list[InterviewQuestion]:
        self._ensure_runtime_supported()

        try:
            from pydantic_ai import Agent, PromptedOutput
        except ImportError as exc:
            raise RuntimeError("题库采集依赖 `pydantic-ai`，请先在当前环境安装后再使用。") from exc

        system_prompt = self.prompt_store.read("question_collector_system")
        user_prompt = (
            f"来源 URL：{source_url or '未提供'}\n"
            f"来源标题：{source_title or '未提供'}\n"
            f"分类提示：{category_hint or '未提供'}\n"
            f"最多提取题目数：{max_questions}\n\n"
            f"网页内容 Markdown：\n{markdown}"
        )
        model = self._build_model()
        agent = Agent(
            model=model,
            instructions=system_prompt,
            output_type=PromptedOutput(QuestionExtractionResult),
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
                    raise RuntimeError(f"题库提取失败：{exc}") from exc

        if output is None:
            raise RuntimeError(f"题库提取失败：{last_error}")

        return output.questions

    def _ensure_runtime_supported(self) -> None:
        if sys.version_info < (3, 10):
            current_version = f"{sys.version_info.major}.{sys.version_info.minor}"
            raise RuntimeError(f"题库采集 Agent 需要 Python 3.10+，当前环境是 Python {current_version}。")

    def _build_model(self) -> Any:
        provider_name = self.settings.llm_provider.lower()

        if provider_name == "mock":
            return self._build_mock_model()

        if provider_name == "openai":
            if not self.settings.openai_api_key:
                raise RuntimeError("当前未配置 `OPENAI_API_KEY`，无法使用 OpenAI 题库采集。")
            from pydantic_ai.models.openai import OpenAIChatModel
            from pydantic_ai.providers.openai import OpenAIProvider

            return OpenAIChatModel(
                self.settings.llm_model,
                provider=OpenAIProvider(api_key=self.settings.openai_api_key),
            )

        if provider_name == "gemini":
            if not self.settings.gemini_api_key:
                raise RuntimeError("当前未配置 `GEMINI_API_KEY`，无法使用 Gemini 题库采集。")
            from pydantic_ai.models.google import GoogleModel
            from pydantic_ai.providers.google import GoogleProvider

            return GoogleModel(
                self.settings.llm_model,
                provider=GoogleProvider(api_key=self.settings.gemini_api_key),
            )

        raise RuntimeError(f"当前不支持使用 `{self.settings.llm_provider}` 作为题库采集模型。")

    @staticmethod
    def _is_retryable_error(exc: Exception) -> bool:
        message = str(exc).lower()
        retry_signals = ("503", "429", "unavailable", "timeout", "temporarily", "rate limit")
        return any(signal in message for signal in retry_signals)

    def _build_mock_model(self) -> Any:
        from pydantic_ai import ModelResponse, TextPart
        from pydantic_ai.models.function import FunctionModel

        async def mock_model(messages: list[Any], info: Any) -> Any:
            last_text = ""
            for message in reversed(messages):
                parts = getattr(message, "parts", [])
                collected = [getattr(part, "content", "") for part in parts if hasattr(part, "content")]
                if collected:
                    last_text = "\n".join(collected)
                    break

            title = self._guess_title(last_text)
            payload = QuestionExtractionResult(
                questions=[
                    InterviewQuestion(
                        title=title,
                        category=self._guess_category(last_text),
                        difficulty="中等",
                        content=title,
                        standard_answer="需要候选人解释关键思路、核心实现与取舍。",
                        follow_up_suggestions=[
                            "请继续展开关键实现细节。",
                            "如果流量翻倍，这个方案会有什么问题？",
                        ],
                        tags=["mock", "题库采集"],
                    )
                ]
            )
            return ModelResponse(parts=[TextPart(json.dumps(payload.model_dump(), ensure_ascii=False))])

        return FunctionModel(mock_model, model_name="function:question-collector")

    @staticmethod
    def _guess_title(markdown: str) -> str:
        for line in markdown.splitlines():
            stripped = line.strip(" -#\t")
            if len(stripped) >= 8:
                return stripped[:120]
        return "请介绍一个你做过的核心项目，并说明你的技术贡献。"

    @staticmethod
    def _guess_category(markdown: str) -> str:
        normalized = markdown.lower()
        rules = [
            ("强化学习", "RL"),
            ("python", "Python"),
            ("算法", "算法"),
            ("系统设计", "系统设计"),
            ("机器学习", "机器学习"),
        ]
        for keyword, category in rules:
            if keyword.lower() in normalized:
                return category
        return "通用技术面试"
