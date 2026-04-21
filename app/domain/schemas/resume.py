from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ResumeProject(BaseModel):
    title: str
    summary: str
    technologies: list[str] = Field(default_factory=list)
    outcomes: list[str] = Field(default_factory=list)


class ResumeExperience(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    summary: str


class ResumeEducation(BaseModel):
    school: Optional[str] = None
    degree: Optional[str] = None
    summary: str


class ResumeProfile(BaseModel):
    headline: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    projects: list[ResumeProject] = Field(default_factory=list)
    experiences: list[ResumeExperience] = Field(default_factory=list)
    educations: list[ResumeEducation] = Field(default_factory=list)


class ResumeParseResponse(BaseModel):
    filename: str
    content_type: Optional[str] = None
    text: str
    preview: str
    char_count: int
    profile: ResumeProfile
