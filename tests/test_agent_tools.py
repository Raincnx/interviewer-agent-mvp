from types import SimpleNamespace
from unittest.mock import Mock

from app.agent.tools import InterviewAgentToolkit
from app.core.config import Settings


def test_toolkit_exposes_explicit_tools() -> None:
    toolkit = InterviewAgentToolkit.build(
        db=Mock(),
        settings=Settings(),
        provider=Mock(),
        interview_repo=Mock(),
        turn_repo=Mock(),
        scoring_service=Mock(),
        report_service=Mock(),
    )

    assert hasattr(toolkit, "create_interview_record")
    assert hasattr(toolkit, "load_state")
    assert hasattr(toolkit, "retrieve_question_bank_context")
    assert hasattr(toolkit, "retrieve_resume_context")
    assert hasattr(toolkit, "generate_opening_question")
    assert hasattr(toolkit, "generate_followup_question")
    assert hasattr(toolkit, "append_question_turn")
    assert hasattr(toolkit, "record_candidate_answer")
    assert hasattr(toolkit, "ensure_report")
    assert hasattr(toolkit, "flush")
    assert hasattr(toolkit, "commit")


def test_toolkit_registry_exposes_metadata() -> None:
    toolkit = InterviewAgentToolkit.build(
        db=Mock(),
        settings=Settings(),
        provider=Mock(),
        interview_repo=Mock(),
        turn_repo=Mock(),
        scoring_service=Mock(),
        report_service=Mock(),
    )

    metadata = toolkit.list_metadata()
    names = {item.name for item in metadata}

    assert "create_interview_record" in names
    assert "retrieve_question_bank_context" in names
    assert "retrieve_resume_context" in names
    assert "generate_followup_question" in names
    assert "ensure_report" in names
    assert toolkit.get_tool("append_question_turn").metadata.description


def test_append_question_turn_tool_delegates_to_repository() -> None:
    toolkit = InterviewAgentToolkit.build(
        db=Mock(),
        settings=Settings(),
        provider=Mock(),
        interview_repo=Mock(),
        turn_repo=Mock(),
        scoring_service=Mock(),
        report_service=Mock(),
    )

    toolkit.append_question_turn.run(
        interview_id="interview-1",
        turn_index=2,
        question_text="请继续说明这个方案的取舍。",
        question_kind="followup",
        followup_reason="基于上一轮回答继续追问。",
        knowledge_refs=[{"id": "q-1", "title": "什么是 Agent？"}],
        resume_refs=[{"snippet_id": "resume-1", "section_title": "项目经历", "excerpt": "负责 Agent 平台开发"}],
    )

    toolkit.append_question_turn.context.turn_repo.create.assert_called_once()
    _, kwargs = toolkit.append_question_turn.context.turn_repo.create.call_args
    assert kwargs["interview_id"] == "interview-1"
    assert kwargs["question_text"] == "请继续说明这个方案的取舍。"
    assert "什么是 Agent？" in kwargs["knowledge_refs_json"]
    assert "负责 Agent 平台开发" in kwargs["resume_refs_json"]


def test_opening_question_tool_returns_fixed_self_intro_prompt() -> None:
    provider = Mock()

    question_rag_service = Mock()
    question_rag_service.retrieve.return_value = [
        SimpleNamespace(
            id="q-1",
            title="什么是 Agent？",
            category="AI Agent 概念与架构",
            difficulty="中等",
            content="解释 Agent 的核心组件。",
            standard_answer="需要说明规划、记忆和工具调用。",
            follow_up_suggestions=["如何设计记忆？", "如何接工具？"],
            tags=["agent", "memory"],
            source_title="示例来源",
            source_url="https://example.com",
            score=9.0,
        )
    ]

    resume_rag_service = Mock()
    resume_rag_service.retrieve.return_value = [
        SimpleNamespace(
            snippet_id="resume-1",
            section_title="项目：多智能体编排平台",
            excerpt="负责多智能体编排平台开发。",
            score=7.0,
        )
    ]

    toolkit = InterviewAgentToolkit.build(
        db=Mock(),
        settings=Settings(),
        provider=provider,
        interview_repo=Mock(),
        turn_repo=Mock(),
        scoring_service=Mock(),
        report_service=Mock(),
        question_rag_service=question_rag_service,
        resume_rag_service=resume_rag_service,
    )

    knowledge_pack = toolkit.retrieve_question_bank_context.run(query="Agent 记忆")
    resume_pack = toolkit.retrieve_resume_context.run(resume_text="负责多智能体编排平台开发。", query="多智能体")
    question = toolkit.generate_opening_question.run(
        SimpleNamespace(
            target_role="AI Agent 开发工程师",
            level="中级",
            resume_text="负责多智能体编排平台开发。",
        ),
        knowledge_context=knowledge_pack.formatted_context,
        resume_context=resume_pack.formatted_context,
    )

    assert "自我介绍" in question
    provider.generate_text.assert_not_called()
