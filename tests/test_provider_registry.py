from pathlib import Path

from app.core.config import Settings
from app.core.prompts import PromptStore
from app.infra.llm.gemini_provider import GeminiLLMProvider
from app.infra.llm.openai_provider import OpenAILLMProvider
from app.infra.llm.registry import get_llm_provider


def test_provider_registry_supports_gemini() -> None:
    settings = Settings(
        llm_provider="gemini",
        llm_model="gemini-2.5-flash",
        gemini_api_key="test-key",
    )

    provider = get_llm_provider(settings)
    assert isinstance(provider, GeminiLLMProvider)


def test_provider_registry_supports_openai() -> None:
    settings = Settings(
        llm_provider="openai",
        llm_model="gpt-4.1-mini",
        openai_api_key="test-key",
    )

    provider = get_llm_provider(settings)
    assert isinstance(provider, OpenAILLMProvider)


def test_prompt_store_reads_versioned_prompt() -> None:
    settings = Settings(prompt_version="v1")
    store = PromptStore(root_dir=Path("app/prompts"), version=settings.prompt_version)
    prompt = store.read("interviewer_system")
    assert "资深技术面试官" in prompt
