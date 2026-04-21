from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.agent.state import InterviewAgentState
from app.core.config import Settings
from app.core.prompts import PromptStore
from app.db.models.turn import Turn
from app.domain.schemas.interview import InterviewCreateRequest
from app.domain.schemas.report import ReportRead
from app.domain.services.report_service import ReportService
from app.domain.services.scoring_service import ScoringService
from app.infra.llm.base import BaseLLMProvider
from app.infra.repositories.interview_repo import InterviewRepository
from app.infra.repositories.turn_repo import TurnRepository


@dataclass(frozen=True)
class AgentToolMetadata:
    name: str
    description: str
    input_summary: str
    output_summary: str


@dataclass
class InterviewAgentToolContext:
    db: Session
    settings: Settings
    provider: BaseLLMProvider
    interview_repo: InterviewRepository
    turn_repo: TurnRepository
    scoring_service: ScoringService
    report_service: ReportService
    prompt_store: PromptStore


class AgentTool:
    metadata: AgentToolMetadata

    def __init__(self, context: InterviewAgentToolContext) -> None:
        self.context = context


class CreateInterviewRecordTool(AgentTool):
    metadata = AgentToolMetadata(
        name="create_interview_record",
        description="创建一条新的面试记录，初始化本场面试的基础配置。",
        input_summary="InterviewCreateRequest",
        output_summary="Interview ORM object",
    )

    def run(self, payload: InterviewCreateRequest):
        return self.context.interview_repo.create(
            target_role=payload.target_role,
            level=payload.level,
            round_type=payload.round_type,
            status="running",
            provider=self.context.settings.llm_provider,
            model_name=self.context.settings.llm_model,
            prompt_version=self.context.prompt_store.version,
            max_turns=self.context.settings.max_turns,
        )


class LoadInterviewStateTool(AgentTool):
    metadata = AgentToolMetadata(
        name="load_interview_state",
        description="读取一场面试的当前状态，包括面试主体、所有轮次和已有报告。",
        input_summary="interview_id",
        output_summary="InterviewAgentState or None",
    )

    def run(self, interview_id: str) -> Optional[InterviewAgentState]:
        interview = self.context.interview_repo.get_by_id(interview_id)
        if interview is None:
            return None

        turns = sorted(interview.turns, key=lambda item: item.turn_index)
        report = self.context.report_service.get_report(interview_id)
        return InterviewAgentState(interview=interview, turns=turns, report=report)


class GenerateOpeningQuestionTool(AgentTool):
    metadata = AgentToolMetadata(
        name="generate_opening_question",
        description="基于面试配置生成首轮问题。",
        input_summary="InterviewCreateRequest",
        output_summary="question text",
    )

    def run(self, payload: InterviewCreateRequest) -> str:
        system_prompt = self.context.prompt_store.read("interviewer_system")
        user_prompt = f"""
现在开始一场新的技术面试。
岗位：{payload.target_role}
级别：{payload.level}
轮次：{payload.round_type}

请直接给出第一道面试问题，不要寒暄，不要解释规则。
        """.strip()
        return self.context.provider.generate_text(system_prompt=system_prompt, user_prompt=user_prompt)


class GenerateFollowupQuestionTool(AgentTool):
    metadata = AgentToolMetadata(
        name="generate_followup_question",
        description="基于当前面试状态生成下一轮追问或新问题。",
        input_summary="InterviewAgentState",
        output_summary="question text",
    )

    def run(self, state: InterviewAgentState) -> str:
        system_prompt = self.context.prompt_store.read("interviewer_system")
        user_prompt = f"""
岗位：{state.interview.target_role}
级别：{state.interview.level}
轮次：{state.interview.round_type}

下面是当前完整对话记录：
{state.build_transcript()}

请只输出面试官下一句要说的话。
优先基于候选人刚才的回答继续追问。
如果回答已经比较完整，再切到下一个相关问题。
        """.strip()
        return self.context.provider.generate_text(system_prompt=system_prompt, user_prompt=user_prompt)


class AppendQuestionTurnTool(AgentTool):
    metadata = AgentToolMetadata(
        name="append_question_turn",
        description="向面试中追加一轮新的问题记录。",
        input_summary="interview_id, turn_index, question_text, question_kind, followup_reason",
        output_summary="Turn ORM object",
    )

    def run(
        self,
        *,
        interview_id: str,
        turn_index: int,
        question_text: str,
        question_kind: str,
        followup_reason: Optional[str] = None,
    ) -> Turn:
        return self.context.turn_repo.create(
            interview_id=interview_id,
            turn_index=turn_index,
            question_text=question_text,
            question_kind=question_kind,
            followup_reason=followup_reason,
        )


