from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.db.models.interview import Interview
from app.db.models.turn import Turn
from app.domain.schemas.report import ReportRead


@dataclass
class InterviewAgentState:
    interview: Interview
    turns: list[Turn]
    report: Optional[ReportRead] = None

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

    def build_transcript(self) -> str:
        lines: list[str] = []
        for turn in self.turns:
            lines.append(f"面试官：{turn.question_text}")
            if turn.candidate_answer:
                lines.append(f"候选人：{turn.candidate_answer}")
        return "\n".join(lines)
