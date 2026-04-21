from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()

TEMPLATE_PATH = Path(__file__).resolve().parents[3] / "templates" / "index.html"


@router.get("/", response_class=FileResponse)
def index() -> FileResponse:
    return FileResponse(TEMPLATE_PATH)
