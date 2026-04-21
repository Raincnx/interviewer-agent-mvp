from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.services.question_bank_service import QuestionBankService


@dataclass(frozen=True)
class RetrievedQuestion:
    id: str
    title: str
    category: str
    difficulty: str
    content: str
    standard_answer: str
    follow_up_suggestions: list[str]
    tags: list[str]
    source_title: str | None
    source_url: str | None
    score: float


@dataclass(frozen=True)
class RetrievedKnowledgePack:
    items: list[RetrievedQuestion]
    formatted_context: str


class QuestionRAGService:
    def __init__(self, question_bank_service: QuestionBankService) -> None:
        self.question_bank_service = question_bank_service

    def retrieve(self, query: str, *, top_k: int = 3) -> list[RetrievedQuestion]:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        ranked: list[RetrievedQuestion] = []
        for item in self.question_bank_service.list_questions():
            score = self._score_item(query_tokens, item)
            if score <= 0:
                continue
            ranked.append(
                RetrievedQuestion(
                    id=item.id,
                    title=item.title,
                    category=item.category,
                    difficulty=item.difficulty,
                    content=item.content,
                    standard_answer=item.standard_answer,
                    follow_up_suggestions=item.follow_up_suggestions,
                    tags=item.tags,
                    source_title=item.source_title,
                    source_url=item.source_url,
                    score=score,
                )
            )

        ranked.sort(key=lambda item: (-item.score, item.title))
        return ranked[:top_k]

    @staticmethod
    def format_context(items: list[RetrievedQuestion]) -> str:
        if not items:
            return "暂无可用题库参考。"

        lines: list[str] = []
        for index, item in enumerate(items, start=1):
            lines.append(f"[参考题 {index}] {item.title}")
            lines.append(f"分类：{item.category} | 难度：{item.difficulty} | 标签：{', '.join(item.tags[:6])}")
            lines.append(f"题目：{item.content}")
            lines.append(f"答案要点：{item.standard_answer}")
            if item.follow_up_suggestions:
                lines.append(f"可追问：{'；'.join(item.follow_up_suggestions[:2])}")
            if item.source_title:
                lines.append(f"来源：{item.source_title}")
            lines.append("")
        return "\n".join(lines).strip()

    @classmethod
    def _score_item(cls, query_tokens: set[str], item) -> float:
        title = item.title.lower()
        category = item.category.lower()
        difficulty = item.difficulty.lower()
        content = item.content.lower()
        answer = item.standard_answer.lower()
        source_title = (item.source_title or "").lower()
        tags = [tag.lower() for tag in item.tags]

        score = 0.0
        for token in query_tokens:
            if not token:
                continue
            if token in title:
                score += 5.0
            if token in category:
                score += 4.0
            if token in tags:
                score += 4.0
            if token in difficulty:
                score += 1.0
            if token in content:
                score += 2.0
            if token in answer:
                score += 1.5
            if token in source_title:
                score += 1.0

        if score > 0:
            score += min(len(item.tags) * 0.1, 0.6)
        return score

    @classmethod
    def _tokenize(cls, text: str) -> set[str]:
        normalized = text.lower()
        tokens: set[str] = set()

        for token in re.findall(r"[a-z0-9_+\-#.]{2,}", normalized):
            tokens.add(token)

        for chunk in re.findall(r"[\u4e00-\u9fff]{2,}", normalized):
            tokens.add(chunk)
            if len(chunk) <= 4:
                tokens.add(chunk[:2])
                tokens.add(chunk[-2:])
                continue
            for size in (2, 3, 4):
                if len(chunk) < size:
                    continue
                for index in range(len(chunk) - size + 1):
                    tokens.add(chunk[index : index + size])

        return {token for token in tokens if token.strip()}
