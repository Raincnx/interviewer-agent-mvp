from __future__ import annotations

from fastapi import HTTPException

from app.agent.policies import AgentDecision, decide_next_step
from app.agent.state import InterviewAgentState
from app.agent.tools import InterviewAgentToolkit
from app.domain.schemas.interview import (
    FinishInterviewResponse,
    InterviewCreateRequest,
    InterviewCreateResponse,
    ReplyResponse,
)


class InterviewerAgent:
    def __init__(self, tools: InterviewAgentToolkit) -> None:
        self.tools = tools

    def start_interview(self, payload: InterviewCreateRequest) -> InterviewCreateResponse:
        interview = self.tools.create_interview_record.run(payload)
        opening_question = self.tools.generate_opening_question.run(payload)
        self.tools.append_question_turn.run(
            interview_id=interview.id,
            turn_index=1,
            question_text=opening_question,
            question_kind="opening",
        )
        self.tools.commit.run()

        return InterviewCreateResponse(
            interview_id=interview.id,
            status=interview.status,
            question=opening_question,
            max_turns=interview.max_turns,
            provider=interview.provider,
            model_name=interview.model_name,
            prompt_version=interview.prompt_version,
        )

    def handle_reply(self, interview_id: str, answer: str) -> ReplyResponse:
        state = self._load_required_state(interview_id)

        if state.is_finished:
            if state.report is None:
                raise HTTPException(status_code=404, detail="评估报告不存在")
            return ReplyResponse(done=True, report=state.report)

        latest_turn = state.latest_turn
        if latest_turn is None:
            raise HTTPException(status_code=400, detail="当前没有可作答的轮次")

        if latest_turn.candidate_answer:
            raise HTTPException(status_code=400, detail="当前轮次已经回答过了")

        self.tools.record_candidate_answer.run(latest_turn, answer)
        self.tools.flush.run()

        refreshed_state = self._load_required_state(interview_id)
        decision = decide_next_step(refreshed_state)

        if decision is AgentDecision.FINISH_AND_SCORE:
            report = self.tools.ensure_report.run(refreshed_state)
            return ReplyResponse(done=True, report=report)

        if decision is AgentDecision.RETURN_EXISTING_REPORT:
            if refreshed_state.report is None:
                raise HTTPException(status_code=404, detail="评估报告不存在")
            return ReplyResponse(done=True, report=refreshed_state.report)

        next_question = self.tools.generate_followup_question.run(refreshed_state)
        self.tools.append_question_turn.run(
            interview_id=interview_id,
            turn_index=refreshed_state.answered_turns + 1,
            question_text=next_question,
            question_kind="followup",
            followup_reason="基于上一轮回答继续追问。",
        )
        self.tools.commit.run()

        return ReplyResponse(
            done=False,
            question=next_question,
            remaining_turns=refreshed_state.remaining_turns,
        )

    def finish_interview(self, interview_id: str) -> FinishInterviewResponse:
        state = self._load_required_state(interview_id)
        report = self.tools.ensure_report.run(state)
        return FinishInterviewResponse(done=True, report=report)

    def _load_required_state(self, interview_id: str) -> InterviewAgentState:
        state = self.tools.load_state.run(interview_id)
        if state is None:
            raise HTTPException(status_code=404, detail="面试不存在")
        return state
