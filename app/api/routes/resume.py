from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import get_resume_parser_service
from app.domain.schemas.resume import ResumeParseResponse
from app.domain.services.resume_parser_service import ResumeParserService

router = APIRouter(prefix="/api/resume", tags=["resume"])


@router.post("/parse", response_model=ResumeParseResponse)
async def parse_resume(
    file: UploadFile = File(...),
    service: ResumeParserService = Depends(get_resume_parser_service),
) -> ResumeParseResponse:
    try:
        return await service.parse_upload(file)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
