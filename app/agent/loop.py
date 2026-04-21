from __future__ import annotations

from fastapi import HTTPException

from app.agent.policies import AgentDecision, decide_next_step
from app.agent.state import InterviewAgentState, InterviewStageRuntime
from app.agent.tools import InterviewAgentToolkit
from app.domain.schemas.interview import (
    FinishInterviewResponse,
    InterviewCreateRequest,
    InterviewCreateResponse,
    ReplyResponse,
)
from app.domain.services.question_rag_service import RetrievedKnowledgePack
from app.domain.services.resume_rag_service import RetrievedResumePack


class InterviewerAgent:
    def __init__(self, tools: InterviewAgentToolkit) -> None:
        self.tools = tools

    def start_interview(self, payload: InterviewCreateRequest) -> InterviewCreateResponse:
        interview = self.tools.create_interview_record.run(payload)
        initial_state = self.tools.load_state.run(interview.id)
        if initial_state is None:
            raise HTTPException(status_code=500, detail="面试初始化失败")

        stage = initial_state.current_stage
        query = self._build_opening_query(payload)
        knowledge_pack = self.tools.retrieve_question_bank_context.run(query=query, top_k=3)
        resume_pack = self.tools.retrieve_resume_context.run(
            resume_text=payload.resume_text,
            query=query,
            top_k=3,
        )
        opening_question = self.tools.generate_opening_question.run(
            payload,
            stage_label=stage.stage_label,
            stage_focus=stage.focus,
            knowledge_context=knowledge_pack.formatted_context,
            resume_context=resume_pack.formatted_context,
        )
        reason = (
            "结合简历与题库知识生成首轮自我介绍问题。"
            if payload.resume_text
            else "基于题库知识生成首轮自我介绍问题。"
        )
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
            current_stage=stage.stage_key,
            current_stage_label=stage.stage_label,
            planned_duration_minutes=initial_state.planned_duration_minutes,
            estimated_elapsed_minutes=initial_state.estimated_elapsed_minutes,
            estimated_remaining_minutes=initial_state.estimated_remaining_minutes,
            stage_plan=[
                {
                    "stage_key": item.stage_key,
                    "stage_label": item.stage_label,
                    "target_turns": item.target_turns,
                    "estimated_minutes": item.estimated_minutes,
                    "focus": item.focus,
                }
                for item in initial_state.stage_plan
            ],
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

        previous_stage = state.current_stage

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

        next_stage = refreshed_state.current_stage
        query = self._build_followup_query(refreshed_state)
        knowledge_pack = self.tools.retrieve_question_bank_context.run(query=query, top_k=3)
        resume_pack = self.tools.retrieve_resume_context.run(
            resume_text=refreshed_state.interview.resume_text,
            query=query,
            top_k=3,
        )

        if previous_stage.stage_key != next_stage.stage_key:
            next_question = self._build_stage_transition_question(
                previous_stage=previous_stage,
                next_stage=next_stage,
                state=refreshed_state,
                knowledge_pack=knowledge_pack,
                resume_pack=resume_pack,
            )
            question_kind = f"{next_stage.stage_key}_transition"
            reason = f"结束{previous_stage.stage_label}阶段后，显式切换到{next_stage.stage_label}阶段。"
        else:
            next_question = self.tools.generate_followup_question.run(
                refreshed_state,
                stage_label=next_stage.stage_label,
                stage_focus=next_stage.focus,
                knowledge_context=knowledge_pack.formatted_context,
                resume_context=resume_pack.formatted_context,
            )
            question_kind = "followup"
            reason = (
                "结合候选人回答、简历片段与题库知识在当前阶段继续追问。"
                if refreshed_state.interview.resume_text
                else "结合候选人回答与题库知识在当前阶段继续追问。"
            )

        self.tools.append_question_turn.run(
            interview_id=interview_id,
            turn_index=refreshed_state.answered_turns + 1,
            question_text=next_question,
            question_kind=question_kind,
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

    def _build_stage_transition_question(
        self,
        *,
        previous_stage: InterviewStageRuntime,
        next_stage: InterviewStageRuntime,
        state: InterviewAgentState,
        knowledge_pack: RetrievedKnowledgePack,
        resume_pack: RetrievedResumePack,
    ) -> str:
        if next_stage.stage_key == "project":
            project_anchor = self._pick_resume_anchor(resume_pack)
            return (
                f"好的，刚才的自我介绍我先听到这里，你的背景和亮点我已经有基本了解了。"
                f"接下来我们进入项目深挖。就从{project_anchor}开始，"
                "请你按项目背景、你的职责、核心技术方案、关键取舍和最终结果，完整讲一遍。"
            )

        if next_stage.stage_key == "fundamentals":
            return (
                "好的，项目部分我先了解到这里，你刚才把背景、方案和取舍讲得比较清楚。"
                "接下来我切到几道基础题，看看你的原理和工程基础。"
                f"{self._build_fundamentals_question(state, knowledge_pack)}"
            )

        if next_stage.stage_key == "coding":
            return (
                "好的，基础部分先到这里。最后我们留 15 到 20 分钟做一道手撕题，"
                "我会先看你的思路，再看代码表达。"
                f"{self._build_coding_question(state)}"
            )

        return self.tools.generate_followup_question.run(
            state,
            stage_label=next_stage.stage_label,
            stage_focus=next_stage.focus,
            knowledge_context=knowledge_pack.formatted_context,
            resume_context=resume_pack.formatted_context,
        )

    @staticmethod
    def _pick_resume_anchor(resume_pack: RetrievedResumePack) -> str:
        if resume_pack.items:
            title = resume_pack.items[0].section_title or "你刚才提到的代表性项目"
            title = title.replace("项目：", "").replace("经历：", "")
            return title
        return "你刚才提到的代表性项目"

    @staticmethod
    def _build_fundamentals_question(state: InterviewAgentState, knowledge_pack: RetrievedKnowledgePack) -> str:
        role = state.interview.target_role.lower()
        knowledge_title = knowledge_pack.items[0].title if knowledge_pack.items else ""
        level = state.interview.level

        if "agent" in role or "llm" in role or "ai" in role:
            if level == "实习":
                return "先说说什么是 Function Calling，它和直接让模型输出一段文本回答相比，最大的区别是什么？"
            if level == "中级":
                return (
                    "先说说 Function Calling、MCP 和普通 prompt chaining 的区别，"
                    "以及在一个 Agent 系统里你会分别把它们放在什么场景下使用？"
                )
            if level == "高级":
                return (
                    "如果一个 Agent 系统同时接了 Function Calling、MCP 和自定义工具总线，"
                    "你会怎么做协议边界、失败重试和可观测性设计，避免整个工具层失控？"
                )
            return (
                "如果你要给公司搭一套通用 Agent 基础设施，"
                "你会如何划分 Function Calling、MCP、记忆层和执行编排层的职责边界，"
                "并说明这样设计对扩展性和治理的价值？"
            )

        if "后端" in state.interview.target_role or "backend" in role:
            if level == "实习":
                return "先说说进程、线程、协程分别是什么，它们最核心的区别是什么？"
            if level == "中级":
                return "先说说进程、线程、协程的区别，以及在高并发服务里你通常怎么选？"
            if level == "高级":
                return "如果一个高并发服务既要低延迟又要可观测性，你会如何在线程池、协程和队列模型之间做取舍？"
            return "如果让你主导一套核心后端服务的并发模型演进，你会怎么平衡吞吐、稳定性、调试复杂度和资源成本？"

        if knowledge_title:
            if level == "实习":
                return f"我们先从一个基础主题开始。你先用自己的话解释一下“{knowledge_title}”是什么。"
            if level == "中级":
                return f"我们先从一个基础主题开始。你怎么理解“{knowledge_title}”背后的核心原理？"
            if level == "高级":
                return f"我们先围绕“{knowledge_title}”聊聊。除了原理本身，你觉得它在线上落地时最难的边界条件是什么？"
            return f"我们先围绕“{knowledge_title}”聊聊。如果让你把它升级成团队级基础能力，你会怎么做架构抽象和演进规划？"

        return "先说说你最常用的一项核心技术背后的原理，以及线上落地时最容易踩的坑。"

    @staticmethod
    def _build_coding_question(state: InterviewAgentState) -> str:
        role = state.interview.target_role.lower()
        level = state.interview.level
        if "后端" in state.interview.target_role or "backend" in role:
            if level == "实习":
                return (
                    "题目是：两数之和。"
                    "你先讲最直接的思路，再优化到哈希表写法，最后再开始写代码。"
                )
            if level == "中级":
                return (
                    "题目是：实现一个支持 `get` 和 `put` 的 LRU Cache。"
                    "你先讲数据结构选择和时间复杂度，再开始写核心代码。"
                )
            if level == "高级":
                return (
                    "题目是：实现一个支持并发访问的 LRU Cache。"
                    "你先说明单机版本的数据结构，再讲线程安全和锁粒度的取舍，最后写核心代码。"
                )
            return (
                "题目是：设计并实现一个支持 TTL、淘汰策略和并发访问的内存缓存组件。"
                "你先拆需求、定接口、分析复杂度，再写你认为最关键的一段代码。"
            )

        if level == "实习":
            return (
                "题目是：给定一个数组，返回出现次数最多的元素。"
                "你先讲最朴素的做法，再说如何用哈希表优化。"
            )
        if level == "中级":
            return (
                "题目是：给定一个字符串，找出其中不含重复字符的最长子串长度。"
                "你先讲思路、复杂度，再开始写代码。"
            )
        if level == "高级":
            return (
                "题目是：合并 K 个有序链表。"
                "你先比较不同解法的复杂度，再写出你认为工程上最稳妥的版本。"
            )
        return (
            "题目是：设计一个支持动态更新和区间查询的数据结构。"
            "你先说清楚抽象思路、复杂度和适用边界，再写关键代码。"
        )

    @staticmethod
    def _build_opening_query(payload: InterviewCreateRequest) -> str:
        return " ".join(
            [
                payload.target_role,
                payload.level,
                payload.resume_text or "",
                "自我介绍",
                "项目经历",
                "实习经历",
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
        stage = state.current_stage.stage_key

        stage_keywords = {
            "project": "项目 实习 技术方案 取舍 指标 复盘",
            "fundamentals": "基础 原理 八股 系统设计 工程实践",
            "coding": "算法 手撕 LeetCode 数据结构 复杂度 编码",
        }

        return " ".join(
            [
                state.interview.target_role,
                state.interview.level,
                state.interview.resume_text or "",
                latest_question,
                latest_answer,
                stage_keywords.get(stage, ""),
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
