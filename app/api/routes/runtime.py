from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_runtime_config_read, get_runtime_settings_store
from app.core.runtime_settings import RuntimeSettingsStore
from app.domain.schemas.runtime import RuntimeConfigRead, RuntimeConfigUpdateRequest
from app.infra.llm.registry import get_llm_provider

router = APIRouter(prefix="/api/runtime", tags=["runtime"])


@router.get("/llm", response_model=RuntimeConfigRead)
def get_runtime_llm_config(
    config: RuntimeConfigRead = Depends(get_runtime_config_read),
) -> RuntimeConfigRead:
    return config


@router.put("/llm", response_model=RuntimeConfigRead)
def update_runtime_llm_config(
    payload: RuntimeConfigUpdateRequest,
    store: RuntimeSettingsStore = Depends(get_runtime_settings_store),
) -> RuntimeConfigRead:
    previous_settings = store.get()
    try:
        settings = store.update(
            provider=payload.provider,
            model_name=payload.model_name,
            prompt_version=payload.prompt_version,
            scoring_backend=payload.scoring_backend,
            api_key=payload.api_key,
        )
        get_llm_provider(settings)
    except (RuntimeError, ValueError) as exc:
        store.replace(previous_settings)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return RuntimeConfigRead(
        provider=settings.llm_provider,
        model_name=settings.llm_model,
        prompt_version=settings.prompt_version,
        scoring_backend=settings.scoring_backend,
        api_key_configured=bool(settings.gemini_api_key or settings.openai_api_key),
    )
