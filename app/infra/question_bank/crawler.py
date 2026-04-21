from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import Settings


@dataclass
class CrawledDocument:
    source_url: Optional[str]
    source_title: Optional[str]
    markdown: str


class SimpleHttpMarkdownCrawler:
    def fetch(self, url: str) -> CrawledDocument:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        body = response.text
        title = self._extract_title(body)

        if "markdown" in content_type or url.endswith(".md"):
            markdown = body
        else:
            markdown = self._html_to_markdown(body)

        return CrawledDocument(
            source_url=url,
            source_title=title,
            markdown=markdown.strip(),
        )

    @staticmethod
    def _extract_title(body: str) -> Optional[str]:
        match = re.search(r"<title>(.*?)</title>", body, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        return html.unescape(match.group(1)).strip() or None

    @staticmethod
    def _html_to_markdown(body: str) -> str:
        text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", body)
        text = re.sub(r"(?i)</(p|div|li|h1|h2|h3|h4|h5|h6|tr|section|article|br)>", "\n", text)
        text = re.sub(r"(?i)<li[^>]*>", "- ", text)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        text = html.unescape(text)
        text = re.sub(r"\r\n?", "\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


class FirecrawlMarkdownCrawler:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def fetch(self, url: str) -> CrawledDocument:
        try:
            from firecrawl import FirecrawlApp
        except ImportError as exc:
            raise RuntimeError("未安装 Firecrawl SDK，请先安装对应依赖后再启用 `use_firecrawl`。") from exc

        app = FirecrawlApp(api_key=self.api_key)
        result = app.scrape_url(url, params={"formats": ["markdown"]})
        markdown = result.get("markdown") or ""
        metadata = result.get("metadata") or {}
        title = metadata.get("title")
        return CrawledDocument(
            source_url=url,
            source_title=title,
            markdown=markdown.strip(),
        )


def build_question_crawler(settings: Settings, use_firecrawl: bool):
    if use_firecrawl:
        if not settings.firecrawl_api_key:
            raise RuntimeError("`use_firecrawl=true`，但当前未配置 `FIRECRAWL_API_KEY`。")
        return FirecrawlMarkdownCrawler(settings.firecrawl_api_key)
    return SimpleHttpMarkdownCrawler()
