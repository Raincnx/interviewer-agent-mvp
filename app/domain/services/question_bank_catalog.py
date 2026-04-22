from __future__ import annotations

from typing import Iterable


CatalogItem = dict[str, object]


def _source(
    *,
    name: str,
    base_url: str,
    category_hint: str,
    max_questions: int,
    job_tracks: list[str],
    source_type: str = "web",
    crawl_strategy: str = "http",
    language: str = "zh-CN",
    use_firecrawl: bool = False,
) -> CatalogItem:
    return {
        "name": name,
        "source_type": source_type,
        "base_url": base_url,
        "language": language,
        "crawl_strategy": crawl_strategy,
        "config": {
            "request_url": base_url,
            "category_hint": category_hint,
            "max_questions": max_questions,
            "use_firecrawl": use_firecrawl,
            "job_tracks": job_tracks,
        },
    }


SOURCE_CATALOG_BY_TRACK: dict[str, list[CatalogItem]] = {
    "ai-agent": [
        _source(
            name="小林面试笔记 Agent 专题 - 什么是 Agent",
            base_url="https://xiaolinnote.com/ai/agent/1_whatisagent.html",
            category_hint="AI Agent 概念与架构",
            max_questions=3,
            job_tracks=["ai-agent"],
        ),
        _source(
            name="小林面试笔记 Agent 专题 - 核心组件",
            base_url="https://xiaolinnote.com/ai/agent/2_components.html",
            category_hint="AI Agent 概念与架构",
            max_questions=3,
            job_tracks=["ai-agent"],
        ),
        _source(
            name="小林面试笔记 Agent 专题 - Workflow 与 Tools",
            base_url="https://xiaolinnote.com/ai/agent/3_workflow_tools.html",
            category_hint="AI Agent 概念与架构",
            max_questions=3,
            job_tracks=["ai-agent"],
        ),
        _source(
            name="小林面试笔记 Agent 专题 - 设计范式",
            base_url="https://xiaolinnote.com/ai/agent/4_patterns.html",
            category_hint="AI Agent 设计范式",
            max_questions=3,
            job_tracks=["ai-agent"],
        ),
        _source(
            name="小林面试笔记 Agent 专题 - ReAct",
            base_url="https://xiaolinnote.com/ai/agent/5_react.html",
            category_hint="AI Agent 设计范式",
            max_questions=3,
            job_tracks=["ai-agent"],
        ),
        _source(
            name="小林面试笔记 Agent 专题 - 记忆机制",
            base_url="https://xiaolinnote.com/ai/agent/8_memory.html",
            category_hint="AI Agent 记忆机制",
            max_questions=3,
            job_tracks=["ai-agent"],
        ),
        _source(
            name="小林面试笔记 Agent 专题 - Multi-Agent",
            base_url="https://xiaolinnote.com/ai/agent/10_multiagent.html",
            category_hint="AI Agent 多智能体",
            max_questions=3,
            job_tracks=["ai-agent"],
        ),
        _source(
            name="小林面试笔记 Agent 专题 - 规划能力",
            base_url="https://xiaolinnote.com/ai/agent/14_planning.html",
            category_hint="AI Agent 规划能力",
            max_questions=3,
            job_tracks=["ai-agent"],
        ),
        _source(
            name="小林面试笔记 Agent 专题 - 反思机制",
            base_url="https://xiaolinnote.com/ai/agent/15_reflection.html",
            category_hint="AI Agent 反思机制",
            max_questions=3,
            job_tracks=["ai-agent"],
        ),
        _source(
            name="小林面试笔记 Agent 专题 - 协作机制",
            base_url="https://xiaolinnote.com/ai/agent/16_collab.html",
            category_hint="AI Agent 多智能体",
            max_questions=3,
            job_tracks=["ai-agent"],
        ),
        _source(
            name="小林面试笔记 Tools - Function Calling",
            base_url="https://xiaolinnote.com/ai/tools/1_function_calling.html",
            category_hint="LLM 工具调用",
            max_questions=3,
            job_tracks=["ai-agent", "ml-engineer"],
        ),
        _source(
            name="小林面试笔记 Tools - Function Calling、Skill、MCP",
            base_url="https://xiaolinnote.com/ai/tools/15_fc_skill_mcp.html",
            category_hint="MCP 与 Agent 工具生态",
            max_questions=3,
            job_tracks=["ai-agent"],
        ),
        _source(
            name="Datawhale hello-agents README",
            base_url="https://raw.githubusercontent.com/datawhalechina/hello-agents/main/README.md",
            category_hint="AI Agent 工程实践",
            max_questions=4,
            job_tracks=["ai-agent"],
            source_type="github",
        ),
        _source(
            name="Datawhale hello-agents 面试题参考答案",
            base_url="https://raw.githubusercontent.com/datawhalechina/hello-agents/main/Extra-Chapter/Extra01-%E5%8F%82%E8%80%83%E7%AD%94%E6%A1%88.md",
            category_hint="AI Agent 面试题",
            max_questions=5,
            job_tracks=["ai-agent"],
            source_type="github",
        ),
        _source(
            name="AgentGuide README",
            base_url="https://raw.githubusercontent.com/adongwanai/AgentGuide/main/README.md",
            category_hint="AI Agent 工程实践",
            max_questions=5,
            job_tracks=["ai-agent"],
            source_type="github",
        ),
        _source(
            name="AIGC Interview Book README",
            base_url="https://raw.githubusercontent.com/WeThinkIn/AIGC-Interview-Book/main/README.md",
            category_hint="AI Agent 与大模型面试",
            max_questions=5,
            job_tracks=["ai-agent", "ml-engineer"],
            source_type="github",
        ),
    ],
    "backend": [
        _source(
            name="小林 coding - 互联网后端开发面试真题汇总",
            base_url="https://www.xiaolincoding.com/backend_interview/",
            category_hint="后端综合面试",
            max_questions=5,
            job_tracks=["backend"],
        ),
        _source(
            name="小林 coding - MySQL 面试题",
            base_url="https://www.xiaolincoding.com/interview/mysql.html",
            category_hint="MySQL",
            max_questions=5,
            job_tracks=["backend"],
        ),
        _source(
            name="小林 coding - Redis 面试题",
            base_url="https://www.xiaolincoding.com/interview/redis.html",
            category_hint="Redis",
            max_questions=5,
            job_tracks=["backend"],
        ),
        _source(
            name="小林 coding - 操作系统面试题",
            base_url="https://xiaolincoding.com/interview/os.html",
            category_hint="操作系统",
            max_questions=4,
            job_tracks=["backend"],
        ),
        _source(
            name="小林 coding - 分布式面试题",
            base_url="https://xiaolincoding.com/interview/cap.html",
            category_hint="分布式系统",
            max_questions=4,
            job_tracks=["backend"],
        ),
        _source(
            name="小林 coding - 系统设计面试题",
            base_url="https://www.xiaolincoding.com/interview/systemdesign.html",
            category_hint="系统设计",
            max_questions=4,
            job_tracks=["backend"],
        ),
        _source(
            name="二哥的 Java 进阶之路 README",
            base_url="https://raw.githubusercontent.com/itwanger/toBeBetterJavaer/master/README.md",
            category_hint="Java 后端",
            max_questions=4,
            job_tracks=["backend"],
            source_type="github",
        ),
        _source(
            name="JavaSouth README",
            base_url="https://raw.githubusercontent.com/hdgaadd/JavaSouth/master/README.md",
            category_hint="Java 后端",
            max_questions=4,
            job_tracks=["backend"],
            source_type="github",
        ),
        _source(
            name="面试鸭 README",
            base_url="https://raw.githubusercontent.com/liyupi/mianshiya/master/README.md",
            category_hint="后端综合面试",
            max_questions=4,
            job_tracks=["backend"],
            source_type="github",
        ),
        _source(
            name="Go 学习路线图 README",
            base_url="https://raw.githubusercontent.com/yongxinz/gopher/main/README.md",
            category_hint="Go 后端",
            max_questions=4,
            job_tracks=["backend"],
            source_type="github",
        ),
    ],
    "ml-engineer": [
        _source(
            name="DeepLearning Interview Awesome 2024 README",
            base_url="https://raw.githubusercontent.com/315386775/DeepLearing-Interview-Awesome-2024/master/README.md",
            category_hint="机器学习与大模型面试",
            max_questions=5,
            job_tracks=["ml-engineer"],
            source_type="github",
        ),
        _source(
            name="Interview Notes README",
            base_url="https://raw.githubusercontent.com/HirahTang/Interview-Notes/master/README.md",
            category_hint="机器学习与推荐系统",
            max_questions=5,
            job_tracks=["ml-engineer"],
            source_type="github",
        ),
        _source(
            name="AI Job Notes README",
            base_url="https://raw.githubusercontent.com/amusi/AI-Job-Notes/master/README.md",
            category_hint="AI 算法岗求职",
            max_questions=4,
            job_tracks=["ml-engineer"],
            source_type="github",
        ),
        _source(
            name="Machine Learning Interview README",
            base_url="https://raw.githubusercontent.com/zhengjingwei/machine-learning-interview/master/README.md",
            category_hint="机器学习基础",
            max_questions=5,
            job_tracks=["ml-engineer"],
            source_type="github",
        ),
        _source(
            name="LLMs Interview Notes README",
            base_url="https://raw.githubusercontent.com/km1994/LLMs_interview_notes/master/README.md",
            category_hint="大模型与 NLP 面试",
            max_questions=5,
            job_tracks=["ml-engineer"],
            source_type="github",
        ),
        _source(
            name="Paddle Awesome DeepLearning README",
            base_url="https://raw.githubusercontent.com/PaddlePaddle/awesome-DeepLearning/master/README.md",
            category_hint="深度学习基础与面试",
            max_questions=4,
            job_tracks=["ml-engineer"],
            source_type="github",
        ),
        _source(
            name="机器学习与深度学习笔记 README",
            base_url="https://raw.githubusercontent.com/loveunk/machine-learning-deep-learning-notes/master/README.md",
            category_hint="机器学习基础",
            max_questions=4,
            job_tracks=["ml-engineer"],
            source_type="github",
        ),
    ],
}


def iter_source_catalog(job_tracks: Iterable[str] | None = None) -> list[CatalogItem]:
    if not job_tracks:
        selected_tracks = list(SOURCE_CATALOG_BY_TRACK.keys())
    else:
        selected_tracks = []
        seen = set()
        for item in job_tracks:
            normalized = item.strip().lower()
            if normalized and normalized in SOURCE_CATALOG_BY_TRACK and normalized not in seen:
                selected_tracks.append(normalized)
                seen.add(normalized)

    catalog: list[CatalogItem] = []
    seen_urls: set[str] = set()
    for track in selected_tracks:
        for item in SOURCE_CATALOG_BY_TRACK[track]:
            base_url = str(item.get("base_url") or "")
            if base_url and base_url in seen_urls:
                continue
            if base_url:
                seen_urls.add(base_url)
            catalog.append(item)
    return catalog


DEFAULT_SOURCE_CATALOG: list[CatalogItem] = iter_source_catalog()
