from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.db.models.interview import Interview
from app.db.models.turn import Turn
from app.domain.schemas.report import ReportRead


@dataclass(frozen=True)
class InterviewStageRuntime:
    stage_key: str
    stage_label: str
    target_turns: int
    estimated_minutes: int
    focus: str


@dataclass
class InterviewAgentState:
    interview: Interview
    turns: list[Turn]
    report: Optional[ReportRead] = None

    STAGE_SPECS = (
        ("intro", "自我介绍", 5, "先用 3-5 分钟了解候选人的背景亮点、求职方向和代表性经历。"),
        ("project", "项目 / 实习深挖", 25, "围绕项目与实习经历深挖方案设计、技术取舍、结果指标与复盘。"),
        ("fundamentals", "八股基础", 15, "补充考察岗位相关的基础原理、系统设计与工程常识。"),
        ("coding", "LeetCode 手撕", 15, "最后 15-20 分钟进入编码题，观察思路、复杂度分析和代码表达。"),
    )

    @property
    def latest_turn(self) -> Optional[Turn]:
        if not self.turns:
            return None
        return self.turns[-1]

    @property
    def answered_turns(self) -> int:
        return sum(1 for turn in self.turns if turn.candidate_answer)

    @property
    def remaining_turns(self) -> int:
        return max(self.interview.max_turns - self.answered_turns, 0)

    @property
    def is_finished(self) -> bool:
        return self.interview.status == "finished"

    @property
    def planned_duration_minutes(self) -> int:
        return 60

    @property
    def stage_plan(self) -> list[InterviewStageRuntime]:
        total_turns = max(int(self.interview.max_turns or 0), 4)

        intro_turns = 1
        coding_turns = max(1, round(total_turns * 0.25))
        fundamentals_turns = max(1, round(total_turns * 0.25))
        project_turns = total_turns - intro_turns - coding_turns - fundamentals_turns

        while project_turns < 2 and fundamentals_turns > 1:
            fundamentals_turns -= 1
            project_turns += 1

        while project_turns < 2 and coding_turns > 1:
            coding_turns -= 1
            project_turns += 1

        if project_turns < 1:
            project_turns = 1

        turn_plan = [intro_turns, project_turns, fundamentals_turns, coding_turns]
        minute_plan = [5, 25, 15, 15]

        result: list[InterviewStageRuntime] = []
        for (stage_key, stage_label, _, focus), target_turns, minutes in zip(self.STAGE_SPECS, turn_plan, minute_plan):
            result.append(
                InterviewStageRuntime(
                    stage_key=stage_key,
                    stage_label=stage_label,
                    target_turns=target_turns,
                    estimated_minutes=minutes,
                    focus=focus,
                )
            )
        return result

    @property
    def current_stage(self) -> InterviewStageRuntime:
        answered = self.answered_turns
        cursor = 0
        for stage in self.stage_plan:
            if answered < cursor + stage.target_turns:
                return stage
            cursor += stage.target_turns
        return self.stage_plan[-1]

    @property
    def estimated_elapsed_minutes(self) -> int:
        answered = self.answered_turns
        elapsed = 0.0
        remaining_answered = answered

        for stage in self.stage_plan:
            if remaining_answered <= 0:
                break
            stage_answered = min(remaining_answered, stage.target_turns)
            elapsed += stage.estimated_minutes * (stage_answered / max(stage.target_turns, 1))
            remaining_answered -= stage_answered

        return int(round(elapsed))

    @property
    def estimated_remaining_minutes(self) -> int:
        return max(self.planned_duration_minutes - self.estimated_elapsed_minutes, 0)

    def build_transcript(self) -> str:
        lines: list[str] = []
        for turn in self.turns:
            lines.append(f"面试官：{turn.question_text}")
            if turn.candidate_answer:
                lines.append(f"候选人：{turn.candidate_answer}")
        return "\n".join(lines)
