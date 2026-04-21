from __future__ import annotations

import json
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
from app.domain.services.question_rag_service import QuestionRAGService, RetrievedKnowledgePack
from app.domain.services.report_service import ReportService
from app.domain.services.resume_parser_service import ResumeParserService
from app.domain.services.resume_rag_service import ResumeRAGService, RetrievedResumePack
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
    question_rag_service: QuestionRAGService | None = None
    resume_rag_service: ResumeRAGService | None = None


class AgentTool:
    metadata: AgentToolMetadata

    def __init__(self, context: InterviewAgentToolContext) -> None:
        self.context = context


class CreateInterviewRecordTool(AgentTool):
    metadata = AgentToolMetadata(
        name="create_interview_record",
        description="创建新的面试记录，并初始化基础配置与可选的简历内容。",
        input_summary="InterviewCreateRequest",
        output_summary="Interview ORM object",
    )

    def run(self, payload: InterviewCreateRequest):
        return self.context.interview_repo.create(
            target_role=payload.target_role,
            level=payload.level,
            status="running",
            provider=self.context.settings.llm_provider,
            model_name=self.context.settings.llm_model,
            prompt_version=self.context.prompt_store.version,
            max_turns=self.context.settings.max_turns,
            resume_filename=payload.resume_filename,
            resume_text=payload.resume_text,
        )


