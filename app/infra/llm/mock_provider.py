from __future__ import annotations

from typing import Any

from app.infra.llm.base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        if "第一道面试问题" in user_prompt or "现在开始一场新的技术面试" in user_prompt:
            return "请你挑一个自己最熟悉的项目，按背景、目标、你的职责、核心技术方案和最终结果完整介绍一下。"
        if "完整对话记录" in user_prompt or "优先基于候选人刚才的回答继续追问" in user_prompt:
            return "你刚才提到用了缓存和异步任务队列，那你具体是怎么保证数据一致性的？如果消息堆积了，你会怎么排查和处理？"
        return "这个点再往下展开一层，说一下你的取舍和原因。"

    def generate_json(self, system_prompt: str, user_prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        return {
            "overall_score": 78,
            "dimension_scores": {
                "基础知识": 4,
                "项目深度": 4,
                "追问应对": 3,
                "表达沟通": 3,
            },
            "strengths": [
                "项目背景和职责交代得比较清楚。",
                "能够说明关键技术选型背后的原因。",
                "对性能和稳定性问题有基本工程意识。",
            ],
            "weaknesses": [
                "继续深挖时，回答细节还不够具体。",
                "容量评估和边界情况考虑不够完整。",
                "表达可以更有结构、更简洁。",
            ],
            "next_actions": [
                "准备两到三个项目的关键实现细节和可追问点。",
                "加强缓存一致性和消息队列异常处理方面的训练。",
                "回答开放题时使用更清晰的结构来组织表达。",
            ],
            "hire_recommendation": "建议保留",
        }
