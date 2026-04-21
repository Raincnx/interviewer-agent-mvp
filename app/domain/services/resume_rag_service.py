from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.schemas.resume import ResumeProfile
from app.domain.services.resume_parser_service import ResumeParserService


@dataclass(frozen=True)
class RetrievedResumeSnippet:
    snippet_id: str
    section_title: str | None
    excerpt: str
    score: float


@dataclass(frozen=True)
class RetrievedResumePack:
    items: list[RetrievedResumeSnippet]
    formatted_context: str


class ResumeRAGService:
    def retrieve(
        self,
        resume_text: str,
        query: str,
        *,
        top_k: int = 3,
        profile: ResumeProfile | None = None,
    ) -> list[RetrievedResumeSnippet]:
        resume_text = (resume_text or "").strip()
        if not resume_text:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        profile = profile or ResumeParserService.extract_profile(resume_text)
        candidates = self._build_candidates(resume_text, profile)

        ranked: list[RetrievedResumeSnippet] = []
        for index, candidate in enumerate(candidates, start=1):
            score = self._score_chunk(query_tokens, candidate["section_title"], candidate["excerpt"])
            if score <= 0:
                continue
            ranked.append(
                RetrievedResumeSnippet(
                    snippet_id=f"resume-{index}",
                    section_title=candidate["section_title"],
                    excerpt=candidate["excerpt"],
                    score=score,
                )
            )

        ranked.sort(key=lambda item: (-item.score, item.snippet_id))
        return ranked[:top_k]

    @staticmethod
    def format_context(items: list[RetrievedResumeSnippet]) -> str:
        if not items:
            return "暂无可用简历参考。"

        lines: list[str] = []
        for index, item in enumerate(items, start=1):
            title = item.section_title or "未命名片段"
            lines.append(f"[简历片段 {index}] {title}")
            lines.append(item.excerpt)
            lines.append("")
        return "\n".join(lines).strip()

    @classmethod
    def _build_candidates(cls, resume_text: str, profile: ResumeProfile) -> list[dict[str, str | None]]:
        candidates: list[dict[str, str | None]] = []

        for project in profile.projects:
            excerpt_parts = [project.summary]
            if project.technologies:
                excerpt_parts.append(f"技术：{', '.join(project.technologies)}")
            if project.outcomes:
                excerpt_parts.append(f"结果：{'；'.join(project.outcomes)}")
            candidates.append(
                {
                    "section_title": f"项目：{project.title}",
                    "excerpt": " | ".join(part for part in excerpt_parts if part)[:420],
                }
            )

        for experience in profile.experiences:
            title = experience.company or experience.role or "经历"
            candidates.append(
                {
                    "section_title": f"经历：{title}",
                    "excerpt": experience.summary[:420],
                }
            )

        for education in profile.educations:
            title = education.school or education.degree or "教育"
            candidates.append(
                {
                    "section_title": f"教育：{title}",
                    "excerpt": education.summary[:420],
                }
            )

        if profile.skills:
            candidates.append(
                {
                    "section_title": "技能栈",
                    "excerpt": "、".join(profile.skills[:20]),
                }
            )

        if not candidates:
            candidates.extend(cls._chunk_resume_fallback(resume_text))

        return candidates

    @staticmethod
    def _chunk_resume_fallback(resume_text: str) -> list[dict[str, str | None]]:
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", resume_text) if part.strip()]
        chunks: list[dict[str, str | None]] = []
        for paragraph in paragraphs[:8]:
            lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
            title = lines[0][:30] if lines else "简历内容"
            chunks.append({"section_title": title, "excerpt": paragraph[:420]})
        return chunks or [{"section_title": "简历内容", "excerpt": resume_text[:420]}]

    @classmethod
    def _score_chunk(cls, query_tokens: set[str], section_title: str | None, excerpt: str) -> float:
        title = (section_title or "").lower()
        content = excerpt.lower()
        score = 0.0
        for token in query_tokens:
            if token in title:
                score += 4.0
            if token in content:
                score += 2.0
        return score

    @classmethod
    def _tokenize(cls, text: str) -> set[str]:
        normalized = text.lower()
        tokens: set[str] = set()

        for token in re.findall(r"[a-z0-9_+\-#.]{2,}", normalized):
            tokens.add(token)

        for chunk in re.findall(r"[\u4e00-\u9fff]{2,}", normalized):
            tokens.add(chunk)
            for size in (2, 3, 4):
                if len(chunk) < size:
                    continue
                for index in range(len(chunk) - size + 1):
                    tokens.add(chunk[index : index + size])

        return {token for token in tokens if token.strip()}
