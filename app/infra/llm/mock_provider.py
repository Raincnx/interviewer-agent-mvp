from __future__ import annotations

from typing import Any

from app.infra.llm.base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        lowered = user_prompt.lower()
        if "第一题" in user_prompt:
            return "请你挑一个最有代表性的项目，按背景、目标、你的职责、技术方案和结果完整介绍一下。"
        if "完整对话" in user_prompt or "继续追问" in user_prompt:
            return "你刚才提到用了缓存和异步队列，那你具体说说缓存一致性怎么保证，出现消息积压时你怎么处理？"
        return "请继续展开这个点，说具体一些。"

    def generate_json(self, system_prompt: str, user_prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        return {
            "overall_score": 78,
            "dimension_scores": {
                "基础知识": 4,
                "项目深度": 4,
                "追问应对": 3,
                "表达结构": 3,
            },
            "strengths": [
                "项目叙述比较完整",
                "能说明关键技术选型",
                "对性能问题有基本工程意识",
            ],
            "weaknesses": [
                "细节深挖时回答不够具体",
                "容量估算与边界处理不足",
                "表达结构还可以更紧凑",
            ],
            "next_actions": [
                "准备 2 个项目的高频追问细节",
                "补强缓存一致性与消息队列异常处理",
                "按 STAR 或 背景-方案-结果 模板练习表达",
            ],
            "hire_recommendation": "建议保留",
        }
