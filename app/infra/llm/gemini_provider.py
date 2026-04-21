from __future__ import annotations

import json
from typing import Any

from app.infra.llm.base import BaseLLMProvider


class GeminiLLMProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model_name: str) -> None:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise RuntimeError(
                "Gemini provider requires `google-genai`. Please install requirements and use the correct interpreter."
            ) from exc

        self.genai = genai
        self.types = types
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=user_prompt,
            config=self.types.GenerateContentConfig(
                system_instruction=system_prompt,
            ),
        )
        text = (response.text or "").strip()
        if not text:
            raise RuntimeError("Gemini returned empty text")
        return text

    def generate_json(self, system_prompt: str, user_prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=user_prompt,
            config=self.types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
        text = (response.text or "").strip()
        if not text:
            raise RuntimeError("Gemini returned empty JSON payload")
        return json.loads(text)
