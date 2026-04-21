from types import SimpleNamespace

from app.domain.services.question_rag_service import QuestionRAGService
from app.domain.services.resume_rag_service import ResumeRAGService


class StubQuestionBankService:
    def __init__(self, items):
        self._items = items

    def list_questions(self):
        return self._items


def test_question_rag_service_prefers_more_relevant_questions() -> None:
    service = QuestionRAGService(
        StubQuestionBankService(
            [
                SimpleNamespace(
                    id="1",
                    title="什么是 Agent？",
                    category="AI Agent 概念与架构",
                    difficulty="中等",
                    content="请解释 Agent 的规划、记忆和工具调用。",
                    standard_answer="需要说明闭环、自主决策和工具调用。",
                    follow_up_suggestions=["为什么需要记忆？"],
                    tags=["agent", "memory", "tool-use"],
                    source_title="示例来源",
                    source_url="https://example.com/agent",
                ),
                SimpleNamespace(
                    id="2",
                    title="Redis 为什么快？",
                    category="后端基础",
                    difficulty="简单",
                    content="请解释 Redis 的性能来源。",
                    standard_answer="内存、单线程、IO 多路复用。",
                    follow_up_suggestions=["持久化怎么做？"],
                    tags=["redis", "backend"],
                    source_title="示例来源",
                    source_url="https://example.com/redis",
                ),
            ]
        )
    )

    results = service.retrieve("Agent 记忆 工具调用", top_k=2)

    assert len(results) == 1
    assert results[0].title == "什么是 Agent？"
    assert results[0].score > 0


def test_question_rag_service_formats_context() -> None:
    formatted = QuestionRAGService.format_context(
        [
            SimpleNamespace(
                title="什么是 Agent？",
                category="AI Agent 概念与架构",
                difficulty="中等",
                content="解释 Agent 的核心组件。",
                standard_answer="需要说明规划、记忆、工具调用。",
                follow_up_suggestions=["如何设计记忆？", "如何接工具？"],
                tags=["agent", "memory"],
                source_title="示例来源",
            )
        ]
    )

    assert "参考题 1" in formatted
    assert "什么是 Agent？" in formatted
    assert "如何设计记忆？" in formatted


def test_resume_rag_service_retrieves_relevant_project_snippets() -> None:
    service = ResumeRAGService()
    results = service.retrieve(
        "项目经历\n多智能体编排平台\n负责多智能体编排平台开发，落地了工具调用与记忆管理。\n\n技能栈\nPython FastAPI RAG",
        "多智能体 记忆 工具调用",
        top_k=2,
    )

    assert results
    assert "多智能体编排平台" in results[0].section_title
    assert results[0].score > 0
