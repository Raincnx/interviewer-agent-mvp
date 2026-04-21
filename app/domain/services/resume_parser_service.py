from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re

from fastapi import UploadFile

from app.domain.schemas.resume import (
    ResumeEducation,
    ResumeExperience,
    ResumeParseResponse,
    ResumeProfile,
    ResumeProject,
)


class ResumeParserService:
    SUPPORTED_SUFFIXES = {".pdf", ".docx", ".txt", ".md"}
    MAX_FILE_BYTES = 5 * 1024 * 1024
    TECH_KEYWORDS = [
        "python",
        "java",
        "golang",
        "go",
        "fastapi",
        "django",
        "flask",
        "react",
        "vue",
        "rag",
        "agent",
        "langgraph",
        "pydanticai",
        "mcp",
        "redis",
        "mysql",
        "postgresql",
        "kafka",
        "docker",
        "kubernetes",
        "llm",
        "transformer",
        "pytorch",
        "tensorflow",
    ]

    async def parse_upload(self, upload: UploadFile) -> ResumeParseResponse:
        filename = upload.filename or "resume.txt"
        suffix = Path(filename).suffix.lower()
        if suffix not in self.SUPPORTED_SUFFIXES:
            raise ValueError("暂时仅支持 PDF、DOCX、TXT 和 Markdown 简历。")

        raw = await upload.read()
        if not raw:
            raise ValueError("上传的简历文件为空。")
        if len(raw) > self.MAX_FILE_BYTES:
            raise ValueError("简历文件过大，请控制在 5MB 以内。")

        if suffix in {".txt", ".md"}:
            text = self._decode_text(raw)
        elif suffix == ".pdf":
            text = self._parse_pdf(raw)
        else:
            text = self._parse_docx(raw)

        normalized = self._normalize_text(self._repair_text(text))
        if len(normalized) < 20:
            raise ValueError("解析后的简历内容过短，请确认上传了完整简历。")

        profile = self.extract_profile(normalized)

        return ResumeParseResponse(
            filename=filename,
            content_type=upload.content_type,
            text=normalized,
            preview=normalized[:600],
            char_count=len(normalized),
            profile=profile,
        )

    @classmethod
    def extract_profile(cls, text: str) -> ResumeProfile:
        normalized = cls._normalize_text(cls._repair_text(text))
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", normalized) if part.strip()]
        sections = cls._group_sections(paragraphs)

        headline = paragraphs[0].splitlines()[0].strip() if paragraphs else None
        skills = cls._extract_skills(sections.get("skills", []), normalized)
        projects = cls._extract_projects(sections.get("projects", []))
        experiences = cls._extract_experiences(sections.get("experience", []))
        educations = cls._extract_educations(sections.get("education", []))

        return ResumeProfile(
            headline=headline,
            skills=skills,
            projects=projects,
            experiences=experiences,
            educations=educations,
        )

    @classmethod
    def _group_sections(cls, paragraphs: list[str]) -> dict[str, list[str]]:
        sections: dict[str, list[str]] = {
            "projects": [],
            "experience": [],
            "education": [],
            "skills": [],
            "other": [],
        }
        current = "other"

        for paragraph in paragraphs:
            first_line = paragraph.splitlines()[0].strip()
            marker = cls._classify_heading(first_line)
            if marker:
                current = marker
            sections[current].append(paragraph)
        return sections

    @staticmethod
    def _classify_heading(line: str) -> str | None:
        lowered = line.lower()
        if any(keyword in lowered for keyword in ["项目经历", "项目经验", "科研项目", "projects", "project experience"]):
            return "projects"
        if any(keyword in lowered for keyword in ["工作经历", "实习经历", "experience", "professional experience"]):
            return "experience"
        if any(keyword in lowered for keyword in ["教育背景", "教育经历", "education"]):
            return "education"
        if any(keyword in lowered for keyword in ["技能", "专业技能", "skill", "skills", "技术栈"]):
            return "skills"
        return None

    @classmethod
    def _extract_projects(cls, paragraphs: list[str]) -> list[ResumeProject]:
        items: list[ResumeProject] = []
        for paragraph in paragraphs:
            lines = [line.strip("•·- ").strip() for line in paragraph.splitlines() if line.strip()]
            if not lines:
                continue
            title = lines[0][:50]
            if cls._classify_heading(title) == "projects" and len(lines) > 1:
                title = lines[1][:50]

            summary = " ".join(lines[1:] if len(lines) > 1 else lines)
            summary = summary[:260] if summary else lines[0][:260]
            technologies = cls._extract_tech_keywords(summary or paragraph)
            outcomes = cls._extract_outcomes(lines)

            if summary:
                items.append(
                    ResumeProject(
                        title=title,
                        summary=summary,
                        technologies=technologies,
                        outcomes=outcomes,
                    )
                )
        return cls._dedupe_projects(items)[:6]

    @classmethod
    def _extract_experiences(cls, paragraphs: list[str]) -> list[ResumeExperience]:
        items: list[ResumeExperience] = []
        for paragraph in paragraphs:
            lines = [line.strip("•·- ").strip() for line in paragraph.splitlines() if line.strip()]
            if not lines:
                continue
            company = lines[0][:80]
            role = lines[1][:80] if len(lines) > 2 else None
            summary = " ".join(lines[1:] if len(lines) > 1 else lines)[:260]
            items.append(ResumeExperience(company=company, role=role, summary=summary))
        return items[:4]

    @classmethod
    def _extract_educations(cls, paragraphs: list[str]) -> list[ResumeEducation]:
        items: list[ResumeEducation] = []
        for paragraph in paragraphs:
            lines = [line.strip("•·- ").strip() for line in paragraph.splitlines() if line.strip()]
            if not lines:
                continue
            school = lines[0][:120]
            degree = lines[1][:120] if len(lines) > 1 else None
            summary = " ".join(lines[1:] if len(lines) > 1 else lines)[:260]
            items.append(ResumeEducation(school=school, degree=degree, summary=summary))
        return items[:3]

    @classmethod
    def _extract_skills(cls, paragraphs: list[str], full_text: str) -> list[str]:
        collected: list[str] = []
        for paragraph in paragraphs:
            normalized = paragraph.replace("，", ",").replace("、", ",").replace("/", ",").replace("｜", ",")
            parts = [part.strip("•·- ").strip() for part in re.split(r"[,:\n]", normalized) if part.strip()]
            collected.extend(parts)

        if not collected:
            collected.extend(cls._extract_tech_keywords(full_text))

        cleaned: list[str] = []
        for item in collected:
            if len(item) > 30:
                continue
            if cls._classify_heading(item):
                continue
            cleaned.append(item)

        deduped = list(dict.fromkeys(cleaned))
        return deduped[:16]

    @staticmethod
    def _extract_outcomes(lines: list[str]) -> list[str]:
        outcomes: list[str] = []
        for line in lines:
            if re.search(r"\d+%|\d+\.\d+%|提升|优化|降低|减少|增长|节省|top|前\d+%", line.lower()):
                outcomes.append(line[:120])
        return outcomes[:3]

    @classmethod
    def _extract_tech_keywords(cls, text: str) -> list[str]:
        lowered = text.lower()
        matched = [keyword for keyword in cls.TECH_KEYWORDS if keyword in lowered]
        return list(dict.fromkeys(item.upper() if item in {"llm", "rag", "mcp"} else item for item in matched))

    @staticmethod
    def _dedupe_projects(items: list[ResumeProject]) -> list[ResumeProject]:
        deduped: list[ResumeProject] = []
        seen: set[str] = set()
        for item in items:
            key = f"{item.title.lower()}|{item.summary.lower()[:80]}"
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    @classmethod
    def _decode_text(cls, raw: bytes) -> str:
        candidates: list[str] = []
        for encoding in ("utf-8", "utf-8-sig", "gb18030", "gbk"):
            try:
                candidates.append(raw.decode(encoding))
            except UnicodeDecodeError:
                continue
        if not candidates:
            candidates.append(raw.decode("utf-8", errors="ignore"))
        return max(candidates, key=cls._score_text_quality)

    @classmethod
    def _parse_pdf(cls, raw: bytes) -> str:
        candidates: list[str] = []

        try:
            import pymupdf

            document = pymupdf.open(stream=raw, filetype="pdf")
            candidates.append("\n\n".join((page.get_text("text") or "").strip() for page in document).strip())
        except Exception:
            pass

        try:
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(raw))
            candidates.append("\n\n".join((page.extract_text() or "") for page in reader.pages).strip())
        except ImportError as exc:  # pragma: no cover
            if not candidates:
                raise RuntimeError("当前环境未安装 PDF 解析依赖，无法解析 PDF 简历。") from exc

        candidates = [item for item in candidates if item.strip()]
        if not candidates:
            raise ValueError("未能从 PDF 中提取到可用文本，请尝试导出为 TXT 或 DOCX 后再上传。")

        return max((cls._repair_text(item) for item in candidates), key=cls._score_text_quality)

    @classmethod
    def _parse_docx(cls, raw: bytes) -> str:
        try:
            from docx import Document
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("当前环境未安装 python-docx，无法解析 DOCX 简历。") from exc

        document = Document(BytesIO(raw))
        paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
        return cls._repair_text("\n\n".join(paragraphs))

    @classmethod
    def _repair_text(cls, text: str) -> str:
        current = text or ""
        best = current
        best_score = cls._score_text_quality(best)

        for _ in range(3):
            improved = False
            for candidate in cls._repair_candidates(current):
                score = cls._score_text_quality(candidate)
                if score > best_score:
                    best = candidate
                    best_score = score
                    current = candidate
                    improved = True
            if not improved:
                break

        return best

    @staticmethod
    def _repair_candidates(text: str) -> list[str]:
        candidates = [text]
        transforms = [
            ("gbk", "utf-8"),
            ("gb18030", "utf-8"),
            ("latin1", "utf-8"),
            ("cp1252", "utf-8"),
        ]
        for source_encoding, target_encoding in transforms:
            try:
                repaired = text.encode(source_encoding, errors="ignore").decode(target_encoding, errors="ignore")
            except (LookupError, UnicodeEncodeError, UnicodeDecodeError):
                continue
            if repaired:
                candidates.append(repaired)
        return candidates

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\t+", " ", text)
        text = re.sub(r"[ \u3000]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _score_text_quality(text: str) -> float:
        if not text:
            return 0.0

        length = len(text)
        cjk_count = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
        ascii_count = sum(1 for char in text if char.isascii() and (char.isalnum() or char in " .,:;+-_/()[]"))
        weird_count = sum(1 for char in text if char in "��€鈥™œŸ锟�")
        suspicious_markers = ["æ", "ç", "鍙", "椤", "闈", "浠", "缁", "瑙", "銆", "寮", "璐", "锛", "锟"]
        mojibake_markers = sum(text.count(marker) for marker in suspicious_markers)
        resume_keywords = [
            "项目",
            "经历",
            "负责",
            "技能",
            "教育",
            "开发",
            "平台",
            "系统",
            "实习",
            "工作",
            "公司",
            "技术",
            "工程师",
            "算法",
            "成果",
        ]
        keyword_bonus = sum(5 for keyword in resume_keywords if keyword in text)
        punctuation_bonus = text.count("。") * 1.5 + text.count("：") * 1.2 + text.count("、") * 0.8

        ratio = (cjk_count * 3 + ascii_count * 0.3) / max(length, 1)
        penalty = weird_count * 2 + mojibake_markers * 3
        return ratio * 100 - penalty + keyword_bonus + punctuation_bonus
