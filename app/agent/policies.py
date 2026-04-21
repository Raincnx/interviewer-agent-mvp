from __future__ import annotations

from enum import Enum

from app.agent.state import InterviewAgentState


class AgentDecision(str, Enum):
    RETURN_EXISTING_REPORT = "return_existing_report"
    FINISH_AND_SCORE = "finish_and_score"
    ASK_FOLLOWUP = "ask_followup"


def decide_next_step(state: InterviewAgentState) -> AgentDecision:
    if state.is_finished and state.report is not None:
        return AgentDecision.RETURN_EXISTING_REPORT

    if state.answered_turns >= state.interview.max_turns:
        return AgentDecision.FINISH_AND_SCORE

    return AgentDecision.ASK_FOLLOWUP
