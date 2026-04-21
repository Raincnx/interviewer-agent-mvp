from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.infra.llm.base import BaseLLMProvider


class ScoringService:
    def __init__(self, settings: Settings, provider: BaseLLMProvider) -> None:
        self.settings = settings
        self.provider = provider
        self.prompts_dir = Path(__file__).resolve().parents[2] / "prompts"

    def generate_report_payload(self, transcript: str, meta: dict[str, str]) -> dict[str, Any]:
        system_prompt = (self.prompts_dir / "grading_system.txt").read_text(encoding="utf-8")
        user_prompt = f"""
请基于以下完整面试对话输出最终评分结果。

岗位：{meta["target_role"]}
级别：{meta["level"]}
轮次：{meta["round_type"]}

完整对话：
{transcript}
        """.strip()

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
                        "表达结构": {"type": "integer"},
                    },
                    "required": ["基础知识", "项目深度", "追问应对", "表达结构"],
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

        return self.provider.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=schema,
        )
