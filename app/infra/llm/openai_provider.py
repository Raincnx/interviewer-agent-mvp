from __future__ import annotations

import json
from typing import Any

from app.infra.llm.base import BaseLLMProvider


class OpenAILLMProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model_name: str) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "OpenAI provider requires `openai`. Please install requirements and use the correct interpreter."
            ) from exc

        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name

    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.responses.create(
            model=self.model_name,
            instructions=system_prompt,
            input=user_prompt,
        )
        text = (response.output_text or "").strip()
        if not text:
            raise RuntimeError("OpenAI returned empty text")
        return text

    def generate_json(self, system_prompt: str, user_prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        response = self.client.responses.create(
            model=self.model_name,
            instructions=system_prompt,
            input=user_prompt,
        )
        text = (response.output_text or "").strip()
        if not text:
            raise RuntimeError("OpenAI returned empty JSON payload")
        return json.loads(text)
