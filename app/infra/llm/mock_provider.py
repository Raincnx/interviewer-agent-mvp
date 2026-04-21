from __future__ import annotations

import re
from typing import Any

from app.infra.llm.base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        stage = self._extract_stage(user_prompt)
        resume_summary = self._extract_resume_hint(user_prompt)

        if stage == "项目 / 实习深挖":
            if resume_summary:
                return (
                    f"你刚才提到了{resume_summary}。如果把它真正放到线上环境里，"
                    "你做过哪些核心方案取舍？当时为什么这么选，最后数据结果怎么样？"
                )
            return "你刚才讲了这个项目的背景，那你具体负责的核心模块是什么？最难的技术取舍是什么？"

        if stage == "八股基础":
            return "我们切到基础题。你先说说 Function Calling、MCP 和普通 prompt chaining 的区别，以及各自适用场景。"

        if stage == "LeetCode 手撕":
            return "我们进入手撕题。请你先讲一下如何用哈希表和滑动窗口求解最长无重复子串，再说时间复杂度。"

        return "继续往下讲讲你会怎么做技术取舍，以及你会关注哪些线上指标。"

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
                "能够结合真实项目讲清楚背景和目标。",
                "对核心技术方案有基本判断，并能解释取舍。",
                "回答中体现出一定的问题拆解能力。",
            ],
            "weaknesses": [
                "对关键细节的展开还不够深入。",
                "工具链与工程化细节描述偏少。",
                "表达结构还可以更清晰一些。",
            ],
            "next_actions": [
                "把一个代表性项目按背景、目标、方案、取舍、结果重新整理成完整故事。",
                "补强可观测性、稳定性和成本控制相关案例。",
                "回答开放题时优先给出结构化框架，再展开细节。",
            ],
            "hire_recommendation": "建议保留",
        }

    @staticmethod
    def _extract_stage(user_prompt: str) -> str | None:
        match = re.search(r"当前阶段：([^\n]+)", user_prompt)
        if match:
            return match.group(1).strip()
        return None

    @staticmethod
    def _extract_resume_hint(user_prompt: str) -> str | None:
        if "暂无可用简历参考。" in user_prompt:
            return None

        matches = re.findall(r"\[简历片段\s*\d+\][^\n]*\n(.+)", user_prompt)
        if not matches:
            return "你的项目经历"

        snippet = matches[0].strip().replace("\n", " ")
        snippet = re.sub(r"\s+", " ", snippet)
        return snippet[:24]
