from typing import Optional

from pydantic import BaseModel, Field


class RuntimeConfigRead(BaseModel):
    provider: str
    model_name: str
    prompt_version: str
    scoring_backend: str
    api_key_configured: bool


class RuntimeConfigUpdateRequest(BaseModel):
    provider: str = Field(pattern="^(mock|gemini|openai)$")
    model_name: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    scoring_backend: str = Field(default="provider", pattern="^(provider|pydanticai)$")
    api_key: Optional[str] = None
