from __future__ import annotations

import re
from dataclasses import dataclass


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
    def retrieve(self, resume_text: str, query: str, *, top_k: int = 3) -> list[RetrievedResumeSnippet]:
        resume_text = (resume_text or "").strip()
        if not resume_text:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        ranked: list[RetrievedResumeSnippet] = []
        for index, chunk in enumerate(self._chunk_resume(resume_text), start=1):
            score = self._score_chunk(query_tokens, chunk["section_title"], chunk["excerpt"])
            if score <= 0:
                continue
            ranked.append(
                RetrievedResumeSnippet(
                    snippet_id=f"resume-{index}",
                    section_title=chunk["section_title"],
                    excerpt=chunk["excerpt"],
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
            title = item.section_title or "未命名段落"
            lines.append(f"[简历片段 {index}] {title}")
            lines.append(item.excerpt)
            lines.append("")
        return "\n".join(lines).strip()

    @staticmethod
    def _chunk_resume(resume_text: str) -> list[dict[str, str | None]]:
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", resume_text) if part.strip()]
        chunks: list[dict[str, str | None]] = []
        buffer: list[str] = []
        section_title: str | None = None

        def flush() -> None:
            nonlocal buffer, section_title
            if not buffer:
                return
            excerpt = "\n".join(buffer).strip()
            chunks.append({"section_title": section_title, "excerpt": excerpt[:420]})
            buffer = []
            section_title = None

        for paragraph in paragraphs:
            first_line = paragraph.splitlines()[0].strip()
            maybe_title = first_line if len(first_line) <= 18 else None
            if maybe_title and len(paragraph) <= 80:
                flush()
                section_title = maybe_title
                buffer.append(paragraph)
                flush()
                continue

            if section_title is None and maybe_title and any(
                keyword in maybe_title.lower()
                for keyword in ["项目", "经历", "教育", "技能", "project", "experience", "education", "skill"]
            ):
                flush()
                section_title = maybe_title
                buffer.append(paragraph)
                continue

            if sum(len(part) for part in buffer) + len(paragraph) > 420:
                flush()
            buffer.append(paragraph)

        flush()
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
