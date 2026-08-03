"""Chunked / Pillar-Cluster content generation.

긴 글을 짧은 chunk 단위로 분할 생성하여:
- qwen 3B + GTX 1050 같은 CPU/저VRAM 환경에서 빠른 응답 (200-400자/chunk)
- Google의 pillar-cluster SEO 권장 구조 (pillar 1 + cluster N)
- 부분 수정·다국어 혼합·재시도 비용 ↓

두 가지 게시 모드:
- single: N개 chunk를 1개 HTML로 stitch → 1 WP post
- cluster: pillar 1 + chunk N개 = N+1개 WP post (권장)

사용법:
    from wp_auto.ai.ollama_client import OllamaClient
    from wp_auto.ai.content_generator import ContentGenerator
    from wp_auto.ai.chunked_generator import ChunkedContentGenerator

    outline_gen = ContentGenerator(client)
    outline = outline_gen.generate_outline(topic=..., keyword=..., language="ko")

    chunked_gen = ChunkedContentGenerator(client)
    cluster = chunked_gen.generate_pillar_cluster(outline, language="ko")

    # 모드 1: 단일 stitch
    single_html = cluster.stitch_single()

    # 모드 2: pillar + N cluster
    for chunk in cluster.all_chunks():
        await wp_client.create_draft(title=chunk.title, content=chunk.body_html, ...)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from loguru import logger

from wp_auto.ai.ollama_client import LLMClient, parse_json_response
from wp_auto.ai.content_generator import Outline, SYSTEM_PROMPTS

PROMPTS_DIR = Path(__file__).parent / "prompts"
SUPPORTED_LANGUAGES = ("ko", "en")

# 1 chunk의 권장 분량 (글자)
DEFAULT_CHUNK_CHARS = 300
PILLAR_CHARS = 400
# 기본 chunk 개수 (plan 단계 기본값)
DEFAULT_TARGET_CHUNKS = 5


# ---------------------------------------------------------------------------
# 데이터 모델
# ---------------------------------------------------------------------------


@dataclass
class Subtopic:
    """1개 chunk의 설계 단위."""

    id: str                       # "background", "method", "example", ...
    title: str                    # H2 제목
    summary: str                  # 1-2문장 요약
    focus_keyword: str = ""       # 이 chunk의 메인 키워드


@dataclass
class ChunkedPost:
    """1개 chunk (cluster 또는 pillar)."""

    subtopic_id: str
    title: str
    body_html: str
    meta_description: str
    keyword: str = ""
    slug: str = ""
    h2_anchor: str = ""            # TOC anchor (e.g., "background")
    prev_slug: str | None = None
    next_slug: str | None = None
    related_slugs: list[str] = field(default_factory=list)
    language: str = "ko"


@dataclass
class PillarCluster:
    """pillar 1 + chunks N = 한 '긴 글' 단위."""

    pillar: ChunkedPost
    chunks: list[ChunkedPost]
    topic: str
    keyword: str
    language: str
    category: str = ""            # WP category 전체 묶음용 (e.g. "news-2026-08-03")
    schema_jsonld: str = ""
    toc_html: str = ""

    def all_chunks(self) -> list[ChunkedPost]:
        """pillar + chunks 순서대로 반환."""
        return [self.pillar, *self.chunks]

    # ----- 모드 1: 단일 stitch HTML -----
    def stitch_single(self) -> str:
        """모든 chunk를 1 HTML에 stitch (TOC + intro + body + 결론)."""
        parts: list[str] = []
        # Pillar (intro + TOC + 결론)
        parts.append(self.pillar.body_html)
        # 중간 chunks (H2 anchor로 식별)
        for ch in self.chunks:
            anchor = ch.h2_anchor or ch.subtopic_id
            parts.append(f'<section id="chunk-{anchor}" data-chunk="{ch.subtopic_id}">')
            parts.append(f'<h2 id="chunk-{anchor}">{ch.title}</h2>')
            parts.append(ch.body_html)
            parts.append(
                f'<nav class="chunk-nav" aria-label="chunk navigation">'
                f'{self._nav_links(ch)}</nav>'
            )
            parts.append('</section>')
        return "\n".join(parts)

    def _nav_links(self, chunk: ChunkedPost) -> str:
        prev_link = (
            f'<a href="#chunk-{chunk.prev_slug}">← {chunk.prev_slug}</a>'
            if chunk.prev_slug else ""
        )
        next_link = (
            f'<a href="#chunk-{chunk.next_slug}">{chunk.next_slug} →</a>'
            if chunk.next_slug else ""
        )
        related = " ".join(
            f'<a href="#chunk-{r}">{r}</a>' for r in chunk.related_slugs
        )
        return f"{prev_link} &nbsp; {next_link} &nbsp; {related}"

    # ----- 모드 2: N+1개 posts (pillar + chunks) -----
    def to_wp_post_specs(self) -> list[dict]:
        """WP publish용 specs (pillar 1 + chunks N)."""
        specs: list[dict] = []
        # pillar
        specs.append({
            "slug": self.pillar.slug or "pillar",
            "title": self.pillar.title,
            "content": self.pillar.body_html,
            "excerpt": self.pillar.meta_description,
            "type": "pillar",
        })
        # chunks
        for ch in self.chunks:
            content_parts = [ch.body_html, f'<nav class="chunk-nav">']
            if ch.prev_slug:
                content_parts.append(f'<a href="/{ch.prev_slug}">← 이전</a>')
            if ch.next_slug:
                content_parts.append(f'<a href="/{ch.next_slug}">다음 →</a>')
            for r in ch.related_slugs:
                content_parts.append(f'<a href="/{r}">{r}</a>')
            content_parts.append('</nav>')
            specs.append({
                "slug": ch.slug or ch.subtopic_id,
                "title": ch.title,
                "content": "\n".join(content_parts),
                "excerpt": ch.meta_description,
                "type": "chunk",
            })
        return specs


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


class ChunkedContentGenerator:
    """Chunked pillar-cluster content generator.

    흐름:
        1. plan_subtopics(outline) → N개 subtopic
        2. generate_chunks(subtopics) → N개 ChunkedPost (200-400자 each)
        3. generate_pillar(subtopics, chunks) → 1개 pillar ChunkedPost
        4. generate_pillar_cluster(outline) → 위 1-3 한번에
    """

    def __init__(
        self,
        client: LLMClient,
        prompts_dir: Path = PROMPTS_DIR,
        chunk_chars: int = DEFAULT_CHUNK_CHARS,
        target_chunks: int = DEFAULT_TARGET_CHUNKS,
    ) -> None:
        self.client = client
        self.prompts_dir = prompts_dir
        self.chunk_chars = chunk_chars
        self.target_chunks = target_chunks
        # 언어별 prompt 3종 로드
        self._templates: dict[str, dict[str, str]] = {
            lang: {
                "plan": (prompts_dir / lang / "chunk_plan.txt").read_text(encoding="utf-8"),
                "body": (prompts_dir / lang / "chunk_body.txt").read_text(encoding="utf-8"),
                "pillar": (prompts_dir / lang / "pillar.txt").read_text(encoding="utf-8"),
            }
            for lang in SUPPORTED_LANGUAGES
        }
        logger.info(
            "ChunkedContentGenerator initialized: chunk_chars={}, target_chunks={}, languages={}",
            chunk_chars, target_chunks, list(self._templates.keys()),
        )

    def _system_prompt(self, language: str) -> str:
        if language not in SYSTEM_PROMPTS:
            language = "ko"
        return SYSTEM_PROMPTS[language]

    # ------------------------------------------------------------------ step 1
    def plan_subtopics(
        self,
        outline: Outline,
        language: str = "ko",
        target_chunks: int | None = None,
    ) -> list[Subtopic]:
        """outline → N개 subtopic (각 = 1 chunk).

        Args:
            outline: 글 개요
            language: 'ko' 또는 'en'
            target_chunks: 정확히 이 개수의 subtopic 생성 (None이면 self.target_chunks)
                          LLM이 N+1을 반환하면 truncate, 부족하면 fallback.
        """
        if language not in self._templates:
            raise ValueError(f"Unsupported language: {language}")
        if target_chunks is None:
            target_chunks = self.target_chunks
        prompt = self._templates[language]["plan"].format(
            topic=outline.title,
            keyword=outline.title,  # outline.title이 가장 대표 키워드
            outline=outline.outline_text(),
            target_chunks=target_chunks,
        )
        logger.info(
            "plan_subtopics: lang={} topic='{}' outline_h2={} target_chunks={}",
            language, outline.title[:40], len(outline.outline), target_chunks,
        )
        response = self.client.generate(
            prompt,
            system=self._system_prompt(language),
            temperature=0.5,
            max_tokens=1500,
        )
        try:
            data = parse_json_response(response)
            items = data.get("subtopics", [])
            if not items and "outline" in data:
                # fallback: outline 키로 시도
                items = [
                    {"id": f"h2-{i}", "title": h.get("h2", ""), "summary": "", "focus_keyword": ""}
                    for i, h in enumerate(data["outline"])
                ]
            subtopics = [
                Subtopic(
                    id=str(it.get("id", f"chunk-{i}")).lower().replace(" ", "-"),
                    title=it.get("title", ""),
                    summary=it.get("summary", ""),
                    focus_keyword=it.get("focus_keyword", ""),
                )
                for i, it in enumerate(items)
            ]
            # LLM이 N+1을 반환하면 target_chunks로 truncate
            if len(subtopics) > target_chunks:
                logger.warning(
                    "plan_subtopics: LLM returned {} subtopics, truncating to {}",
                    len(subtopics), target_chunks,
                )
                subtopics = subtopics[:target_chunks]
            elif len(subtopics) < target_chunks:
                logger.warning(
                    "plan_subtopics: LLM returned {} subtopics, less than target {}",
                    len(subtopics), target_chunks,
                )
            return subtopics
        except Exception as e:
            logger.error("plan_subtopics JSON parse failed: {}", e)
            # fallback: outline H2를 그대로 1 subtopic = 1 chunk으로
            return [
                Subtopic(
                    id=f"h2-{i}",
                    title=h.get("h2", ""),
                    summary="; ".join(h.get("h3", [])),
                    focus_keyword=outline.title,
                )
                for i, h in enumerate(outline.outline)
            ]

    # ------------------------------------------------------------------ step 2
    def generate_chunks(
        self,
        outline: Outline,
        subtopics: list[Subtopic],
        language: str = "ko",
    ) -> list[ChunkedPost]:
        """N개 subtopic 각각 → N개 ChunkedPost (병렬 가능하지만 순차)."""
        if language not in self._templates:
            raise ValueError(f"Unsupported language: {language}")

        chunks: list[ChunkedPost] = []
        n = len(subtopics)
        for i, st in enumerate(subtopics):
            # prev / next 슬러그 결정
            prev_slug = subtopics[i - 1].id if i > 0 else None
            next_slug = subtopics[i + 1].id if i < n - 1 else None
            related = [s.id for j, s in enumerate(subtopics) if abs(j - i) == 1][:2]

            prompt = self._templates[language]["body"].format(
                topic=outline.title,
                keyword=outline.title,
                subtopic_id=st.id,
                subtopic_title=st.title,
                subtopic_summary=st.summary,
                focus_keyword=st.focus_keyword or outline.title,
                chunk_chars=self.chunk_chars,
                prev_slug=prev_slug or "(none)",
                next_slug=next_slug or "(none)",
                related_slugs=", ".join(related) if related else "(none)",
            )
            logger.info(
                "generate_chunk [{}/{}]: id={} title='{}'",
                i + 1, n, st.id, st.title[:30],
            )
            t0_time = __import__("time").time()
            try:
                body = self.client.generate(
                    prompt,
                    system=self._system_prompt(language),
                    temperature=0.7,
                    max_tokens=int(self.chunk_chars * 1.5),  # 한/영 토큰 비율 마진
                )
            except Exception as e:
                logger.error("chunk '{}' failed: {}", st.id, e)
                body = f"<p>{st.summary}</p>"
            elapsed = __import__("time").time() - t0_time
            logger.info("  → chunk '{}' done in {:.1f}s ({}자)", st.id, elapsed, len(body))

            chunk = ChunkedPost(
                subtopic_id=st.id,
                title=st.title,
                body_html=body.strip(),
                meta_description=st.summary[:160] if st.summary else st.title,
                keyword=st.focus_keyword or outline.title,
                slug=st.id,
                h2_anchor=st.id,
                prev_slug=prev_slug,
                next_slug=next_slug,
                related_slugs=related,
                language=language,
            )
            chunks.append(chunk)
        return chunks

    # ------------------------------------------------------------------ step 3
    def generate_pillar(
        self,
        outline: Outline,
        subtopics: list[Subtopic],
        chunks: list[ChunkedPost],
        language: str = "ko",
    ) -> ChunkedPost:
        """pillar (intro + TOC + 결론 + 모든 chunk로 internal links)."""
        if language not in self._templates:
            raise ValueError(f"Unsupported language: {language}")

        # chunk 목록을 pillar에 전달
        chunk_summaries = "\n".join(
            f"- id={c.subtopic_id}, title='{c.title}', slug='{c.slug}'"
            for c in chunks
        )
        prompt = self._templates[language]["pillar"].format(
            topic=outline.title,
            keyword=outline.title,
            chunk_summaries=chunk_summaries,
            pillar_chars=PILLAR_CHARS,
        )
        logger.info("generate_pillar: lang={} topic='{}'", language, outline.title[:40])
        try:
            body = self.client.generate(
                prompt,
                system=self._system_prompt(language),
                temperature=0.5,
                max_tokens=int(PILLAR_CHARS * 1.5),
            )
        except Exception as e:
            logger.error("pillar failed: {}", e)
            body = f"<p>{outline.meta_description}</p>"

        return ChunkedPost(
            subtopic_id="pillar",
            title=outline.title + " (개요)" if language == "ko" else outline.title + " (Overview)",
            body_html=body.strip(),
            meta_description=outline.meta_description,
            keyword=outline.title,
            slug="pillar",
            h2_anchor="pillar",
            prev_slug=None,
            next_slug=chunks[0].slug if chunks else None,
            related_slugs=[c.slug for c in chunks[:3]],
            language=language,
        )

    # ------------------------------------------------------------------ all-in-one
    def generate_pillar_cluster(
        self,
        outline: Outline,
        language: str = "ko",
        target_chunks: int | None = None,
    ) -> PillarCluster:
        """outline → N개 chunk + 1개 pillar 한 번에.

        Args:
            outline: 글 개요
            language: 'ko' 또는 'en'
            target_chunks: 정확히 이 개수의 chunk (None이면 self.target_chunks)
        """
        subtopics = self.plan_subtopics(outline, language, target_chunks=target_chunks)
        chunks = self.generate_chunks(outline, subtopics, language)
        pillar = self.generate_pillar(outline, subtopics, chunks, language)
        return PillarCluster(
            pillar=pillar,
            chunks=chunks,
            topic=outline.title,
            keyword=outline.title,
            language=language,
            category=f"chunked-{language}",
        )


__all__ = [
    "Subtopic",
    "ChunkedPost",
    "PillarCluster",
    "ChunkedContentGenerator",
    "SUPPORTED_LANGUAGES",
]