class LoadInterviewStateTool(AgentTool):
    metadata = AgentToolMetadata(
        name="load_interview_state",
        description="读取一场面试的当前状态，包括面试主体、轮次、简历与报告。",
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


class RetrieveQuestionBankContextTool(AgentTool):
    metadata = AgentToolMetadata(
        name="retrieve_question_bank_context",
        description="从题库知识库检索与当前面试主题最相关的参考题，供问题生成时做 RAG 增强。",
        input_summary="query, top_k",
        output_summary="RetrievedKnowledgePack",
    )

    def run(self, *, query: str, top_k: int = 3) -> RetrievedKnowledgePack:
        if self.context.question_rag_service is None:
            return RetrievedKnowledgePack(items=[], formatted_context="暂无可用题库参考。")

        items = self.context.question_rag_service.retrieve(query, top_k=top_k)
        return RetrievedKnowledgePack(items=items, formatted_context=QuestionRAGService.format_context(items))


class RetrieveResumeContextTool(AgentTool):
    metadata = AgentToolMetadata(
        name="retrieve_resume_context",
        description="从候选人简历中检索与当前追问最相关的项目或片段，供个性化发问。",
        input_summary="resume_text, query, top_k",
        output_summary="RetrievedResumePack",
    )

    def run(self, *, resume_text: str | None, query: str, top_k: int = 3) -> RetrievedResumePack:
        if self.context.resume_rag_service is None or not (resume_text or "").strip():
            return RetrievedResumePack(items=[], formatted_context="暂无可用简历参考。")

        profile = ResumeParserService.extract_profile(resume_text or "")
        items = self.context.resume_rag_service.retrieve(
            resume_text or "",
            query,
            top_k=top_k,
            profile=profile,
        )
        return RetrievedResumePack(items=items, formatted_context=ResumeRAGService.format_context(items))


class GenerateOpeningQuestionTool(AgentTool):
    metadata = AgentToolMetadata(
        name="generate_opening_question",
        description="生成首轮自我介绍问题，可同时结合简历与题库知识。",
        input_summary="InterviewCreateRequest, knowledge_context, resume_context",
        output_summary="question text",
    )

    def run(
        self,
        payload: InterviewCreateRequest,
        *,
        stage_label: str = "自我介绍",
        stage_focus: str = "",
        knowledge_context: str = "",
        resume_context: str = "",
    ) -> str:
        return (
            "我们先用 3-5 分钟做个自我介绍。请你从当前最相关的一段项目或实习经历开始，"
            "讲讲你的背景、做过什么、最拿得出手的成果，以及为什么想来面这个岗位。"
        )


class GenerateFollowupQuestionTool(AgentTool):
    metadata = AgentToolMetadata(
        name="generate_followup_question",
        description="基于当前面试状态生成同阶段追问，可同时结合简历与题库。",
        input_summary="InterviewAgentState, knowledge_context, resume_context",
        output_summary="question text",
    )

    def run(
        self,
        state: InterviewAgentState,
        *,
        stage_label: str = "项目 / 实习深挖",
        stage_focus: str = "",
        knowledge_context: str = "",
        resume_context: str = "",
    ) -> str:
        system_prompt = self.context.prompt_store.read("interviewer_system")
        knowledge_block = knowledge_context.strip() or "暂无可用题库参考。"
        resume_block = resume_context.strip() or "暂无可用简历参考。"
        user_prompt = f"""
岗位：{state.interview.target_role}
级别：{state.interview.level}
当前阶段：{stage_label}
阶段目标：{stage_focus}
预计剩余时间：{state.estimated_remaining_minutes} 分钟

下面是当前完整对话记录：
{state.build_transcript()}

下面是候选人的简历画像与相关片段：
{resume_block}

下面是从题库知识库里召回的参考材料：
{knowledge_block}

请只输出面试官下一句要说的话，要求：
1. 只在当前阶段内追问，不要跨阶段继续追旧话题。
2. 必须匹配当前级别的难度：
   - 实习：问题更基础，允许更多提示，重点看潜力和思路。
   - 中级：问题覆盖原理与落地，要求能说明常见取舍。
   - 高级：问题要更强调复杂场景、边界条件、稳定性和系统设计。
   - 资深：问题要明显提高抽象层次，关注架构演进、团队决策与 trade-off。
3. 如果当前阶段是项目 / 实习深挖，就追问方案、取舍、指标、失败复盘。
4. 如果当前阶段是八股基础，就明确切到基础原理、系统设计或工程常识，不要继续深挖某个具体项目。
5. 如果当前阶段是 LeetCode 手撕，就围绕算法题的思路、复杂度和编码表达发问。
6. 问题要具体、自然、像真实面试官。
        """.strip()
        return self.context.provider.generate_text(system_prompt=system_prompt, user_prompt=user_prompt)


class AppendQuestionTurnTool(AgentTool):
    metadata = AgentToolMetadata(
        name="append_question_turn",
        description="向面试中追加一轮新问题记录，并持久化引用的题库/简历片段。",
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
        knowledge_refs: Optional[list[dict]] = None,
        resume_refs: Optional[list[dict]] = None,
    ) -> Turn:
        return self.context.turn_repo.create(
            interview_id=interview_id,
            turn_index=turn_index,
            question_text=question_text,
            question_kind=question_kind,
            followup_reason=followup_reason,
            knowledge_refs_json=json.dumps(knowledge_refs or [], ensure_ascii=False),
            resume_refs_json=json.dumps(resume_refs or [], ensure_ascii=False),
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
        description="确保面试拥有最终报告；如果没有则生成并落库。",
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
    retrieve_question_bank_context: RetrieveQuestionBankContextTool
    retrieve_resume_context: RetrieveResumeContextTool
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
        question_rag_service: QuestionRAGService | None = None,
        resume_rag_service: ResumeRAGService | None = None,
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
            question_rag_service=question_rag_service,
            resume_rag_service=resume_rag_service,
        )

        toolkit = cls(
            create_interview_record=CreateInterviewRecordTool(context),
            load_state=LoadInterviewStateTool(context),
            retrieve_question_bank_context=RetrieveQuestionBankContextTool(context),
            retrieve_resume_context=RetrieveResumeContextTool(context),
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
            toolkit.retrieve_question_bank_context.metadata.name: toolkit.retrieve_question_bank_context,
            toolkit.retrieve_resume_context.metadata.name: toolkit.retrieve_resume_context,
            toolkit.generate_opening_question.metadata.name: toolkit.generate_opening_question,
            toolkit.generate_followup_question.metadata.name: toolkit.generate_followup_question,
            toolkit.append_question_turn.metadata.name: toolkit.append_question_turn,
            toolkit.record_candidate_answer.metadata.name: toolkit.record_candidate_answer,
            toolkit.ensure_report.metadata.name: toolkit.ensure_report,
            toolkit.flush.metadata.name: toolkit.flush,
            toolkit.commit.metadata.name: toolkit.commit,
        }
        return toolkit
