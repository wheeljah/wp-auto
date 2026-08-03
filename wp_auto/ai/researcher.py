"""Researcher: source 텍스트 → outline 자동 생성.

source_ingestor.py로 추출한 ExtractedText들을 입력으로 받아
기존 ContentGenerator와 호환되는 Outline을 생성합니다.

핵심 결정 (1차 출처 기반):
- **Fair Use 4 factors 준수** (US Copyright Office + Stanford Fair Use):
  1. Purpose and character: "transformative" (요약/재구성, 단순 복제 X)
  2. Nature of the work: 사실/뉴스/리뷰 (creative work보다 fair use 유리)
  3. Amount and substantiality: "최소화" (핵심 fact만 발췌, 전체 복제 X)
  4. Effect on the market: "시장 대체 X" (자체 분석/시각/cta 결합)
  - 출처: https://www.copyright.gov/fair-use/
  - 출처: https://fairuse.stanford.edu/overview/fair-use/four-factors/
  - 출처: https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title17-section107
- **"원문 복제 절대 금지"** prompt로 강제
- **인용/숫자는 출처 명시** (링크/footnote 형식)
- LLM이 자체 outline JSON 생성 (기존 Outline dataclass와 호환)

사용법:
    from wp_auto.ai.ollama_client import OllamaClient
    from wp_auto.ai.source_ingestor import ingest_sources, SourceRef
    from wp_auto.ai.researcher import Researcher

    client = OllamaClient(model="qwen2.5:7b")
    researcher = Researcher(client)

    refs = [SourceRef.from_url("https://example.com/news/123")]
    sources = ingest_sources(refs)
    outline = researcher.research(
        topic="미·이란 회담의 경제적 영향",
        keyword="미·이란 회담",
        intent="informational",
        sources=sources,
        language="ko",
    )
    # outline.to_dict() → 기존 ContentGenerator와 동일 형식
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from wp_auto.ai.content_generator import Outline, SYSTEM_PROMPTS
from wp_auto.ai.ollama_client import LLMClient, parse_json_response
from wp_auto.ai.source_ingestor import ExtractedText, SourceRef, extract_key_facts

PROMPTS_DIR = Path(__file__).parent / "prompts"
SUPPORTED_LANGUAGES = ("ko", "en")

# 1 source당 LLM에 전달할 최대 fact 수 (fair use "amount 최소화")
MAX_FACTS_PER_SOURCE = 8

# 1 source당 LLM에 전달할 최대 body 글자 수 (전체 복제 방지)
MAX_BODY_CHARS_PER_SOURCE = 1500


@dataclass
class ResearchContext:
    """Research 단계의 입력 컨텍스트."""

    topic: str
    keyword: str
    intent: str                              # informational | commercial investigation | transactional
    sources: list[ExtractedText]
    language: str = "ko"                    # "ko" | "en"
    target_length: int = 2000               # 목표 분량 (자)
    category: str = ""                       # WP category (선택)
    notes: str = ""                          # 추가 지시 (예: "한국 독자 대상")

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "keyword": self.keyword,
            "intent": self.intent,
            "language": self.language,
            "target_length": self.target_length,
            "category": self.category,
            "notes": self.notes,
            "source_count": len(self.sources),
        }


class Researcher:
    """Source → Outline 자동 생성.

    흐름:
        1. ctx.sources에서 fair use 준수 부분만 발췌 (key_facts + body 발췌)
        2. LLM 호출 → outline JSON (원문 복제 X, 요약/재구성)
        3. Outline dataclass로 파싱
    """

    def __init__(
        self,
        client: LLMClient,
        prompts_dir: Path = PROMPTS_DIR,
        max_facts_per_source: int = MAX_FACTS_PER_SOURCE,
        max_body_chars_per_source: int = MAX_BODY_CHARS_PER_SOURCE,
    ) -> None:
        self.client = client
        self.prompts_dir = prompts_dir
        self.max_facts_per_source = max_facts_per_source
        self.max_body_chars_per_source = max_body_chars_per_source
        # 언어별 prompt 로드
        self._templates: dict[str, str] = {
            lang: (prompts_dir / lang / "research.txt").read_text(encoding="utf-8")
            for lang in SUPPORTED_LANGUAGES
        }
        logger.info(
            "Researcher 초기화: max_facts/source={}, max_body_chars/source={}, languages={}",
            max_facts_per_source, max_body_chars_per_source, list(self._templates.keys()),
        )

    def research(self, ctx: ResearchContext) -> Outline:
        """source들을 참고해 Outline 생성.

        Args:
            ctx: ResearchContext (topic/keyword/intent/sources/language)

        Returns:
            Outline (기존 ContentGenerator와 호환)
        """
        if not ctx.sources:
            raise ValueError("ctx.sources 비어있음. 최소 1개 source 필요.")

        if ctx.language not in self._templates:
            raise ValueError(
                f"지원 안 되는 language: {ctx.language} (지원: {list(self._templates.keys())})"
            )

        # 1) fair use: 발췌 부분만 prompt에 포함
        source_excerpts = self._build_source_excerpts(ctx.sources)

        # 2) prompt 작성
        template = self._templates[ctx.language]
        prompt = template.format(
            topic=ctx.topic,
            keyword=ctx.keyword,
            intent=ctx.intent,
            target_length=ctx.target_length,
            source_count=len(ctx.sources),
            sources=source_excerpts,
            notes=ctx.notes or "(없음)",
        )

        system_prompt = SYSTEM_PROMPTS[ctx.language]

        # 3) LLM 호출
        logger.info(
            "LLM 호출 (research): topic={!r}, sources={}, language={}",
            ctx.topic, len(ctx.sources), ctx.language,
        )
        response = self.client.generate(
            prompt=prompt,
            system=system_prompt,
            temperature=0.3,  # 사실 기반이라 낮은 temperature
        )
        response_text = self._extract_response_text(response)

        # 4) JSON 파싱 → Outline
        data = parse_json_response(response_text)

        try:
            outline = Outline(
                title=data.get("title") or ctx.topic,
                meta_description=data.get("meta_description", ""),
                slug=data.get("slug", ""),
                outline=data.get("outline", []),
                faq=data.get("faq", []),
                key_takeaways=data.get("key_takeaways", []),
            )
        except Exception as e:
            logger.error("Outline 파싱 실패: {}", e)
            raise RuntimeError(f"LLM 응답을 Outline으로 변환 실패: {e}") from e

        logger.info(
            "Research 완료: title={!r}, h2_sections={}, faq={}, key_takeaways={}",
            outline.title, len(outline.outline), len(outline.faq), len(outline.key_takeaways),
        )
        return outline

    def _build_source_excerpts(self, sources: list[ExtractedText]) -> str:
        """Fair use 준수: source에서 발췌 부분만 추출 (원문 전체 X).

        1차 출처 (US Copyright Office + Stanford Fair Use):
        - "amount and substantiality of the portion used" 최소화
        - 핵심 fact만 발췌 (extract_key_facts)
        - body는 max_body_chars_per_source 글자만
        """
        excerpts: list[str] = []
        for i, src in enumerate(sources, 1):
            ref = src.source
            facts = (src.key_facts or extract_key_facts(src.body))[: self.max_facts_per_source]
            # body 발췌 (앞부분만)
            body_excerpt = src.body[: self.max_body_chars_per_source]
            if len(src.body) > self.max_body_chars_per_source:
                body_excerpt = body_excerpt.rsplit(" ", 1)[0] + "..."

            excerpt_parts = [
                f"### Source {i}: {src.title}",
                f"- URL/Path: {ref.display_name}",
                f"- Type: {ref.source_type}",
                f"- Original char count: {len(src.body)}",
            ]
            if src.metadata.get("sitename"):
                excerpt_parts.append(f"- Source site: {src.metadata['sitename']}")
            if src.metadata.get("date"):
                excerpt_parts.append(f"- Published: {src.metadata['date']}")
            if src.metadata.get("author"):
                excerpt_parts.append(f"- Author: {src.metadata['author']}")

            if facts:
                excerpt_parts.append("\n**Key facts (발췌, fair use):**")
                for j, f in enumerate(facts, 1):
                    excerpt_parts.append(f"  {j}. {f}")
            else:
                excerpt_parts.append("\n**Key facts (발췌, fair use):** (본문에서 fact 자동 추출 실패 — body excerpt 참고)")

            excerpt_parts.append(
                f"\n**Body excerpt (앞 {self.max_body_chars_per_source}자, fair use):**"
            )
            excerpt_parts.append(body_excerpt)

            excerpts.append("\n".join(excerpt_parts))

        return "\n\n---\n\n".join(excerpts)

    def _extract_response_text(self, response) -> str:
        """LLM 응답에서 텍스트 추출 (str/dict/object 모두 지원)."""
        if isinstance(response, str):
            return response
        if isinstance(response, dict):
            for key in ("response", "text", "content", "message"):
                if key in response and response[key]:
                    return str(response[key])
            return json.dumps(response, ensure_ascii=False)
        # 객체: .response or .text
        for attr in ("response", "text", "content"):
            if hasattr(response, attr):
                val = getattr(response, attr)
                if val:
                    return str(val)
        return str(response)


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "Researcher",
    "ResearchContext",
    "MAX_FACTS_PER_SOURCE",
    "MAX_BODY_CHARS_PER_SOURCE",
]
