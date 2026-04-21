from fastapi import APIRouter, Depends

from app.api.deps import get_runtime_config_read
from app.domain.schemas.runtime import RuntimeConfigRead

router = APIRouter()


@router.get("/health")
def health(config: RuntimeConfigRead = Depends(get_runtime_config_read)) -> dict:
    return {
        "ok": True,
        "provider": config.provider,
        "model": config.model_name,
        "prompt_version": config.prompt_version,
        "scoring_backend": config.scoring_backend,
        "api_key_configured": config.api_key_configured,
    }
