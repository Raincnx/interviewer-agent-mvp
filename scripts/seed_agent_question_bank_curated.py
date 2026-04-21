from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import Settings
from app.db.base import Base
from app.domain.schemas.question_bank import InterviewQuestion
from app.domain.services.question_bank_service import QuestionBankService
from app.infra.repositories.question_bank_repo import QuestionBankRepository


CURATED_QUESTIONS: list[InterviewQuestion] = [
    InterviewQuestion(
        title="Agent 的基本架构由哪些核心组件构成？",
        category="AI Agent 概念与架构",
        difficulty="中等",
        content="请介绍一个完整 AI Agent 系统的核心组件，并说明各组件分别承担什么职责。",
        standard_answer="一个完整 Agent 通常包含 LLM、规划模块、工具调用层、记忆模块、状态管理与执行循环。LLM 负责理解任务和决策，规划模块负责拆解复杂目标，工具层负责访问外部能力，记忆模块负责保留短期与长期上下文，执行循环负责把感知、决策、行动、反馈串成闭环。",
        follow_up_suggestions=[
            "如果只保留 LLM 和工具，不做规划和记忆，会出现什么问题？",
            "这些模块里哪一层最适合做工程可观测性？为什么？",
        ],
        tags=["agent", "architecture", "llm", "memory", "planning"],
        source_url="https://xiaolinnote.com/ai/agent/2_components.html",
        source_title="小林面试笔记 - Agent 的基本架构由哪些核心组件构成？",
    ),
    InterviewQuestion(
        title="Agent 推理模式有哪些？ReAct 是什么？",
        category="AI Agent 设计范式",
        difficulty="中等",
        content="请介绍 Agent 常见推理模式，并重点讲清楚 ReAct 的工作流程和适用场景。",
        standard_answer="ReAct 的核心是 Thought、Action、Observation 循环：模型先思考，再决定调用什么工具，拿到观察结果后继续推理。它适合流程不固定、需要边探索边行动的任务。优点是灵活透明，缺点是长链路任务容易跑偏、上下文会越来越长。",
        follow_up_suggestions=[
            "ReAct 和传统工作流编排最大的工程差异是什么？",
            "如果 ReAct 出现循环调用工具的情况，你会怎么限制？",
        ],
        tags=["agent", "react", "tool-use", "reasoning"],
        source_url="https://xiaolinnote.com/ai/agent/5_react.html",
        source_title="小林面试笔记 - Agent 推理模式有哪些？ReAct 是啥？具体是怎么实现的？",
    ),
    InterviewQuestion(
        title="ReAct、Plan-and-Execute、Reflection 三种范式如何选型？",
        category="AI Agent 设计范式",
        difficulty="困难",
        content="请比较 ReAct、Plan-and-Execute、Reflection 三种 Agent 设计范式，并说明实际项目中该如何选型。",
        standard_answer="ReAct 适合需要灵活探索的任务，Plan-and-Execute 适合长链路复杂任务，Reflection 适合对质量要求高的任务。Reflection 不是单独完整流程，而是叠加在其他范式上的质量增强层。选型时通常看任务复杂度、流程确定性和输出质量要求，工程上也常用混合策略：先规划、再执行、最后反思。",
        follow_up_suggestions=[
            "为什么 Reflection 不能简单理解为 ReAct 的替代方案？",
            "如果你只能选一种范式上线 MVP，会优先选哪种？为什么？",
        ],
        tags=["agent", "react", "plan-and-execute", "reflection", "patterns"],
        source_url="https://xiaolinnote.com/ai/agent/6_three_patterns.html",
        source_title="小林面试笔记 - ReAct、Plan-and-Execute、Reflection 三种范式有什么核心区别？",
    ),
    InterviewQuestion(
        title="复杂任务为什么要做任务拆分？怎么拆？",
        category="AI Agent 工程实践",
        difficulty="中等",
        content="请结合实际项目，说明 Agent 在处理复杂任务时为什么要做任务拆分，以及常见拆分策略有哪些。",
        standard_answer="复杂任务拆分的目的，是降低单次决策难度、提升中间结果可验证性，并让不同步骤可以独立执行和重试。常见方式包括按阶段拆分、按角色拆分、按依赖关系拆分以及按工具类型拆分。拆分后通常要配合状态机、检查点和结果汇总逻辑，否则容易造成步骤漂移或上下文断裂。",
        follow_up_suggestions=[
            "拆得过细和拆得过粗分别有什么代价？",
            "你会怎么判断一个拆分方案是否真的提升了效果？",
        ],
        tags=["agent", "task-decomposition", "workflow", "orchestration"],
        source_url="https://xiaolinnote.com/ai/agent/7_tasksplit.html",
        source_title="小林面试笔记 - 复杂任务怎么做任务拆分？为什么要拆分？效果如何提升？",
    ),
    InterviewQuestion(
        title="AI Agent 的记忆机制应该如何设计？",
        category="AI Agent 记忆机制",
        difficulty="中等",
        content="请介绍 AI Agent 的记忆机制，并说明短期记忆、长期记忆在实际开发中应该如何分层设计。",
        standard_answer="短期记忆通常保存当前任务上下文、最近几轮对话、工具返回结果，强调时效性；长期记忆通常保存用户偏好、历史经验、稳定事实，强调跨任务复用。设计时要关注存储粒度、检索时机、写入策略和过期机制，避免把所有内容都塞进上下文窗口导致噪声膨胀。",
        follow_up_suggestions=[
            "哪些信息应该直接进上下文，哪些信息应该走检索？",
            "长期记忆写入过于激进会带来什么问题？",
        ],
        tags=["agent", "memory", "short-term-memory", "long-term-memory"],
        source_url="https://xiaolinnote.com/ai/agent/8_memory.html",
        source_title="小林面试笔记 - AI Agent 的记忆机制，并说明在实际开发中如何设计记忆模块",
    ),
    InterviewQuestion(
        title="Agent 的长短期记忆系统怎么存？粒度怎么设计？",
        category="AI Agent 记忆机制",
        difficulty="困难",
        content="请结合真实系统，说明 Agent 的长短期记忆通常怎么存，存储粒度如何设计，以及记忆在运行时如何被使用。",
        standard_answer="短期记忆常以消息历史、状态快照、任务上下文对象形式保存在运行态或数据库中；长期记忆常以摘要、事件、用户画像、知识片段形式存入结构化库或向量库。粒度要围绕检索单元来设计，既不能粗到无法定位，也不能细到导致碎片化。运行时一般通过规则触发或 LLM 决策触发来检索和写回。",
        follow_up_suggestions=[
            "如果长期记忆存在错误信息，你会如何纠正？",
            "向量库记忆和关系型数据库记忆各适合放什么？",
        ],
        tags=["agent", "memory", "vector-db", "state-management"],
        source_url="https://xiaolinnote.com/ai/agent/9_memory_storage.html",
        source_title="小林面试笔记 - Agent 的长短期记忆系统怎么做的？",
    ),
    InterviewQuestion(
        title="什么是 Multi-Agent？什么时候需要多智能体？",
        category="AI Agent 多智能体",
        difficulty="中等",
        content="请解释什么是 Multi-Agent，以及它相比 Single-Agent 的核心优势与代价。",
        standard_answer="Multi-Agent 是把复杂任务拆给多个具备不同职责的 Agent 协同完成，比如规划、执行、审核、汇总等角色分离。优势在于职责清晰、可并行、专业化更强；代价在于通信协议、状态共享、路由决策、错误传播和成本控制都会更复杂。只有当任务复杂度和角色边界足够明确时，多智能体才真正值得引入。",
        follow_up_suggestions=[
            "哪些场景其实不应该上 Multi-Agent？",
            "多智能体里最容易被低估的工程成本是什么？",
        ],
        tags=["agent", "multi-agent", "collaboration", "routing"],
        source_url="https://xiaolinnote.com/ai/agent/10_multiagent.html",
        source_title="小林面试笔记 - 什么是 Multi-Agent？",
    ),
    InterviewQuestion(
        title="Single-Agent 和 Multi-Agent 应该如何选型？",
        category="AI Agent 多智能体",
        difficulty="中等",
        content="请比较 Single-Agent 与 Multi-Agent 两种设计方案，并说明项目中该如何做选型。",
        standard_answer="如果任务目标单一、步骤不多、上下文集中，Single-Agent 往往更简单稳定；如果任务链路长、角色边界清晰、需要并行处理或专业分工，多智能体更合适。选型时要综合考虑任务复杂度、通信开销、状态共享、调试成本和可观测性，不应为了“高级感”而过度多智能体化。",
        follow_up_suggestions=[
            "如果 Single-Agent 性能不够，你会优先怎么演进而不是直接改成 Multi-Agent？",
            "Multi-Agent 的路由决策是规则好还是 LLM 好？为什么？",
        ],
        tags=["agent", "single-agent", "multi-agent", "architecture"],
        source_url="https://xiaolinnote.com/ai/agent/11_single_multi.html",
        source_title="小林面试笔记 - 说说 Single-Agent 和 Multi-Agent 的设计方案？",
    ),
    InterviewQuestion(
        title="Agent 记忆压缩通常有哪些方法？",
        category="AI Agent 记忆机制",
        difficulty="中等",
        content="请介绍 Agent 记忆压缩的常见方法，并说明各自适用场景。",
        standard_answer="常见方法包括对话摘要、事件抽取、重要性打分、语义聚类、时间衰减和分层存储。核心目标是在上下文窗口有限时保留关键信息、丢弃噪声。压缩策略要兼顾可恢复性和成本，过强压缩会损失细节，过弱压缩会拖垮上下文和检索效率。",
        follow_up_suggestions=[
            "你会如何验证压缩后没有损失关键事实？",
            "哪些任务更适合做摘要式压缩，哪些更适合做事件式压缩？",
        ],
        tags=["agent", "memory", "compression", "context-window"],
        source_url="https://xiaolinnote.com/ai/agent/12_memcompress.html",
        source_title="小林面试笔记 - Agent 记忆压缩通常有哪些方法？",
    ),
    InterviewQuestion(
        title="如何赋予 LLM 规划能力？",
        category="AI Agent 规划能力",
        difficulty="困难",
        content="请解释在 Agent 系统中，LLM 的规划能力通常如何实现，以及工程上如何控制规划质量和成本。",
        standard_answer="LLM 规划能力通常通过显式任务拆解、计划模板、子任务约束、检查点机制和执行反馈闭环来实现。工程上会把规划和执行解耦，必要时采用强模型规划、弱模型执行的混合策略，同时限制计划长度、增加计划校验，避免产生不可执行或成本过高的计划。",
        follow_up_suggestions=[
            "如果模型产出的计划不可执行，你会在哪一层做兜底？",
            "为什么很多项目会把规划模型和执行模型分开？",
        ],
        tags=["agent", "planning", "plan-and-execute", "cost-control"],
        source_url="https://xiaolinnote.com/ai/agent/14_planning.html",
        source_title="小林面试笔记 - 如何赋予 LLM 规划能力？",
    ),
    InterviewQuestion(
        title="Agent 的反思机制为什么重要？怎么实现？",
        category="AI Agent 反思机制",
        difficulty="中等",
        content="请介绍 Agent 中的反思机制，以及它在提高结果质量方面的作用与代价。",
        standard_answer="反思机制本质上是生成、评估、修正的闭环。它通过额外的审查步骤检查输出是否满足目标、是否存在事实错误或逻辑漏洞，再决定是否重试或调整策略。它能显著提升高风险任务的质量，但代价是增加调用次数、延迟与 token 成本，因此通常需要轮次上限和明确的触发条件。",
        follow_up_suggestions=[
            "Reflection 和普通重试有什么本质不同？",
            "在哪些任务里你不会启用反思机制？",
        ],
        tags=["agent", "reflection", "quality-control", "evaluation"],
        source_url="https://xiaolinnote.com/ai/agent/15_reflection.html",
        source_title="小林面试笔记 - 讲讲 Agent 的反思机制？为什么要用反思？",
    ),
    InterviewQuestion(
        title="如何设计多 Agent 的协作与动态切换机制？",
        category="AI Agent 多智能体",
        difficulty="困难",
        content="请介绍多 Agent 协作系统中，角色切换、任务路由和共享状态通常如何设计。",
        standard_answer="多 Agent 协作通常要解决三个核心问题：谁来接任务、任务如何在角色之间流转、共享上下文如何保持一致。常见方案包括规则路由、LLM 路由、显式状态总线和中心调度器。动态切换时要注意角色职责边界、上下文裁剪、错误隔离和回退策略，否则系统会变得难以调试。",
        follow_up_suggestions=[
            "中心调度器和完全自治协作各有什么优缺点？",
            "多 Agent 协作中如何避免上下文在角色之间无限膨胀？",
        ],
        tags=["agent", "multi-agent", "routing", "state-sharing", "orchestration"],
        source_url="https://xiaolinnote.com/ai/agent/16_collab.html",
        source_title="小林面试笔记 - 如何设计多 Agent 的协作与动态切换机制？",
    ),
    InterviewQuestion(
        title="什么是 Function Calling？原理是什么？",
        category="LLM 工具调用",
        difficulty="中等",
        content="请解释什么是 Function Calling，它在 LLM 与工具之间起到什么作用，以及完整调用流程是怎样的。",
        standard_answer="Function Calling 是让模型输出结构化工具调用请求，而不是自然语言描述。开发者先用 schema 描述工具，模型根据当前上下文决定是否调用工具并输出参数，宿主代码执行工具后把结果再塞回上下文，模型再据此生成最终回答。模型负责决策，代码负责执行，这是最重要的职责分离。",
        follow_up_suggestions=[
            "为什么 Function Calling 比自然语言解析更可靠？",
            "如果多个工具都可能匹配，如何降低误调用？",
        ],
        tags=["function-calling", "tool-use", "schema", "llm"],
        source_url="https://xiaolinnote.com/ai/tools/1_function_calling.html",
        source_title="小林面试笔记 - 什么是 Function Calling？原理是什么？",
    ),
    InterviewQuestion(
        title="大模型的 Function Calling 能力是怎么训练出来的？",
        category="LLM 工具调用",
        difficulty="困难",
        content="请介绍大模型的 Function Calling 能力通常是如何训练出来的，以及训练数据长什么样。",
        standard_answer="Function Calling 训练通常依赖结构化监督信号：输入是用户问题与工具定义，输出不是自然语言，而是符合 schema 的 tool_calls JSON。模型通过监督微调和指令数据学习何时调用、调用哪个工具、参数如何填充。高质量训练数据需要覆盖负例、多工具歧义、参数缺失和并行调用等情况。",
        follow_up_suggestions=[
            "为什么训练数据里必须包含“不调用工具”的负例？",
            "你会如何评估一个模型的 Function Calling 能力是否稳定？",
        ],
        tags=["function-calling", "training", "sft", "tool-use"],
        source_url="https://xiaolinnote.com/ai/tools/3_fc_training.html",
        source_title="小林面试笔记 - 大模型的 Function Call 能力是怎么训练出来的？",
    ),
    InterviewQuestion(
        title="Skill 是什么？在多 Agent 系统中有什么作用？",
        category="Agent Skills 与任务路由",
        difficulty="中等",
        content="请解释 Skill 在多 Agent 系统中的含义，以及它和工具描述、Agent 描述之间的区别。",
        standard_answer="Skill 是比单个工具更高层的能力摘要，用来告诉调度器“这个 Agent 擅长处理什么任务”。它主要用于任务匹配、路由和委托，而不是直接执行。与具体工具 schema 相比，Skill 更抽象；与 Agent 全量说明相比，Skill 更适合机器做快速匹配。",
        follow_up_suggestions=[
            "为什么不能只靠工具列表做任务路由？",
            "Skill 设计得过粗或过细会分别带来什么问题？",
        ],
        tags=["skill", "multi-agent", "routing", "a2a"],
        source_url="https://xiaolinnote.com/ai/tools/13_skill.html",
        source_title="小林面试笔记 - Skill 是什么？",
    ),
    InterviewQuestion(
        title="Function Calling、Skill、MCP 三者有什么区别？",
        category="MCP 与 Agent 工具生态",
        difficulty="困难",
        content="请从工程分层的角度，解释 Function Calling、Skill、MCP 三者分别解决什么问题，它们之间是什么关系。",
        standard_answer="Function Calling 是模型与单个工具的调用协议，解决“怎么发起调用”；MCP 是工具的标准化接入与发现机制，解决“工具怎么被统一管理和暴露”；Skill 是 Agent 能力摘要，解决“任务该路由给谁”。三者不是互斥关系，而是从下到上的三个层级：底层调用、中层工具管理、上层任务路由。",
        follow_up_suggestions=[
            "如果没有 MCP，只靠 Function Calling 会在哪些地方变得脆弱？",
            "在真实系统里，Skill 和 MCP 是否可能同时存在？为什么？",
        ],
        tags=["mcp", "function-calling", "skill", "tool-ecosystem", "agent"],
        source_url="https://xiaolinnote.com/ai/tools/15_fc_skill_mcp.html",
        source_title="小林面试笔记 - Function Calling、Skill、MCP 这三个有什么区别？",
    ),
]


def build_session(settings: Settings) -> Session:
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    engine = create_engine(settings.database_url, future=True, connect_args=connect_args)
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        class_=Session,
    )
    return session_local()


def main() -> int:
    settings = Settings()
    db = build_session(settings)
    repo = QuestionBankRepository(db)
    inserted = 0
    skipped = 0

    try:
        for question in CURATED_QUESTIONS:
            fingerprint = QuestionBankService._build_fingerprint(question)
            if repo.get_by_fingerprint(fingerprint):
                skipped += 1
                continue

            repo.create(
                title=question.title,
                category=question.category,
                difficulty=question.difficulty,
                content=question.content,
                standard_answer=question.standard_answer,
                follow_up_suggestions_json=json.dumps(question.follow_up_suggestions, ensure_ascii=False),
                tags_json=json.dumps(question.tags, ensure_ascii=False),
                source_url=question.source_url,
                source_title=question.source_title,
                fingerprint=fingerprint,
            )
            inserted += 1

        db.commit()
        print(f"新增题目: {inserted}")
        print(f"跳过重复: {skipped}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
