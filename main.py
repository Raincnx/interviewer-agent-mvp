import json
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from openai import OpenAI
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app.db"
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(title="Interviewer Agent MVP", version="0.1.0")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4")
MAX_ANSWERS = int(os.getenv("MAX_ANSWERS", "5"))

if not OPENAI_API_KEY:
    print("WARNING: OPENAI_API_KEY is not set yet.")

client = OpenAI(api_key=OPENAI_API_KEY)


class StartInterviewRequest(BaseModel):
    target_role: str = Field(default="后端开发")
    level: str = Field(default="校招")
    round_type: str = Field(default="项目面")


class ReplyRequest(BaseModel):
    interview_id: str
    answer: str


class FinishRequest(BaseModel):
    interview_id: str


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS interviews (
            id TEXT PRIMARY KEY,
            target_role TEXT NOT NULL,
            level TEXT NOT NULL,
            round_type TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            finished_at TEXT,
            final_report TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            interview_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(interview_id) REFERENCES interviews(id)
        )
        """
    )

    conn.commit()
    conn.close()


@app.on_event("startup")
def startup_event() -> None:
    init_db()


def save_message(interview_id: str, role: str, content: str) -> None:
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO messages (id, interview_id, role, content, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            interview_id,
            role,
            content,
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def get_interview(interview_id: str) -> sqlite3.Row | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM interviews WHERE id = ?",
        (interview_id,),
    ).fetchone()
    conn.close()
    return row


def load_messages(interview_id: str) -> list[dict[str, str]]:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT role, content
        FROM messages
        WHERE interview_id = ?
        ORDER BY created_at ASC
        """,
        (interview_id,),
    ).fetchall()
    conn.close()

    messages: list[dict[str, str]] = []
    for row in rows:
        role = row["role"]
        if role not in ("user", "assistant"):
            continue
        messages.append({"role": role, "content": row["content"]})
    return messages


def count_user_answers(interview_id: str) -> int:
    conn = get_conn()
    row = conn.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM messages
        WHERE interview_id = ? AND role = 'user'
        """,
        (interview_id,),
    ).fetchone()
    conn.close()
    return int(row["cnt"])


def update_report(interview_id: str, report: dict[str, Any]) -> None:
    conn = get_conn()
    conn.execute(
        """
        UPDATE interviews
        SET status = ?, finished_at = ?, final_report = ?
        WHERE id = ?
        """,
        (
            "finished",
            datetime.utcnow().isoformat(),
            json.dumps(report, ensure_ascii=False),
            interview_id,
        ),
    )
    conn.commit()
    conn.close()


def interviewer_instructions(meta: sqlite3.Row) -> str:
    return f"""
你是一名中国互联网大厂的技术面试官。
当前面试配置：
- 岗位：{meta["target_role"]}
- 级别：{meta["level"]}
- 轮次：{meta["round_type"]}

你的任务：
1. 每次只输出“面试官下一轮要说的话”。
2. 优先基于候选人刚才的回答做追问，抓不清楚、没展开、可能有水分的点。
3. 如果候选人的回答已经比较完整，再切到下一题。
4. 语气专业、直接，像真实技术面试官。
5. 输出控制在 30~120 字。
6. 不要给分，不要解释你的思路，不要说“作为AI”。

追问偏好：
- 项目真实性核验
- 技术细节
- trade-off
- 边界情况
- 故障处理
- 性能/扩展性
""".strip()


def grading_instructions(meta: sqlite3.Row) -> str:
    return f"""
你是一名严格、专业的技术面试评估官。
你要根据完整面试对话，对候选人进行评分。

当前面试配置：
- 岗位：{meta["target_role"]}
- 级别：{meta["level"]}
- 轮次：{meta["round_type"]}

请只返回合法 JSON，不要使用 markdown 代码块，不要输出任何额外解释。
JSON 结构必须严格为：
{{
  "overall_score": 0,
  "dimension_scores": {{
    "基础知识": 0,
    "项目深度": 0,
    "追问应对": 0,
    "表达结构": 0
  }},
  "strengths": ["", "", ""],
  "weaknesses": ["", "", ""],
  "next_actions": ["", "", ""],
  "hire_recommendation": ""
}}