class RecordCandidateAnswerTool(AgentTool):
    metadata = AgentToolMetadata(
        name="record_candidate_answer",
        description="为当前轮次写入候选人的回答。",
        input_summary="Turn, answer text",
        output_summary="updated Turn ORM object",
    )

    def run(self, turn: Turn, answer: str) -> Turn:
        return self.context.turn_repo.set_answer(turn, answer)


class EnsureReportTool(AgentTool):
    metadata = AgentToolMetadata(
        name="ensure_report",
        description="确保面试拥有最终报告；若没有则生成并落库。",
        input_summary="InterviewAgentState",
        output_summary="ReportRead",
    )

    def run(self, state: InterviewAgentState) -> ReportRead:
        if state.report is not None:
            self.context.interview_repo.update_status(state.interview, "finished")
            self.context.db.commit()
            return state.report

        payload = self.context.scoring_service.generate_report_payload(
            transcript=state.build_transcript(),
            meta={
                "target_role": state.interview.target_role,
                "level": state.interview.level,
                "round_type": state.interview.round_type,
            },
        )
        report = self.context.report_service.create_report(state.interview.id, payload)
        self.context.interview_repo.update_status(state.interview, "finished")
        self.context.db.commit()
        return report


class FlushTool(AgentTool):
    metadata = AgentToolMetadata(
        name="flush_session",
        description="将当前数据库会话中的变更刷入事务上下文，但不提交。",
        input_summary="None",
        output_summary="None",
    )

    def run(self) -> None:
        self.context.db.flush()


class CommitTool(AgentTool):
    metadata = AgentToolMetadata(
        name="commit_session",
        description="提交当前数据库事务。",
        input_summary="None",
        output_summary="None",
    )

    def run(self) -> None:
        self.context.db.commit()


@dataclass
class InterviewAgentToolkit:
    create_interview_record: CreateInterviewRecordTool
    load_state: LoadInterviewStateTool
    generate_opening_question: GenerateOpeningQuestionTool
    generate_followup_question: GenerateFollowupQuestionTool
    append_question_turn: AppendQuestionTurnTool
    record_candidate_answer: RecordCandidateAnswerTool
    ensure_report: EnsureReportTool
    flush: FlushTool
    commit: CommitTool
    registry: Dict[str, AgentTool]

    def get_tool(self, name: str) -> AgentTool:
        return self.registry[name]

    def list_metadata(self) -> List[AgentToolMetadata]:
        return [tool.metadata for tool in self.registry.values()]

    @classmethod
    def build(
        cls,
        *,
        db: Session,
        settings: Settings,
        provider: BaseLLMProvider,
        interview_repo: InterviewRepository,
        turn_repo: TurnRepository,
        scoring_service: ScoringService,
        report_service: ReportService,
    ) -> "InterviewAgentToolkit":
        prompts_dir = Path(__file__).resolve().parents[1] / "prompts"
        context = InterviewAgentToolContext(
            db=db,
            settings=settings,
            provider=provider,
            interview_repo=interview_repo,
            turn_repo=turn_repo,
            scoring_service=scoring_service,
            report_service=report_service,
            prompt_store=PromptStore(prompts_dir, settings.prompt_version),
        )

        toolkit = cls(
            create_interview_record=CreateInterviewRecordTool(context),
            load_state=LoadInterviewStateTool(context),
            generate_opening_question=GenerateOpeningQuestionTool(context),
            generate_followup_question=GenerateFollowupQuestionTool(context),
            append_question_turn=AppendQuestionTurnTool(context),
            record_candidate_answer=RecordCandidateAnswerTool(context),
            ensure_report=EnsureReportTool(context),
            flush=FlushTool(context),
            commit=CommitTool(context),
            registry={},
        )
        toolkit.registry = {
            toolkit.create_interview_record.metadata.name: toolkit.create_interview_record,
            toolkit.load_state.metadata.name: toolkit.load_state,
            toolkit.generate_opening_question.metadata.name: toolkit.generate_opening_question,
            toolkit.generate_followup_question.metadata.name: toolkit.generate_followup_question,
            toolkit.append_question_turn.metadata.name: toolkit.append_question_turn,
            toolkit.record_candidate_answer.metadata.name: toolkit.record_candidate_answer,
            toolkit.ensure_report.metadata.name: toolkit.ensure_report,
            toolkit.flush.metadata.name: toolkit.flush,
            toolkit.commit.metadata.name: toolkit.commit,
        }
        return toolkit
