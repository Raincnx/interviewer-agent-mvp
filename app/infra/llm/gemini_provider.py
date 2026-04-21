from __future__ import annotations

import json
import time
from typing import Any

from app.infra.llm.base import BaseLLMProvider


class GeminiLLMProvider(BaseLLMProvider):
    _retry_delays_seconds = (1.5, 3.0, 6.0)

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
        response = self._generate_content(
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
        response = self._generate_content(
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

    def _generate_content(self, *, contents: str, config: Any) -> Any:
        last_error: Exception | None = None

        for attempt_index, delay_seconds in enumerate((0.0, *self._retry_delays_seconds), start=1):
            if delay_seconds:
                time.sleep(delay_seconds)

            try:
                return self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config,
                )
            except Exception as exc:
                last_error = exc
                if not self._is_retryable_error(exc) or attempt_index == len(self._retry_delays_seconds) + 1:
                    raise RuntimeError(f"Gemini request failed: {exc}") from exc

        raise RuntimeError(f"Gemini request failed: {last_error}")

    @staticmethod
    def _is_retryable_error(exc: Exception) -> bool:
        message = str(exc).lower()
        retry_signals = ("503", "429", "unavailable", "timeout", "temporarily", "rate limit")
        return any(signal in message for signal in retry_signals)
