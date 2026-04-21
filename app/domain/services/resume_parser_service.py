from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re

from fastapi import UploadFile

from app.domain.schemas.resume import ResumeParseResponse


class ResumeParserService:
    SUPPORTED_SUFFIXES = {".pdf", ".docx", ".txt", ".md"}
    MAX_FILE_BYTES = 5 * 1024 * 1024

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

        normalized = self._normalize_text(text)
        if len(normalized) < 20:
            raise ValueError("解析后的简历内容过短，请确认上传了完整简历。")

        return ResumeParseResponse(
            filename=filename,
            content_type=upload.content_type,
            text=normalized,
            preview=normalized[:600],
            char_count=len(normalized),
        )

    @staticmethod
    def _decode_text(raw: bytes) -> str:
        for encoding in ("utf-8", "utf-8-sig", "gb18030"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="ignore")

    @staticmethod
    def _parse_pdf(raw: bytes) -> str:
        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("当前环境未安装 pypdf，无法解析 PDF 简历。") from exc

        reader = PdfReader(BytesIO(raw))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages)

    @staticmethod
    def _parse_docx(raw: bytes) -> str:
        try:
            from docx import Document
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("当前环境未安装 python-docx，无法解析 DOCX 简历。") from exc

        document = Document(BytesIO(raw))
        paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
        return "\n\n".join(paragraphs)

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\t+", " ", text)
        text = re.sub(r"[ \u3000]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
