"""콘텐츠 품질 점수화 코어 (SpecializedContentOptimizer).

원본: `범용_로직1.txt` L55-272 (Google E-E-A-T / SEO / Page Speed 기반)
이식: 2026-08-02, wp-auto v0.1
라이선스: 자료 인용 — 원본 코드는 사용자가 제공한 자료에 포함됨

가중치:
- Content Depth & Helpfulness: 40점
- E-E-A-T: 25점
- SEO Technical: 20점
- Page Speed Readiness: 15점

합격 기준:
- 90점 이상: 우수 (EXCELLENT)
- 75~89점: 발행 가능 (PASS)
- 75점 미만: 보완 필요 (FAIL)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List

from loguru import logger


class ContentQualityLevel(Enum):
    """콘텐츠 품질 판정 레벨."""

    FAIL = "보완 필요"
    PASS = "발행 가능"
    EXCELLENT = "우수"


@dataclass
class ContentMetrics:
    """콘텐츠 입력 메트릭.

    점수화에 필요한 모든 입력값. HTML 파싱 또는 수동 입력으로 채움.
    """

    title: str
    word_count: int
    has_original_analysis: bool = False
    has_step_by_step_guide: bool = False
    has_data_or_case: bool = False
    has_comparison_table: bool = False
    has_faq: bool = False
    author_experience_mentioned: bool = False
    author_bio_present: bool = False
    sources_cited: int = 0
    update_date_present: bool = False
    main_keyword_in_title: bool = False
    h2_count: int = 0
    internal_links: int = 0
    external_authority_links: int = 0
    meta_description_length: int = 0
    images_optimized: bool = False  # WebP + alt + size
    lazy_load_applied: bool = False
    unnecessary_js_css: bool = True  # True면 문제 있음
    estimated_lcp_ok: bool = False  # LCP ≤ 2.5s 예상
    mobile_friendly: bool = True


@dataclass
class VerificationResult:
    """점수화 결과."""

    total_score: float
    category_scores: dict[str, float]
    level: ContentQualityLevel
    feedback: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.level != ContentQualityLevel.FAIL

    @property
    def is_excellent(self) -> bool:
        return self.level == ContentQualityLevel.EXCELLENT


class SpecializedContentOptimizer:
    """특화 콘텐츠 + SEO + 페이지 속도 최적화 범용/검증 로직.

    사용법:
        optimizer = SpecializedContentOptimizer()
        result = optimizer.verify(metrics)
        optimizer.print_report(result)
    """

    def __init__(self) -> None:
        self.weights = {
            "content_depth": 40,
            "eeat": 25,
            "seo": 20,
            "speed": 15,
        }
        logger.debug("SpecializedContentOptimizer initialized with weights={}", self.weights)

    def verify(self, metrics: ContentMetrics) -> VerificationResult:
        """ContentMetrics → VerificationResult.

        각 카테고리별 점수 + 총점 + 레벨 + 피드백 + 권고를 반환.
        """
        scores: dict[str, float] = {}
        feedback: List[str] = []
        recommendations: List[str] = []

        # === 1. Content Depth & Helpfulness (40점) ===
        depth_score = 0
        if metrics.word_count >= 2500:
            depth_score += 12
        elif metrics.word_count >= 1800:
            depth_score += 8
        else:
            feedback.append("글자 수 부족 (권장 2,500자 이상)")
            recommendations.append("심층 분석과 가이드를 더 추가하세요.")

        if metrics.has_original_analysis:
            depth_score += 10
        else:
            feedback.append("원본 분석/인사이트 부족")
            recommendations.append("직접 테스트·데이터·고유 관점을 추가하세요.")

        if metrics.has_step_by_step_guide:
            depth_score += 8
        if metrics.has_data_or_case:
            depth_score += 5
        if metrics.has_comparison_table:
            depth_score += 3
        if metrics.has_faq:
            depth_score += 2

        scores["content_depth"] = min(depth_score, 40)

        # === 2. E-E-A-T (25점) ===
        eeat_score = 0
        if metrics.author_experience_mentioned:
            eeat_score += 8
        else:
            feedback.append("1차 경험 서술 부족")
            recommendations.append("본인이 직접 해본 경험이나 관찰을 구체적으로 쓰세요.")

        if metrics.author_bio_present:
            eeat_score += 6
        if metrics.sources_cited >= 3:
            eeat_score += 6
        elif metrics.sources_cited >= 1:
            eeat_score += 3
        else:
            feedback.append("신뢰할 수 있는 출처 부족")
            recommendations.append("권위 있는 외부 출처를 최소 3개 이상 인용하세요.")

        if metrics.update_date_present:
            eeat_score += 5

        scores["eeat"] = min(eeat_score, 25)

        # === 3. SEO Technical (20점) ===
        seo_score = 0
        if metrics.main_keyword_in_title:
            seo_score += 5
        if metrics.h2_count >= 4:
            seo_score += 5
        elif metrics.h2_count >= 2:
            seo_score += 3

        if metrics.internal_links >= 3:
            seo_score += 4
        if metrics.external_authority_links >= 2:
            seo_score += 3
        if 140 <= metrics.meta_description_length <= 165:
            seo_score += 3

        scores["seo"] = min(seo_score, 20)

        # === 4. Page Speed Readiness (15점) ===
        speed_score = 0
        if metrics.images_optimized:
            speed_score += 5
        else:
            feedback.append("이미지 최적화 미흡")
            recommendations.append("WebP 변환 + alt 텍스트 + 적절한 해상도로 리사이즈하세요.")

        if metrics.lazy_load_applied:
            speed_score += 3
        if not metrics.unnecessary_js_css:
            speed_score += 4
        else:
            feedback.append("불필요한 JS/CSS 존재 가능성")
            recommendations.append("외부 스크립트와 사용하지 않는 CSS를 최소화하세요.")

        if metrics.estimated_lcp_ok:
            speed_score += 3
        if metrics.mobile_friendly:
            speed_score += 0  # 기본 가점 없음, 필수 조건

        scores["speed"] = min(speed_score, 15)

        # === 총점 계산 ===
        total = sum(scores.values())

        # === 레벨 판정 ===
        if total >= 90:
            level = ContentQualityLevel.EXCELLENT
        elif total >= 75:
            level = ContentQualityLevel.PASS
        else:
            level = ContentQualityLevel.FAIL

        logger.info(
            "verify: title='{}' total={:.1f} level={}",
            metrics.title[:40],
            total,
            level.value,
        )

        return VerificationResult(
            total_score=round(total, 1),
            category_scores=scores,
            level=level,
            feedback=feedback,
            recommendations=recommendations,
        )

    def print_report(self, result: VerificationResult) -> None:
        """콘솔 리포트 출력 (사람이 읽기 좋은 형식)."""
        print("=" * 50)
        print(f"총점: {result.total_score} / 100")
        print(f"판정: {result.level.value}")
        print("-" * 50)
        for cat, score in result.category_scores.items():
            print(f"  {cat:20s}: {score:5.1f} / {self.weights[cat]}")
        print("-" * 50)
        if result.feedback:
            print("주요 문제점:")
            for f in result.feedback:
                print(f"  • {f}")
        if result.recommendations:
            print("\n개선 권장사항:")
            for r in result.recommendations:
                print(f"  → {r}")
        print("=" * 50)


__all__ = [
    "ContentQualityLevel",
    "ContentMetrics",
    "VerificationResult",
    "SpecializedContentOptimizer",
]
