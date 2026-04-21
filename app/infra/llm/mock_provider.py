from __future__ import annotations

from typing import Any

from app.infra.llm.base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        lowered = user_prompt.lower()
        if "ask the first interview question" in lowered or "start a new interview" in lowered:
            return (
                "Tell me about one backend project you know best, including the goal, your role, "
                "the architecture, and the result."
            )
        if "full interview transcript" in lowered or "ask the next interviewer question" in lowered:
            return (
                "You mentioned using caching and async jobs. How did you keep data consistent, "
                "and what did you do when messages started piling up?"
            )
        return "Please go one level deeper and explain the trade-offs in your decision."

    def generate_json(self, system_prompt: str, user_prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        return {
            "overall_score": 78,
            "dimension_scores": {
                "Technical Knowledge": 4,
                "Project Depth": 4,
                "Follow-up Handling": 3,
                "Communication": 3,
            },
            "strengths": [
                "Explains project context clearly.",
                "Shows sound reasoning around technical choices.",
                "Demonstrates practical performance awareness.",
            ],
            "weaknesses": [
                "Answers lose specificity under deeper probing.",
                "Capacity planning and edge cases need more detail.",
                "Communication can be tighter and more structured.",
            ],
            "next_actions": [
                "Prepare two projects with deeper implementation detail.",
                "Practice consistency and failure-handling scenarios for caches and queues.",
                "Use a tighter story structure when answering open questions.",
            ],
            "hire_recommendation": "Hold",
        }
