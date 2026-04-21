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
        query = self._build_opening_query(payload)
        knowledge_pack = self.tools.retrieve_question_bank_context.run(query=query, top_k=3)
        resume_pack = self.tools.retrieve_resume_context.run(
            resume_text=payload.resume_text,
            query=query,
            top_k=3,
        )
        opening_question = self.tools.generate_opening_question.run(
            payload,
            knowledge_context=knowledge_pack.formatted_context,
            resume_context=resume_pack.formatted_context,
        )
        reason = "结合简历与题库知识库生成首轮问题。" if payload.resume_text else "基于题库知识库召回的首轮问题。"
        self.tools.append_question_turn.run(
            interview_id=interview.id,
            turn_index=1,
            question_text=opening_question,
            question_kind="opening",
            followup_reason=reason,
            knowledge_refs=self._serialize_knowledge_refs(knowledge_pack.items),
            resume_refs=self._serialize_resume_refs(resume_pack.items),
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
            resume_attached=bool(interview.resume_text),
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

        query = self._build_followup_query(refreshed_state)
        knowledge_pack = self.tools.retrieve_question_bank_context.run(query=query, top_k=3)
        resume_pack = self.tools.retrieve_resume_context.run(
            resume_text=refreshed_state.interview.resume_text,
            query=query,
            top_k=3,
        )
        next_question = self.tools.generate_followup_question.run(
            refreshed_state,
            knowledge_context=knowledge_pack.formatted_context,
            resume_context=resume_pack.formatted_context,
        )
        reason = (
            "结合候选人回答、简历片段与题库知识库继续追问。"
            if refreshed_state.interview.resume_text
            else "结合候选人回答与题库知识库继续追问。"
        )
        self.tools.append_question_turn.run(
            interview_id=interview_id,
            turn_index=refreshed_state.answered_turns + 1,
            question_text=next_question,
            question_kind="followup",
            followup_reason=reason,
            knowledge_refs=self._serialize_knowledge_refs(knowledge_pack.items),
            resume_refs=self._serialize_resume_refs(resume_pack.items),
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

    @staticmethod
    def _build_opening_query(payload: InterviewCreateRequest) -> str:
        return " ".join(
            [
                payload.target_role,
                payload.level,
                payload.round_type,
                payload.resume_text or "",
                "Agent",
                "Workflow",
                "Tools",
                "记忆",
                "规划",
                "多智能体",
                "Function Calling",
                "MCP",
            ]
        )

    @staticmethod
    def _build_followup_query(state: InterviewAgentState) -> str:
        latest_turn = state.latest_turn
        latest_answer = latest_turn.candidate_answer if latest_turn and latest_turn.candidate_answer else ""
        latest_question = latest_turn.question_text if latest_turn else ""
        return " ".join(
            [
                state.interview.target_role,
                state.interview.level,
                state.interview.round_type,
                state.interview.resume_text or "",
                latest_question,
                latest_answer,
                "Agent",
                "记忆",
                "规划",
                "工具调用",
                "Function Calling",
                "MCP",
                "Multi-Agent",
            ]
        )

    @staticmethod
    def _serialize_knowledge_refs(items) -> list[dict]:
        return [
            {
                "id": item.id,
                "title": item.title,
                "category": item.category,
                "difficulty": item.difficulty,
                "source_title": item.source_title,
                "source_url": item.source_url,
            }
            for item in items
        ]

    @staticmethod
    def _serialize_resume_refs(items) -> list[dict]:
        return [
            {
                "snippet_id": item.snippet_id,
                "section_title": item.section_title,
                "excerpt": item.excerpt,
            }
            for item in items
        ]
