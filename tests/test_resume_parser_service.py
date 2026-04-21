from app.domain.services.resume_parser_service import ResumeParserService


def test_repair_text_recovers_utf8_gbk_mojibake() -> None:
    original = "项目经历\n负责 AI Agent 平台开发与线上观测。"
    garbled = original.encode("utf-8").decode("gbk", errors="ignore")
    repaired = ResumeParserService._repair_text(garbled)

    assert "项目经历" in repaired
    assert "AI Agent 平台" in repaired
    assert "线上观测" in repaired


def test_decode_text_prefers_chinese_quality() -> None:
    raw = "项目经历\n负责多智能体编排平台开发。".encode("utf-8")
    decoded = ResumeParserService._decode_text(raw)

    assert "项目经历" in decoded
    assert "多智能体编排平台开发" in decoded


def test_extract_profile_builds_projects_and_skills() -> None:
    text = """
项目经历
AI Agent 开发平台
负责多智能体编排、工具调用和 RAG 检索，落地线上监控，推理成功率提升 12%。

专业技能
Python、FastAPI、RAG、MCP

教育背景
某某大学 计算机科学与技术
""".strip()

    profile = ResumeParserService.extract_profile(text)

    assert profile.projects
    assert profile.projects[0].title == "AI Agent 开发平台"
    assert "python" in ",".join(item.lower() for item in profile.skills)
    assert profile.educations
