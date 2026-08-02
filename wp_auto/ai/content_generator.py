"""콘텐츠 생성 오케스트레이션: outline → draft → review.

사용법:
    from wp_auto.ai.ollama_client import OllamaClient
    from wp_auto.ai.content_generator import ContentGenerator

    client = OllamaClient(model="llama3.1:8b")
    gen = ContentGenerator(client)
    html = gen.generate_full_post(
        topic="워드프레스 SEO 7가지 핵심 전략",
        keyword="워드프레스 SEO",
        intent="informational",
        length=3000,
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from wp_auto.ai.ollama_client import LLMClient

PROMPTS_DIR = Path(__file__).parent / "prompts"


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
    outline: Outline | None = None
    score: dict | None = None
    iterations: int = 1


class ContentGenerator:
    """AI 글 생성 오케스트레이션.

    흐름:
        1. outline 생성 (저비용, JSON)
        2. 본문 생성 (outline 기반 HTML)
        3. 점수화 (선택)
        4. 점수 < 75면 review + 재생성 (max 3 iterations)
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
        self._outline_template = (prompts_dir / "outline.txt").read_text(encoding="utf-8")
        self._draft_template = (prompts_dir / "draft.txt").read_text(encoding="utf-8")
        self._review_template = (prompts_dir / "review.txt").read_text(encoding="utf-8")
        self._alt_template = (prompts_dir / "alt_text.txt").read_text(encoding="utf-8")
        logger.info(
            "ContentGenerator initialized: min_score={}, max_iterations={}",
            min_score,
            max_iterations,
        )

    def generate_outline(
        self,
        topic: str,
        keyword: str,
        intent: str = "informational",
        length: int = 3000,
    ) -> Outline:
        """글 개요 (JSON) 생성."""
        prompt = self._outline_template.format(
            topic=topic, keyword=keyword, intent=intent, length=length
        )
        logger.info("generate_outline: topic='{}', keyword='{}'", topic[:30], keyword)
        response = self.client.generate(prompt, temperature=0.7, max_tokens=2000)

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
                meta_description=f"{topic}에 대한 완벽 가이드. {keyword} 핵심 정리.",
                slug=keyword.replace(" ", "-").lower(),
                outline=[{"h2": "개요", "h3": []}, {"h2": "결론", "h3": []}],
                faq=[],
                key_takeaways=[],
            )

    def generate_draft(
        self,
        outline: Outline,
        keyword: str,
        tone: str = "친근한 전문가",
        length: int = 3000,
    ) -> str:
        """outline 기반 본문 HTML 생성."""
        outline_str = outline.outline_text()
        prompt = self._draft_template.format(
            keyword=keyword, tone=tone, length=length, outline=outline_str
        )
        logger.info("generate_draft: keyword='{}', outline_h2={}", keyword, len(outline.outline))
        return self.client.generate(prompt, temperature=0.7, max_tokens=4000)

    def review(
        self,
        html: str,
        keyword: str,
        current_score: float,
        level: str,
        feedback: list[str],
        recommendations: list[str],
    ) -> str:
        """점수 미달 시 권고 반영하여 본문 개선."""
        prompt = self._review_template.format(
            keyword=keyword,
            current_score=current_score,
            level=level,
            feedback="; ".join(feedback) or "없음",
            recommendations="; ".join(recommendations) or "없음",
            html=html[:5000],  # 토큰 절약
        )
        logger.info("review: score={}, feedback_count={}", current_score, len(feedback))
        return self.client.generate(prompt, temperature=0.5, max_tokens=4000)

    def generate_alt_text(
        self,
        keyword: str,
        filename: str,
        context: str = "",
    ) -> str:
        """이미지 alt 텍스트 생성."""
        prompt = self._alt_template.format(
            keyword=keyword, filename=filename, context=context
        )
        response = self.client.generate(prompt, temperature=0.5, max_tokens=200)
        # 마침표 제거, 한 줄
        return response.strip().rstrip(".")

    def generate_full_post(
        self,
        topic: str,
        keyword: str,
        intent: str = "informational",
        length: int = 3000,
        tone: str = "친근한 전문가",
        enable_review: bool = True,
    ) -> GeneratedPost:
        """outline + draft + (선택) review 전체 흐름.

        Args:
            enable_review: True면 점수 < min_score 일 때 review + 재생성 (max max_iterations)
        """
        outline = self.generate_outline(topic, keyword, intent, length)
        html = self.generate_draft(outline, keyword, tone, length)

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
                        "iteration {}: score={:.1f} level={}",
                        i + 1,
                        result.total_score,
                        result.level.value,
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
                        )
                        iterations += 1
            except Exception as e:
                logger.error("review iteration failed: {}", e)

        return GeneratedPost(
            title=outline.title,
            meta_description=outline.meta_description,
            slug=outline.slug,
            html=html,
            outline=outline,
            score=score_info,
            iterations=iterations,
        )


__all__ = ["ContentGenerator", "GeneratedPost", "Outline"]
