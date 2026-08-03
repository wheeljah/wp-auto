"""Structure Optimizer — pillar/cluster 글의 구조를 레거시 미디어 + 인기 블로그 패턴으로 보강.

기능:
- TL;DR 자동 추출 (첫 단락 또는 메타 설명 기반)
- Article Summary ('요약 내용' h2 + 실제 기사 요약 2-3문장) 자동 주입
- FAQ section 자동 추가 (outline.faq 활용 또는 LLM 1회)
- E-E-A-T footer 추가 (author, last updated, 출처 표기 가이드)
- Related articles (cluster chunks internal link)
- "Updated:" 메타 표시 (HTML 상단/하단)

사용법:
    from wp_auto.ai.structure_optimizer import StructureOptimizer

    optimizer = StructureOptimizer(author_name="1인 운영자", language="ko")
    enhanced_html = optimizer.optimize_pillar(pillar_body, cluster.chunks)
    enhanced_chunk = optimizer.optimize_chunk(chunk_body, related_slugs=[...])
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from loguru import logger

PROMPTS_DIR = Path(__file__).parent / "prompts"
SUPPORTED_LANGUAGES = ("ko", "en")

# E-E-A-T footer 다국어 템플릿
EEAT_FOOTER_TEMPLATE: dict[str, str] = {
    "ko": (
        '\n<hr style="margin:32px 0;border:none;border-top:1px solid #e5e7eb;">\n'
        '<div class="wp-auto-eeat" style="font-size:13px;color:#6b7280;line-height:1.6;">\n'
        '<p style="margin:0 0 6px 0;"><strong>📝 작성:</strong> {author} '
        '<span style="margin-left:12px;">🕒 업데이트: {updated}</span></p>\n'
        '<p style="margin:0;"><strong>ℹ️ 본문 안내:</strong> 본 글은 AI로 초안 작성 후 사람이 검수/보완했습니다. '
        '인용된 출처는 발행 시점 기준이며, 최신 정보는 각 출처를 확인해 주세요.</p>\n'
        '</div>\n'
    ),
    "en": (
        '\n<hr style="margin:32px 0;border:none;border-top:1px solid #e5e7eb;">\n'
        '<div class="wp-auto-eeat" style="font-size:13px;color:#6b7280;line-height:1.6;">\n'
        '<p style="margin:0 0 6px 0;"><strong>📝 Written by:</strong> {author} '
        '<span style="margin-left:12px;">🕒 Last updated: {updated}</span></p>\n'
        '<p style="margin:0;"><strong>ℹ️ Note:</strong> This article was drafted with AI assistance and reviewed by a human editor. '
        'Cited sources are accurate as of publication; please verify the latest information at each source.</p>\n'
        '</div>\n'
    ),
}

# TL;DR 라벨 다국어
TLDR_LABEL: dict[str, str] = {
    "ko": "⚡ 한 줄 요약 (TL;DR)",
    "en": "⚡ TL;DR",
}

# FAQ 라벨 다국어
FAQ_LABEL: dict[str, str] = {
    "ko": "❓ 자주 묻는 질문 (FAQ)",
    "en": "❓ Frequently Asked Questions",
}

# Related articles 라벨 다국어
RELATED_LABEL: dict[str, str] = {
    "ko": "📚 관련 글",
    "en": "📚 Related Articles",
}


class StructureOptimizer:
    """pillar / chunk HTML에 구조 요소 자동 주입."""

    def __init__(
        self,
        author_name: str = "1인 운영자 (AI-assisted)",
        language: str = "ko",
    ) -> None:
        self.author_name = author_name
        self.language = language
        logger.info("StructureOptimizer initialized: language={}", language)

    def _eet_footer(self) -> str:
        return EEAT_FOOTER_TEMPLATE[self.language].format(
            author=self.author_name,
            updated=datetime.now().strftime("%Y-%m-%d"),
        )

    def wrap_tldr(self, body_html: str, tldr: str) -> str:
        """body 맨 위에 TL;DR 박스 삽입."""
        if not tldr.strip():
            return body_html
        box = (
            '<div class="wp-auto-tldr" style="'
            'margin:0 0 24px 0;padding:14px 18px;'
            'border-left:4px solid #3b82f6;background:#eff6ff;'
            'border-radius:4px;font-size:15px;line-height:1.6;">'
            f'<div style="font-weight:600;color:#1e40af;margin-bottom:6px;">{TLDR_LABEL[self.language]}</div>'
            f'<div>{tldr}</div>'
            '</div>'
        )
        return box + body_html

    def wrap_faq(
        self,
        body_html: str,
        faqs: list[dict],
    ) -> str:
        """body 끝에 FAQ section 삽입.

        Args:
            body_html: 원본 HTML
            faqs: [{"q": "질문", "a": "답변"}, ...]
        """
        if not faqs:
            return body_html
        items = "\n".join(
            f'<details style="margin:0 0 12px 0;padding:10px 14px;'
            f'background:#f9fafb;border-radius:4px;">'
            f'<summary style="font-weight:600;cursor:pointer;color:#111827;">{f.get("q", "")}</summary>'
            f'<p style="margin:8px 0 0 0;color:#374151;line-height:1.6;">{f.get("a", "")}</p>'
            f'</details>'
            for f in faqs
        )
        section = (
            f'\n<h2 id="faq">{FAQ_LABEL[self.language]}</h2>\n'
            f'<div class="wp-auto-faq">{items}</div>\n'
        )
        return body_html + section

    def wrap_related(
        self,
        body_html: str,
        related_items: list[dict],
    ) -> str:
        """body 끝에 related articles 섹션 삽입.

        Args:
            body_html: 원본 HTML
            related_items: [{"title": "...", "url": "/slug", "description": "..."}, ...]
        """
        if not related_items:
            return body_html
        items_html = "\n".join(
            f'<li style="margin:0 0 10px 0;">'
            f'<a href="{it.get("url", "#")}" style="font-weight:600;color:#2563eb;text-decoration:none;">'
            f'{it.get("title", "")}</a>'
            + (f'<div style="font-size:13px;color:#6b7280;margin-top:2px;">{it.get("description", "")}</div>' if it.get("description") else "")
            + '</li>'
            for it in related_items
        )
        section = (
            f'\n<aside class="wp-auto-related" style="margin:24px 0 0 0;'
            f'padding:16px 18px;background:#f9fafb;border-radius:6px;">'
            f'<h3 style="margin:0 0 10px 0;font-size:16px;">{RELATED_LABEL[self.language]}</h3>'
            f'<ul style="margin:0;padding-left:20px;list-style:disc;">{items_html}</ul>'
            f'</aside>\n'
        )
        return body_html + section

    def append_eeat(self, body_html: str) -> str:
        """body 끝에 E-E-A-T footer 추가."""
        return body_html + self._eet_footer()

    def optimize_pillar(
        self,
        body_html: str,
        *,
        tldr: str = "",
        article_summary: str = "",
        chunk_summaries: list[str] | None = None,
        faqs: list[dict] | None = None,
        related_items: list[dict] | None = None,
    ) -> str:
        """pillar body에 TL;DR + Article Summary + FAQ + Related + E-E-A-T footer 통합 주입.

        Args:
            body_html: 원본 pillar HTML
            tldr: 한 줄 요약 (top of article)
            article_summary: 기사의 핵심 요약 2-3문장 (LLM이 작성). 없으면 chunk_summaries로 자동 생성
            chunk_summaries: chunk별 1-2문장 요약 리스트 (article_summary 생성용)
            faqs: FAQ 리스트
            related_items: 관련 글 리스트 (cluster chunks 등)
        """
        out = body_html
        if tldr:
            out = self.wrap_tldr(out, tldr)
        # article summary 주입: "요약 내용" h2 아래 (있는 경우) 또는 body 시작에 추가
        if article_summary or chunk_summaries:
            out = self._inject_article_summary(out, article_summary, chunk_summaries or [])
        if faqs:
            out = self.wrap_faq(out, faqs)
        if related_items:
            out = self.wrap_related(out, related_items)
        out = self.append_eeat(out)
        return out

    def _inject_article_summary(
        self,
        body_html: str,
        article_summary: str,
        chunk_summaries: list[str],
    ) -> str:
        """pillar body에 '요약 내용' h2 + 실제 기사 요약 주입.

        기존 "요약 내용" h2가 있으면 그 아래에 summary 삽입, 없으면 nut graf 다음에 추가.
        """
        # 1) chunk_summaries에서 자동 summary 생성 (article_summary가 비어있을 때)
        if not article_summary and chunk_summaries:
            # 첫 2개 chunk의 meta_description을 결합 (이미 1-2문장이므로 그대로 사용)
            summary_parts = [s.strip() for s in chunk_summaries[:2] if s and s.strip()]
            article_summary = " ".join(summary_parts)
        if not article_summary:
            return body_html
        # 2) body에 "요약 내용" h2가 이미 있으면 그 아래에 p 삽입
        if '<h2 id="요약 내용">' in body_html or '<h2>요약 내용</h2>' in body_html:
            # h2 다음 줄에 p 삽입
            summary_html = (
                f'<p style="margin:12px 0 24px 0;line-height:1.7;'
                f'font-size:15px;color:#1f2937;">{article_summary}</p>'
            )
            body_html = re.sub(
                r'(<h2[^>]*>요약 내용</h2>)',
                r'\1' + "\n" + summary_html,
                body_html, count=1,
            )
            return body_html
        # 3) "요약 내용" h2가 없으면 nut graf 다음에 추가 (fallback)
        # nut graf p 다음에 h2+p 삽입
        summary_block = (
            '<h2>요약 내용</h2>\n'
            f'<p style="margin:12px 0 24px 0;line-height:1.7;'
            f'font-size:15px;color:#1f2937;">{article_summary}</p>\n'
        )
        # nut graf를 포함한 첫 <p>...</p>\n 다음
        m = re.search(r'(<p[^>]*><strong>Nut graf</strong>.*?</p>\n)', body_html, re.DOTALL)
        if m:
            return body_html[:m.end()] + summary_block + body_html[m.end():]
        # nut graf 없으면 h2 첫 등장 직전
        m = re.search(r'(<h2)', body_html)
        if m:
            return body_html[:m.start()] + summary_block + "\n" + body_html[m.start():]
        # body 시작
        return summary_block + body_html

    def optimize_chunk(
        self,
        body_html: str,
        *,
        related_items: list[dict] | None = None,
    ) -> str:
        """chunk body에 Related + E-E-A-T footer 주입 (TL;DR/FAQ는 pillar에만)."""
        out = body_html
        if related_items:
            out = self.wrap_related(out, related_items)
        out = self.append_eeat(out)
        return out


__all__ = ["StructureOptimizer"]