要求：
- overall_score：0-100 的整数
- dimension_scores：每项 1-5 分整数
- strengths / weaknesses / next_actions：各 3 条，简洁具体
- hire_recommendation：只能填 “建议通过” / “建议保留” / “建议不通过”
""".strip()


def call_interviewer(messages: list[dict[str, str]], meta: sqlite3.Row) -> str:
    response = client.responses.create(
        model=OPENAI_MODEL,
        instructions=interviewer_instructions(meta),
        input=messages,
    )
    text = (response.output_text or "").strip()
    if not text:
        raise RuntimeError("模型没有返回提问内容")
    return text


def generate_opening_question(meta: sqlite3.Row) -> str:
    response = client.responses.create(
        model=OPENAI_MODEL,
        instructions=interviewer_instructions(meta),
        input=[{"role": "user", "content": "请直接开始第一题，不要寒暄。"}],
    )
    text = (response.output_text or "").strip()
    if not text:
        raise RuntimeError("模型没有返回首题")
    return text


def generate_report(messages: list[dict[str, str]], meta: sqlite3.Row) -> dict[str, Any]:
    prompt_messages = messages + [
        {
            "role": "user",
            "content": "请基于以上完整面试对话，输出最终评分 JSON。",
        }
    ]

    response = client.responses.create(
        model=OPENAI_MODEL,
        instructions=grading_instructions(meta),
        input=prompt_messages,
    )

    text = (response.output_text or "").strip()
    if not text:
        raise RuntimeError("模型没有返回评估结果")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 容错：尽量截取 JSON 主体
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise RuntimeError(f"评估 JSON 解析失败，原始输出：{text}")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
def health():
    return {"ok": True, "model": OPENAI_MODEL}


@app.post("/api/start")
def start_interview(payload: StartInterviewRequest):
    interview_id = str(uuid.uuid4())

    conn = get_conn()
    conn.execute(
        """
        INSERT INTO interviews (id, target_role, level, round_type, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            interview_id,
            payload.target_role,
            payload.level,
            payload.round_type,
            "running",
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()

    meta = get_interview(interview_id)
    if meta is None:
        raise HTTPException(status_code=500, detail="创建面试失败")

    opening = generate_opening_question(meta)
    save_message(interview_id, "assistant", opening)

    return {
        "interview_id": interview_id,
        "question": opening,
        "max_answers": MAX_ANSWERS,
    }


@app.post("/api/reply")
def reply(payload: ReplyRequest):
    meta = get_interview(payload.interview_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="面试不存在")

    if meta["status"] == "finished":
        final_report = json.loads(meta["final_report"]) if meta["final_report"] else {}
        return {
            "done": True,
            "report": final_report,
            "message": "该面试已结束",
        }

    answer = payload.answer.strip()
    if not answer:
        raise HTTPException(status_code=400, detail="回答不能为空")

    save_message(payload.interview_id, "user", answer)
    answer_count = count_user_answers(payload.interview_id)
    messages = load_messages(payload.interview_id)

    if answer_count >= MAX_ANSWERS:
        report = generate_report(messages, meta)
        update_report(payload.interview_id, report)
        return {"done": True, "report": report}

    next_question = call_interviewer(messages, meta)
    save_message(payload.interview_id, "assistant", next_question)

    return {
        "done": False,
        "question": next_question,
        "current_answer_count": answer_count,
        "remaining_answers": MAX_ANSWERS - answer_count,
    }


@app.post("/api/finish")
def finish(payload: FinishRequest):
    meta = get_interview(payload.interview_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="面试不存在")

    if meta["status"] == "finished":
        final_report = json.loads(meta["final_report"]) if meta["final_report"] else {}
        return {"done": True, "report": final_report}

    messages = load_messages(payload.interview_id)
    if not messages:
        raise HTTPException(status_code=400, detail="没有可评估的对话")

    report = generate_report(messages, meta)
    update_report(payload.interview_id, report)
    return {"done": True, "report": report}