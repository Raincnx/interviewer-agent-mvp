from app.core.config import Settings
from app.infra.llm.base import BaseLLMProvider
from app.infra.llm.gemini_provider import GeminiLLMProvider
from app.infra.llm.mock_provider import MockLLMProvider
from app.infra.llm.openai_provider import OpenAILLMProvider


def get_llm_provider(settings: Settings) -> BaseLLMProvider:
    provider_name = settings.llm_provider.lower()

    if provider_name == "mock":
        return MockLLMProvider()

    if provider_name == "gemini":
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")
        return GeminiLLMProvider(
            api_key=settings.gemini_api_key,
            model_name=settings.llm_model,
        )

    if provider_name == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        return OpenAILLMProvider(
            api_key=settings.openai_api_key,
            model_name=settings.llm_model,
        )

    raise ValueError(f"Unsupported llm provider: {settings.llm_provider}")
