from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class InterviewQuestion(BaseModel):
    title: str = Field(description="题目简述")
    category: str = Field(description="分类，如：RL、Python、算法、系统设计")
    difficulty: str = Field(description="难度：简单、中等、困难")
    content: str = Field(description="完整的题目描述")
    standard_answer: str = Field(description="标准答案或核心要点")
    follow_up_suggestions: list[str] = Field(default_factory=list, description="推荐的追问路径")
    tags: list[str] = Field(default_factory=list, description="题目标记标签")
    source_url: Optional[str] = None
    source_title: Optional[str] = None


class QuestionExtractionResult(BaseModel):
    questions: list[InterviewQuestion] = Field(default_factory=list)


class QuestionCollectRequest(BaseModel):
    source_url: Optional[str] = None
    raw_markdown: Optional[str] = None
    source_title: Optional[str] = None
    category_hint: Optional[str] = None
    max_questions: int = Field(default=20, ge=1, le=100)
    use_firecrawl: bool = False

    @model_validator(mode="after")
    def validate_source(self) -> "QuestionCollectRequest":
        if not self.source_url and not self.raw_markdown:
            raise ValueError("`source_url` 和 `raw_markdown` 至少需要提供一个。")
        return self


class QuestionBankItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    category: str
    difficulty: str
    content: str
    standard_answer: str
    follow_up_suggestions: list[str]
    tags: list[str]
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    fingerprint: str
    created_at: datetime
    updated_at: datetime


class QuestionCollectResponse(BaseModel):
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    fetched_chars: int
    extracted_count: int
    inserted_count: int
    skipped_count: int
    questions: list[QuestionBankItemRead]
