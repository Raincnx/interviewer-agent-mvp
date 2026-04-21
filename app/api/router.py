from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.interviews import router as interviews_router
from app.api.routes.question_bank import router as question_bank_router
from app.api.routes.reports import router as reports_router
from app.api.routes.runtime import router as runtime_router
from app.api.routes.web import router as web_router

api_router = APIRouter()
api_router.include_router(web_router)
api_router.include_router(health_router, tags=["health"])
api_router.include_router(runtime_router)
api_router.include_router(question_bank_router)
api_router.include_router(interviews_router, prefix="/api/interviews", tags=["interviews"])
api_router.include_router(reports_router, prefix="/api/interviews", tags=["reports"])
