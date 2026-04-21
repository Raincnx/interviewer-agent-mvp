from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "ok": True,
        "provider": settings.llm_provider,
        "model": settings.llm_model,
    }
