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
Generate the final structured interview assessment for this interview.
Role: {meta["target_role"]}
Level: {meta["level"]}
Round type: {meta["round_type"]}

Full transcript:
{transcript}
        """.strip()

        schema = {
            "type": "object",
            "properties": {
                "overall_score": {"type": "integer"},
                "dimension_scores": {
                    "type": "object",
                    "properties": {
                        "Technical Knowledge": {"type": "integer"},
                        "Project Depth": {"type": "integer"},
                        "Follow-up Handling": {"type": "integer"},
                        "Communication": {"type": "integer"},
                    },
                    "required": [
                        "Technical Knowledge",
                        "Project Depth",
                        "Follow-up Handling",
                        "Communication",
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

        return self.provider.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=schema,
        )
