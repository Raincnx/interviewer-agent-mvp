from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_interview_service
from app.domain.schemas.report import ReportRead
from app.domain.services.interview_service import InterviewService

router = APIRouter()


@router.get("/{interview_id}/report", response_model=ReportRead)
def get_report(
    interview_id: str,
    service: InterviewService = Depends(get_interview_service),
) -> ReportRead:
    report = service.get_report(interview_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
