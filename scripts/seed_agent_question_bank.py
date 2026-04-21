from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import Settings
from app.db.base import Base
from app.domain.schemas.question_bank import QuestionCollectRequest
from app.domain.services.question_bank_service import QuestionBankService
from app.infra.repositories.question_bank_repo import QuestionBankRepository


@dataclass(frozen=True)
class SeedSource:
    source_url: str
    category_hint: str
    max_questions: int = 1


SEED_SOURCES: list[SeedSource] = [
    SeedSource("https://xiaolinnote.com/ai/agent/1_whatisagent.html", "AI Agent 概念与架构"),
    SeedSource("https://xiaolinnote.com/ai/agent/2_components.html", "AI Agent 概念与架构"),
    SeedSource("https://xiaolinnote.com/ai/agent/3_workflow_tools.html", "AI Agent 概念与架构"),
    SeedSource("https://xiaolinnote.com/ai/agent/4_patterns.html", "AI Agent 设计范式"),
    SeedSource("https://xiaolinnote.com/ai/agent/5_react.html", "AI Agent 设计范式"),
    SeedSource("https://xiaolinnote.com/ai/agent/6_three_patterns.html", "AI Agent 设计范式"),
    SeedSource("https://xiaolinnote.com/ai/agent/7_tasksplit.html", "AI Agent 工程实践"),
    SeedSource("https://xiaolinnote.com/ai/agent/8_memory.html", "AI Agent 记忆机制"),
    SeedSource("https://xiaolinnote.com/ai/agent/9_memory_storage.html", "AI Agent 记忆机制"),
    SeedSource("https://xiaolinnote.com/ai/agent/10_multiagent.html", "AI Agent 多智能体"),
    SeedSource("https://xiaolinnote.com/ai/agent/11_single_multi.html", "AI Agent 多智能体"),
    SeedSource("https://xiaolinnote.com/ai/agent/12_memcompress.html", "AI Agent 记忆机制"),
    SeedSource("https://xiaolinnote.com/ai/agent/13_handcode.html", "AI Agent 工程实践"),
    SeedSource("https://xiaolinnote.com/ai/agent/14_planning.html", "AI Agent 规划能力"),
    SeedSource("https://xiaolinnote.com/ai/agent/15_reflection.html", "AI Agent 反思机制"),
    SeedSource("https://xiaolinnote.com/ai/agent/16_collab.html", "AI Agent 多智能体"),
    SeedSource("https://xiaolinnote.com/ai/tools/1_function_calling.html", "LLM 工具调用"),
    SeedSource("https://xiaolinnote.com/ai/tools/3_fc_training.html", "LLM 工具调用"),
    SeedSource("https://xiaolinnote.com/ai/tools/13_skill.html", "Agent Skills 与任务路由"),
    SeedSource("https://xiaolinnote.com/ai/tools/15_fc_skill_mcp.html", "MCP 与 Agent 工具生态"),
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
    parser = argparse.ArgumentParser(description="抓取中文 AI Agent 开发题库种子数据。")
    parser.add_argument("--provider", default=None, help="覆盖 LLM provider，例如 gemini / openai / mock")
    parser.add_argument("--model", default=None, help="覆盖模型名，例如 gemini-3-flash-preview")
    parser.add_argument("--prompt-version", default=None, help="覆盖 prompt 版本")
    args = parser.parse_args()

    settings = Settings()
    if args.provider:
        settings.llm_provider = args.provider
    if args.model:
        settings.llm_model = args.model
    if args.prompt_version:
        settings.prompt_version = args.prompt_version

    db = build_session(settings)
    service = QuestionBankService(
        db=db,
        settings=settings,
        repo=QuestionBankRepository(db),
    )

    inserted_total = 0
    skipped_total = 0

    try:
        for source in SEED_SOURCES:
            result = service.collect(
                QuestionCollectRequest(
                    source_url=source.source_url,
                    category_hint=source.category_hint,
                    max_questions=source.max_questions,
                )
            )
            inserted_total += result.inserted_count
            skipped_total += result.skipped_count
            print(f"[DONE] {source.source_url}")
            print(
                f"       extracted={result.extracted_count} inserted={result.inserted_count} skipped={result.skipped_count}"
            )

        print("")
        print("中文 Agent 题库采集完成。")
        print(f"累计新增题目: {inserted_total}")
        print(f"累计跳过重复: {skipped_total}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
