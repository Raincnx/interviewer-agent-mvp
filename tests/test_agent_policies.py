from types import SimpleNamespace

from app.agent.loop import InterviewerAgent
from app.agent.policies import AgentDecision, decide_next_step
from app.agent.state import InterviewAgentState
from app.domain.services.question_rag_service import RetrievedKnowledgePack, RetrievedQuestion


def test_agent_policy_returns_existing_report_for_finished_interview() -> None:
    state = SimpleNamespace(
        is_finished=True,
        report={"overall_score": 78},
        answered_turns=8,
        interview=SimpleNamespace(max_turns=8),
    )

    assert decide_next_step(state) is AgentDecision.RETURN_EXISTING_REPORT


def test_agent_policy_finishes_when_max_turns_are_reached() -> None:
    state = SimpleNamespace(
        is_finished=False,
        report=None,
        answered_turns=8,
        interview=SimpleNamespace(max_turns=8),
    )

    assert decide_next_step(state) is AgentDecision.FINISH_AND_SCORE


def test_agent_policy_asks_followup_when_interview_should_continue() -> None:
    state = SimpleNamespace(
        is_finished=False,
        report=None,
        answered_turns=2,
        interview=SimpleNamespace(max_turns=8),
    )

    assert decide_next_step(state) is AgentDecision.ASK_FOLLOWUP


def test_stage_plan_follows_intro_project_fundamentals_and_coding() -> None:
    state = InterviewAgentState(
        interview=SimpleNamespace(max_turns=8, status="running"),
        turns=[],
        report=None,
    )

    plan = state.stage_plan
    assert [item.stage_key for item in plan] == ["intro", "project", "fundamentals", "coding"]
    assert plan[0].target_turns == 1
    assert sum(item.target_turns for item in plan) == 8


def test_level_changes_fundamentals_question_difficulty() -> None:
    knowledge_pack = RetrievedKnowledgePack(
        items=[
            RetrievedQuestion(
                id="q-1",
                title="什么是 Agent？",
                category="AI Agent 概念与架构",
                difficulty="中等",
                content="解释 Agent 的核心组件。",
                standard_answer="说明规划、记忆和工具调用。",
                follow_up_suggestions=[],
                tags=["agent"],
                source_title=None,
                source_url=None,
                score=9.0,
            )
        ],
        formatted_context="",
    )
    intern_state = InterviewAgentState(
        interview=SimpleNamespace(max_turns=8, status="running", target_role="AI Agent 开发工程师", level="实习"),
        turns=[],
        report=None,
    )
    senior_state = InterviewAgentState(
        interview=SimpleNamespace(max_turns=8, status="running", target_role="AI Agent 开发工程师", level="高级"),
        turns=[],
        report=None,
    )

    intern_question = InterviewerAgent._build_fundamentals_question(intern_state, knowledge_pack)
    senior_question = InterviewerAgent._build_fundamentals_question(senior_state, knowledge_pack)

    assert "什么是 Function Calling" in intern_question
    assert "协议边界" in senior_question
    assert intern_question != senior_question


def test_level_changes_coding_question_difficulty() -> None:
    intern_state = InterviewAgentState(
        interview=SimpleNamespace(max_turns=8, status="running", target_role="后端工程师", level="实习"),
        turns=[],
        report=None,
    )
    principal_state = InterviewAgentState(
        interview=SimpleNamespace(max_turns=8, status="running", target_role="后端工程师", level="资深"),
        turns=[],
        report=None,
    )

    intern_question = InterviewerAgent._build_coding_question(intern_state)
    principal_question = InterviewerAgent._build_coding_question(principal_state)

    assert "两数之和" in intern_question
    assert "TTL" in principal_question
    assert intern_question != principal_question
