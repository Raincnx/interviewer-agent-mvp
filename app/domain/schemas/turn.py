from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class QuestionKnowledgeRef(BaseModel):
    id: str
    title: str
    category: str
    difficulty: str
    source_title: Optional[str] = None
    source_url: Optional[str] = None


class ResumeSnippetRef(BaseModel):
    snippet_id: str
    section_title: Optional[str] = None
    excerpt: str


class TurnRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    turn_index: int
    question_text: str
    question_kind: str
    followup_reason: Optional[str] = None
    candidate_answer: Optional[str] = None
    knowledge_refs: list[QuestionKnowledgeRef] = Field(default_factory=list)
    resume_refs: list[ResumeSnippetRef] = Field(default_factory=list)
    created_at: datetime
