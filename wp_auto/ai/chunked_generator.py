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
from wp_auto.ai.hook_generator import HookGenerator
from wp_auto.ai.cta_injector import CTAInjector
from wp_auto.ai.link_verifier import LinkVerifier
from wp_auto.ai.structure_optimizer import StructureOptimizer

PROMPTS_DIR = Path(__file__).parent / "prompts"
SUPPORTED_LANGUAGES = ("ko", "en")

# 1 chunk의 권장 분량 (글자)
DEFAULT_CHUNK_CHARS = 300
PILLAR_CHARS = 400
# 기본 chunk 개수 (plan 단계 기본값)
DEFAULT_TARGET_CHUNKS = 5

# 지원되는 콘텐츠 스타일
STYLES = ("standard", "trend", "deep_dive")

# 스타일별 추가 지시 (prompt 끝에 append). language별 톤.
STYLE_INSTRUCTIONS: dict[str, dict[str, str]] = {
    "ko": {
        "trend": (
            "\n\n[트렌드 리포트 스타일] "
            "최신 데이터/통계/뉴스 앵글을 반드시 포함하고, "
            "'지금 왜 이게 중요한지(Why Now)'를 명확히 하세요. "
            "시각적 요소(콜아웃 박스, 이모지, 시간순 timeline)를 활용해 스캔 가능하게 만드세요."
        ),
        "deep_dive": (
            "\n\n[심층 분석 스타일] "
            "다각도 분석(긍정/부정/맥락), 인용, 데이터, 반론을 반드시 포함하여 "
            "'왜 이런 일이 벌어지는지(Why)' 깊이 파고드세요. "
            "전문가 인용과 데이터 소스를 명시하고, "
            "본문 끝에 '더 알아보기' CTA를 자연스럽게 배치하세요."
        ),
    },
    "en": {
        "trend": (
            "\n\n[Trend Report Style] "
            "Must include latest data/statistics/news angle. "
            "Make clear 'why this matters NOW'. "
            "Use visual elements (callout boxes, emojis, timeline) for scannability."
        ),
        "deep_dive": (
            "\n\n[Deep Dive Style] "
            "Must include multi-angle analysis (positive/negative/context), "
            "expert quotes, data, counterarguments. "
            "Cite expert opinions and data sources explicitly. "
            "Place a 'Learn more' CTA naturally at the end of the body."
        ),
    },
}


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
        style: str = "standard",
        verify_links: bool = False,
        optimize_structure: bool = False,
        author_name: str = "1인 운영자 (AI-assisted)",
    ) -> None:
        if style not in STYLES:
            raise ValueError(f"Invalid style: {style}. Supported: {STYLES}")
        self.client = client
        self.prompts_dir = prompts_dir
        self.chunk_chars = chunk_chars
        self.target_chunks = target_chunks
        self.style = style
        self.verify_links = verify_links
        self.optimize_structure = optimize_structure
        self.author_name = author_name
        # 언어별 prompt 3종 로드
        self._templates: dict[str, dict[str, str]] = {
            lang: {
                "plan": (prompts_dir / lang / "chunk_plan.txt").read_text(encoding="utf-8"),
                "body": (prompts_dir / lang / "chunk_body.txt").read_text(encoding="utf-8"),
                "pillar": (prompts_dir / lang / "pillar.txt").read_text(encoding="utf-8"),
            }
            for lang in SUPPORTED_LANGUAGES
        }
        # Hook/CTA/Verifier/Optimizer — lazy init
        self._hook_gens: dict[str, HookGenerator] = {}
        self._cta_injs: dict[str, CTAInjector] = {}
        self._link_verifier: LinkVerifier | None = None
        self._structure_optimizers: dict[str, StructureOptimizer] = {}
        logger.info(
            "ChunkedContentGenerator initialized: chunk_chars={}, target_chunks={}, style={}, verify_links={}, optimize_structure={}, languages={}",
            chunk_chars, target_chunks, style, verify_links, optimize_structure, list(self._templates.keys()),
        )

    def _get_link_verifier(self) -> LinkVerifier | None:
        if not self.verify_links:
            return None
        if self._link_verifier is None:
            self._link_verifier = LinkVerifier(timeout=5.0, max_concurrent=3)
        return self._link_verifier

    def _get_structure_optimizer(self, language: str) -> StructureOptimizer:
        if language not in self._structure_optimizers:
            self._structure_optimizers[language] = StructureOptimizer(
                author_name=self.author_name, language=language
            )
        return self._structure_optimizers[language]

    def _get_hook_gen(self, language: str) -> HookGenerator:
        if language not in self._hook_gens:
            self._hook_gens[language] = HookGenerator(self.client, language=language)
        return self._hook_gens[language]

    def _get_cta_inj(self, language: str) -> CTAInjector:
        if language not in self._cta_injs:
            self._cta_injs[language] = CTAInjector(self.client, language=language)
        return self._cta_injs[language]

    def _style_instruction(self, language: str) -> str:
        """style에 따라 prompt 끝에 append할 instruction."""
        if self.style == "standard":
            return ""
        return STYLE_INSTRUCTIONS.get(language, {}).get(self.style, "")

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
        """N개 subtopic 각각 → N개 ChunkedPost (병렬 가능하지만 순차).

        style != "standard"이면:
          - prompt 끝에 style instruction append
          - chunk body 끝에 CTA 자동 삽입 (3종 round-robin)
        """
        if language not in self._templates:
            raise ValueError(f"Unsupported language: {language}")

        # style != standard면 CTA 3종 한 번에 생성 (전체 chunks에 round-robin)
        ctas = []
        cta_inj = None
        if self.style != "standard":
            cta_inj = self._get_cta_inj(language)
            ctas = cta_inj.generate_ctas(
                topic=outline.title,
                summary=outline.meta_description,
                keyword=outline.title,
                position="chunk_end",
            )
            logger.info("generate_chunks: {} CTAs for round-robin", len(ctas))

        style_instruction = self._style_instruction(language)
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
            # style instruction append (prompt 파일 변경 없이)
            if style_instruction:
                prompt = prompt + style_instruction
            logger.info(
                "generate_chunk [{}/{}]: id={} title='{}' style={}",
                i + 1, n, st.id, st.title[:30], self.style,
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

            # 외부 링크 검증 (broken link → 텍스트로 변환)
            verifier = self._get_link_verifier()
            if verifier:
                body, removed = verifier.verify_and_clean_html(body)
                if removed:
                    logger.info("  → link verified: {} broken removed", len(removed))

            # style != standard면 chunk body 끝에 CTA 주입 (round-robin)
            if ctas and cta_inj:
                cta = ctas[i % len(ctas)]
                body = cta_inj.inject_into_html(body, cta, position="end")
                logger.info("  → CTA injected: type={}", cta.type)

            # structure optimize: chunk에는 related_items + E-E-A-T footer만
            if self.optimize_structure:
                optimizer = self._get_structure_optimizer(language)
                related_items = []
                for j, s in enumerate(subtopics):
                    if s.id == st.id:
                        continue
                    # related에 들어간 것만 (이웃 2개)
                    if s.id in related:
                        related_items.append({
                            "title": s.title,
                            "url": f"#chunk-{s.id}",
                            "description": s.summary[:80] if s.summary else "",
                        })
                body = optimizer.optimize_chunk(body, related_items=related_items)

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
        """pillar (intro + TOC + 결론 + 모든 chunk로 internal links).

        style != "standard"이면:
          - prompt 끝에 style instruction append
          - pillar body 시작에 hook (1-2문장 강력한 도입) prepend
          - pillar body 끝에 CTA 주입
        """
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
        # style instruction append
        style_instruction = self._style_instruction(language)
        if style_instruction:
            prompt = prompt + style_instruction
        logger.info("generate_pillar: lang={} topic='{}' style={}", language, outline.title[:40], self.style)
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

        # style != standard면 hook + CTA 주입
        if self.style != "standard":
            # 1) hook 생성 (1회)
            hook_gen = self._get_hook_gen(language)
            hook = hook_gen.generate_best_hook(
                topic=outline.title,
                keyword=outline.title,
                context=outline.meta_description,
            )
            hook_html = (
                f'<div class="wp-auto-hook" style="'
                f'margin:0 0 24px 0;padding:18px 22px;'
                f'border-left:5px solid #f59e0b;background:#fffbeb;'
                f'border-radius:6px;font-size:18px;line-height:1.6;'
                f'font-weight:600;color:#1a1a1a;">'
                f'<span style="display:inline-block;margin-right:8px;color:#f59e0b;">⚡</span>'
                f'{hook.text}</div>'
            )
            body = hook_html + "\n\n" + body.strip()
            logger.info("  → hook injected: type={} text='{}'", hook.type, hook.text[:60])

            # 2) CTA 주입 (chunks와 다른 type 우선)
            cta_inj = self._get_cta_inj(language)
            ctas = cta_inj.generate_ctas(
                topic=outline.title,
                summary=outline.meta_description,
                keyword=outline.title,
                position="pillar_end",
            )
            if ctas:
                # chunk에서 이미 쓴 type은 피해서 다양성 보장
                chunk_cta_types = set()
                # (chunk body 끝의 wp-auto-cta div class로 type 추출은 복잡하므로 추정)
                # 단순화: chunk CTA는 round-robin 3종이 모두 사용됐다고 가정
                used_types = {c.type for c in ctas}  # 3종 모두 사용된 상태
                pillar_cta = ctas[0]  # fallback
                for c in ctas:
                    if c.type not in used_types or c.type == "action":
                        pillar_cta = c
                        break
                body = cta_inj.inject_into_html(body, pillar_cta, position="end")
                logger.info("  → pillar CTA injected: type={}", pillar_cta.type)

        # 외부 링크 검증
        verifier = self._get_link_verifier()
        if verifier:
            body, removed = verifier.verify_and_clean_html(body)
            if removed:
                logger.info("  → pillar link verified: {} broken removed", len(removed))

        # structure optimize: pillar에는 TL;DR + related + E-E-A-T footer
        # (FAQ는 LLM이 pillar body에 이미 작성 → 보강 안 함)
        if self.optimize_structure:
            optimizer = self._get_structure_optimizer(language)
            # TL;DR = outline.meta_description 사용
            tldr = outline.meta_description
            # article summary: chunk summaries에서 자동 생성
            chunk_summaries_list = [c.meta_description for c in chunks if c.meta_description]
            # related = cluster chunks 전체
            related_items = [
                {"title": c.title, "url": f"#chunk-{c.subtopic_id}",
                 "description": c.meta_description[:80] if c.meta_description else ""}
                for c in chunks
            ]
            body = optimizer.optimize_pillar(
                body,
                tldr=tldr,
                article_summary="",  # 빈 값이면 chunk_summaries로 자동 생성
                chunk_summaries=chunk_summaries_list,
                faqs=None,
                related_items=related_items,
            )
            logger.info("  → pillar structure optimized: TL;DR + Article Summary + related + E-E-A-T footer")

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

        Note:
            style은 ChunkedContentGenerator.__init__에서 설정.
            style='standard'면 기존 동작 (hook/CTA 없음).
            style='trend' 또는 'deep_dive'면 hook + CTA 자동 주입.
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
            category=f"chunked-{language}-{self.style}",
        )


__all__ = [
    "Subtopic",
    "ChunkedPost",
    "PillarCluster",
    "ChunkedContentGenerator",
    "SUPPORTED_LANGUAGES",
    "STYLES",
    "STYLE_INSTRUCTIONS",
]
