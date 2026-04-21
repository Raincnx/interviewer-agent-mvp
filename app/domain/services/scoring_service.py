from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.core.prompts import PromptStore
from app.infra.llm.base import BaseLLMProvider
from app.infra.scoring.pydanticai_backend import PydanticAIScoringBackend

logger = logging.getLogger(__name__)


class ScoringService:
    def __init__(self, settings: Settings, provider: BaseLLMProvider) -> None:
        self.settings = settings
        self.provider = provider
        self.prompts_dir = Path(__file__).resolve().parents[2] / "prompts"
        self.prompt_store = PromptStore(self.prompts_dir, settings.prompt_version)
        self.pydanticai_backend = PydanticAIScoringBackend(settings)

    def generate_report_payload(self, transcript: str, meta: dict[str, str]) -> dict[str, Any]:
        system_prompt = self.prompt_store.read("grading_system")
        user_prompt = (
            "请基于下面这场面试生成最终结构化评估报告。\n"
            f"岗位：{meta['target_role']}\n"
            f"级别：{meta['level']}\n"
            f"轮次：{meta['round_type']}\n\n"
            f"完整对话：\n{transcript}"
        )

        schema = {
            "type": "object",
            "properties": {
                "overall_score": {"type": "integer"},
                "dimension_scores": {
                    "type": "object",
                    "properties": {
                        "基础知识": {"type": "integer"},
                        "项目深度": {"type": "integer"},
                        "追问应对": {"type": "integer"},
                        "表达沟通": {"type": "integer"},
                    },
                    "required": [
                        "基础知识",
                        "项目深度",
                        "追问应对",
                        "表达沟通",
                    ],
                },
                "strengths": {"type": "array", "items": {"type": "string"}},
                "weaknesses": {"type": "array", "items": {"type": "string"}},
                "next_actions": {"type": "array", "items": {"type": "string"}},
                "hire_recommendation": {"type": "string"},
            },
            "required": [
                "overall_score",
                "dimension_scores",
                "strengths",
                "weaknesses",
                "next_actions",
                "hire_recommendation",
            ],
        }

        if self.settings.scoring_backend.lower() == "pydanticai":
            try:
                return self.pydanticai_backend.generate_report_payload(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                )
            except RuntimeError as exc:
                logger.warning(
                    "PydanticAI scoring unavailable, falling back to provider JSON scoring: %s",
                    exc,
                )

        return self.provider.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=schema,
        )
