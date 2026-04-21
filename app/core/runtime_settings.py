from __future__ import annotations

from threading import Lock

from app.core.config import Settings


class RuntimeSettingsStore:
    def __init__(self, base_settings: Settings) -> None:
        self._lock = Lock()
        self._settings = base_settings.model_copy(deep=True)

    def get(self) -> Settings:
        with self._lock:
            return self._settings.model_copy(deep=True)

    def replace(self, settings: Settings) -> Settings:
        with self._lock:
            self._settings = settings.model_copy(deep=True)
            return self._settings.model_copy(deep=True)

    def update(
        self,
        *,
        provider: str,
        model_name: str,
        prompt_version: str,
        scoring_backend: str,
        api_key: str | None = None,
    ) -> Settings:
        provider_name = provider.lower().strip()
        backend_name = scoring_backend.lower().strip()
        new_values = {
            "llm_provider": provider_name,
            "llm_model": model_name.strip(),
            "prompt_version": prompt_version.strip(),
            "scoring_backend": backend_name,
        }

        if backend_name not in {"provider", "pydanticai"}:
            raise ValueError(f"Unsupported scoring backend: {scoring_backend}")

        if provider_name == "mock":
            new_values["gemini_api_key"] = ""
            new_values["openai_api_key"] = ""
        elif provider_name == "gemini":
            if api_key:
                new_values["gemini_api_key"] = api_key.strip()
            new_values["openai_api_key"] = ""
        elif provider_name == "openai":
            if api_key:
                new_values["openai_api_key"] = api_key.strip()
            new_values["gemini_api_key"] = ""
        else:
            raise ValueError(f"Unsupported llm provider: {provider}")

        with self._lock:
            self._settings = self._settings.model_copy(update=new_values, deep=True)
            return self._settings.model_copy(deep=True)
