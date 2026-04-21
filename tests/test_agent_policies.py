from types import SimpleNamespace

from app.agent.policies import AgentDecision, decide_next_step


def test_agent_policy_returns_existing_report_for_finished_interview() -> None:
    state = SimpleNamespace(
        is_finished=True,
        report={"overall_score": 78},
        answered_turns=5,
        interview=SimpleNamespace(max_turns=5),
    )

    assert decide_next_step(state) is AgentDecision.RETURN_EXISTING_REPORT


def test_agent_policy_finishes_when_max_turns_are_reached() -> None:
    state = SimpleNamespace(
        is_finished=False,
        report=None,
        answered_turns=5,
        interview=SimpleNamespace(max_turns=5),
    )

    assert decide_next_step(state) is AgentDecision.FINISH_AND_SCORE


def test_agent_policy_asks_followup_when_interview_should_continue() -> None:
    state = SimpleNamespace(
        is_finished=False,
        report=None,
        answered_turns=2,
        interview=SimpleNamespace(max_turns=5),
    )

    assert decide_next_step(state) is AgentDecision.ASK_FOLLOWUP
