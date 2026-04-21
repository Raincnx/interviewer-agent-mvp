from __future__ import annotations

import re
from typing import Any

from app.infra.llm.base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        if "现在开始一场新的技术面试" in user_prompt:
            resume_summary = self._extract_resume_hint(user_prompt)
            if resume_summary:
                return f"我看到你在简历里提到了{resume_summary}。请你挑一个最能体现你技术判断的项目，按背景、职责、方案取舍和结果完整展开。"
            if "参考题 1" in user_prompt:
                return "我们先从题库里的核心主题开始。请你解释一下 Agent、Workflow 和 Tools 三者的区别，并结合一个真实项目说明它们是如何协同工作的。"
            return "先请你挑一个最能代表你技术深度的项目，按背景、职责、技术方案和结果完整介绍一下。"

        if "完整对话" in user_prompt:
            resume_summary = self._extract_resume_hint(user_prompt)
            if resume_summary:
                return f"你刚才提到了{resume_summary}。如果把它真正落到线上系统里，你会怎么做可观测性、容错和回滚设计？"
            if "参考题 1" in user_prompt:
                return "你提到了这个方案，那如果要继续往下深挖，Memory、Function Calling 和可观测性这三块你会怎么一起设计？"
            return "如果把你刚才说的方案真正落地到线上，你会怎么处理稳定性、观测性和回滚？"

        return "继续说说你会怎么做取舍。"

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
                "表达结构可以再更清晰一些。",
            ],
            "next_actions": [
                "把一个代表性项目按背景、目标、方案、取舍、结果重新整理成完整故事。",
                "补强可观测性、稳定性和成本控制相关案例。",
                "回答开放题时优先给出结构化框架，再展开细节。",
            ],
            "hire_recommendation": "建议保留",
        }

    @staticmethod
    def _extract_resume_hint(user_prompt: str) -> str | None:
        if "暂无可用简历参考。" in user_prompt:
            return None
        matches = re.findall(r"\[简历片段 \d+\][^\n]*\n(.+)", user_prompt)
        if not matches:
            return "你的项目经历"
        snippet = matches[0].strip().replace("\n", " ")
        snippet = re.sub(r"\s+", " ", snippet)
        return snippet[:24]
