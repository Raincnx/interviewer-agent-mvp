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
    )

    toolkit.append_question_turn.context.turn_repo.create.assert_called_once_with(
        interview_id="interview-1",
        turn_index=2,
        question_text="请继续说明这个方案的取舍。",
        question_kind="followup",
        followup_reason="基于上一轮回答继续追问。",
    )
