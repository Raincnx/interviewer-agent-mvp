from typing import Optional

from pydantic import BaseModel


class ResumeParseResponse(BaseModel):
    filename: str
    content_type: Optional[str] = None
    text: str
    preview: str
    char_count: int
