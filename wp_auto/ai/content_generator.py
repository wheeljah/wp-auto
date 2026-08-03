"""콘텐츠 생성 오케스트레이션: outline → draft → review.

다국어 지원: 한국어(ko) / 영어(en) — 각 언어별 prompt set을 prompts/{lang}/ 에서 로드.

사용법:
    from wp_auto.ai.ollama_client import OllamaClient
    from wp_auto.ai.content_generator import ContentGenerator

    client = OllamaClient(model="qwen2.5:7b")
    gen = ContentGenerator(client)

    # 단일 언어 (한국어 기본)
    post = gen.generate_full_post(topic="워드프레스 SEO 7가지", keyword="워드프레스 SEO")

    # 한 번에 두 언어 모두 생성
    bilingual = gen.generate_multilang_post(
        topic="워드프레스 SEO 7가지 핵심 전략",
        keyword="워드프레스 SEO",
        languages=["ko", "en"],
    )
    # bilingual["ko"].html, bilingual["en"].html
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from loguru import logger

from wp_auto.ai.ollama_client import LLMClient

PROMPTS_DIR = Path(__file__).parent / "prompts"
SUPPORTED_LANGUAGES = ("ko", "en")

# Per-language system prompt — 강제 language isolation (qwen2.5가 중국어/일본어로 새는 것 방지)
SYSTEM_PROMPTS: dict[str, str] = {
    "ko": (
        "당신은 한국어 블로그 글쓰기 전문가입니다. "
        "모든 응답을 자연스러운 한국어로만 작성하세요. "
        "중국어, 일본어, 영어를 포함한 다른 언어는 절대 사용하지 마세요. "
        "사용자가 다른 언어로 요청하더라도 반드시 한국어로 답하세요."
    ),
    "en": (
        "You are a professional English blog writer. "
        "Always respond in clear, natural English only. "
        "Never use any other language (Korean, Chinese, Japanese, etc.). "
        "Even if the user requests another language, you must respond in English."
    ),
}


@dataclass
class Outline:
    """글 개요."""

    title: str
    meta_description: str
    slug: str
    outline: list[dict] = field(default_factory=list)  # [{"h2": "...", "h3": [...]}]
    faq: list[dict] = field(default_factory=list)  # [{"q": "...", "a": "..."}]
    key_takeaways: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "meta_description": self.meta_description,
            "slug": self.slug,
            "outline": self.outline,
            "faq": self.faq,
            "key_takeaways": self.key_takeaways,
        }

    def outline_text(self) -> str:
        """outline을 텍스트로 직렬화 (draft 프롬프트용)."""
        lines = []
        for i, item in enumerate(self.outline, 1):
            lines.append(f"{i}. H2: {item.get('h2', '')}")
            for h3 in item.get("h3", []):
                lines.append(f"   - H3: {h3}")
        return "\n".join(lines)


@dataclass
class GeneratedPost:
    """생성된 글 결과."""

    title: str
    meta_description: str
    slug: str
    html: str
    language: str = "ko"
    outline: Outline | None = None
    score: dict | None = None
    iterations: int = 1


class ContentGenerator:
    """AI 글 생성 오케스트레이션 (다국어 지원).

    흐름:
        1. outline 생성 (저비용, JSON)
        2. 본문 생성 (outline 기반 HTML)
        3. 점수화 (선택)
        4. 점수 < 75면 review + 재생성 (max 3 iterations)

    다국어: language 인자 (ko/en) 또는 generate_multilang_post(languages=[...]).
    """

    def __init__(
        self,
        client: LLMClient,
        prompts_dir: Path = PROMPTS_DIR,
        min_score: float = 75.0,
        max_iterations: int = 3,
    ) -> None:
        self.client = client
        self.prompts_dir = prompts_dir
        self.min_score = min_score
        self.max_iterations = max_iterations
        # 언어별 prompt 4종 로드 (ko + en)
        self._templates: dict[str, dict[str, str]] = {
            lang: {
                "outline": (prompts_dir / lang / "outline.txt").read_text(encoding="utf-8"),
                "draft": (prompts_dir / lang / "draft.txt").read_text(encoding="utf-8"),
                "review": (prompts_dir / lang / "review.txt").read_text(encoding="utf-8"),
                "alt": (prompts_dir / lang / "alt_text.txt").read_text(encoding="utf-8"),
            }
            for lang in SUPPORTED_LANGUAGES
        }
        logger.info(
            "ContentGenerator initialized: min_score={}, max_iterations={}, languages={}",
            min_score, max_iterations, list(self._templates.keys()),
        )

    def _system_prompt(self, language: str) -> str:
        """언어별 system prompt 반환 (없으면 ko fallback)."""
        if language not in SYSTEM_PROMPTS:
            logger.warning("Unknown language '{}', fallback to 'ko'", language)
            language = "ko"
        return SYSTEM_PROMPTS[language]

    def generate_outline(
        self,
        topic: str,
        keyword: str,
        intent: str = "informational",
        length: int = 3000,
        language: str = "ko",
    ) -> Outline:
        """글 개요 (JSON) 생성."""
        if language not in self._templates:
            raise ValueError(f"Unsupported language: {language}. Use one of {SUPPORTED_LANGUAGES}")
        prompt = self._templates[language]["outline"].format(
            topic=topic, keyword=keyword, intent=intent, length=length
        )
        logger.info(
            "generate_outline: lang={} topic='{}', keyword='{}'",
            language, topic[:30], keyword,
        )
        response = self.client.generate(
            prompt,
            system=self._system_prompt(language),
            temperature=0.7,
            max_tokens=2000,
        )

        from wp_auto.ai.ollama_client import parse_json_response

        try:
            data = parse_json_response(response)
            return Outline(
                title=data.get("title", topic),
                meta_description=data.get("meta_description", ""),
                slug=data.get("slug", ""),
                outline=data.get("outline", []),
                faq=data.get("faq", []),
                key_takeaways=data.get("key_takeaways", []),
            )
        except Exception as e:
            logger.error("outline JSON parse failed: {} - response: {}", e, response[:200])
            # fallback: minimal outline
            return Outline(
                title=topic,
                meta_description=f"{topic}에 대한 완벽 가이드. {keyword} 핵심 정리."
                if language == "ko"
                else f"A complete guide to {topic}. Key {keyword} insights.",
                slug=keyword.replace(" ", "-").lower(),
                outline=[{"h2": "개요" if language == "ko" else "Overview", "h3": []},
                         {"h2": "결론" if language == "ko" else "Conclusion", "h3": []}],
                faq=[],
                key_takeaways=[],
            )

    def generate_draft(
        self,
        outline: Outline,
        keyword: str,
        tone: str = "친근한 전문가",
        length: int = 3000,
        language: str = "ko",
    ) -> str:
        """outline 기반 본문 HTML 생성."""
        if language not in self._templates:
            raise ValueError(f"Unsupported language: {language}. Use one of {SUPPORTED_LANGUAGES}")
        outline_str = outline.outline_text()
        prompt = self._templates[language]["draft"].format(
            keyword=keyword, tone=tone, length=length, outline=outline_str
        )
        logger.info(
            "generate_draft: lang={} keyword='{}', outline_h2={}",
            language, keyword, len(outline.outline),
        )
        return self.client.generate(
            prompt,
            system=self._system_prompt(language),
            temperature=0.7,
            max_tokens=4000,
        )

    def review(
        self,
        html: str,
        keyword: str,
        current_score: float,
        level: str,
        feedback: list[str],
        recommendations: list[str],
        language: str = "ko",
    ) -> str:
        """점수 미달 시 권고 반영하여 본문 개선."""
        if language not in self._templates:
            raise ValueError(f"Unsupported language: {language}. Use one of {SUPPORTED_LANGUAGES}")
        prompt = self._templates[language]["review"].format(
            keyword=keyword,
            current_score=current_score,
            level=level,
            feedback="; ".join(feedback) or "없음",
            recommendations="; ".join(recommendations) or "없음",
            html=html[:5000],  # 토큰 절약
        )
        logger.info("review: lang={} score={}, feedback_count={}", language, current_score, len(feedback))
        return self.client.generate(
            prompt,
            system=self._system_prompt(language),
            temperature=0.5,
            max_tokens=4000,
        )

    def generate_alt_text(
        self,
        keyword: str,
        filename: str,
        context: str = "",
        language: str = "ko",
    ) -> str:
        """이미지 alt 텍스트 생성."""
        if language not in self._templates:
            raise ValueError(f"Unsupported language: {language}. Use one of {SUPPORTED_LANGUAGES}")
        prompt = self._templates[language]["alt"].format(
            keyword=keyword, filename=filename, context=context
        )
        response = self.client.generate(
            prompt,
            system=self._system_prompt(language),
            temperature=0.5,
            max_tokens=200,
        )
        # 마침표 제거, 한 줄
        return response.strip().rstrip(".")

    def generate_full_post(
        self,
        topic: str,
        keyword: str,
        intent: str = "informational",
        length: int = 3000,
        tone: str = "친근한 전문가",
        language: str = "ko",
        enable_review: bool = True,
    ) -> GeneratedPost:
        """단일 언어 글 생성 (outline + draft + 선택 review).

        Args:
            language: "ko" (한국어) 또는 "en" (영어)
            enable_review: True면 점수 < min_score 일 때 review + 재생성 (max max_iterations)

        Returns:
            GeneratedPost (language 필드 포함)
        """
        outline = self.generate_outline(topic, keyword, intent, length, language=language)
        html = self.generate_draft(outline, keyword, tone, length, language=language)

        score_info: dict | None = None
        iterations = 1

        if enable_review:
            try:
                from wp_auto.core.content_score import (
                    SpecializedContentOptimizer,
                )

                optimizer = SpecializedContentOptimizer()
                for i in range(self.max_iterations):
                    result = optimizer.verify_html(html, focus_keyword=keyword)
                    score_info = {
                        "total_score": result.total_score,
                        "level": result.level.value,
                        "feedback": result.feedback,
                        "recommendations": result.recommendations,
                    }
                    logger.info(
                        "iteration {} (lang={}): score={:.1f} level={}",
                        i + 1, language, result.total_score, result.level.value,
                    )
                    if result.total_score >= self.min_score:
                        break
                    if i < self.max_iterations - 1:
                        html = self.review(
                            html,
                            keyword,
                            result.total_score,
                            result.level.value,
                            result.feedback,
                            result.recommendations,
                            language=language,
                        )
                        iterations += 1
            except Exception as e:
                logger.error("review iteration failed: {}", e)

        return GeneratedPost(
            title=outline.title,
            meta_description=outline.meta_description,
            slug=outline.slug,
            html=html,
            language=language,
            outline=outline,
            score=score_info,
            iterations=iterations,
        )

    def generate_multilang_post(
        self,
        topic: str,
        keyword: str,
        intent: str = "informational",
        length: int = 3000,
        tone: str = "친근한 전문가",
        languages: list[str] | None = None,
        enable_review: bool = True,
    ) -> dict[str, GeneratedPost]:
        """여러 언어 버전 동시 생성.

        Args:
            languages: 생성할 언어 코드 리스트. None이면 ["ko"] (한국어만).

        Returns:
            {language_code: GeneratedPost} dict. 예: {"ko": post_ko, "en": post_en}
        """
        if languages is None:
            languages = ["ko"]
        for lang in languages:
            if lang not in SUPPORTED_LANGUAGES:
                raise ValueError(
                    f"Unsupported language '{lang}'. Use one of {SUPPORTED_LANGUAGES}"
                )

        results: dict[str, GeneratedPost] = {}
        for lang in languages:
            logger.info("generate_multilang_post: starting language={}", lang)
            results[lang] = self.generate_full_post(
                topic=topic,
                keyword=keyword,
                intent=intent,
                length=length,
                tone=tone,
                language=lang,
                enable_review=enable_review,
            )
        logger.info("generate_multilang_post: done. languages={}", list(results.keys()))
        return results


__all__ = ["ContentGenerator", "GeneratedPost", "Outline", "SUPPORTED_LANGUAGES"]
