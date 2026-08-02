"""Rank Math 스타일 SEO 분석기.

Rank Math의 점수화 로직을 Python으로 재구성 (자료 `워드프레스_자동화1.txt` L161-228 +
Rank Math 공식 문서 기반).
- 100점 만점
- 카테고리: basic_seo(30점), additional(40점), title_readability(15점), content_readability(15점)

출처:
- 자료 `워드프레스_자동화1.txt` L165-228: Rank Math 점수 항목
- Rank Math 공식 docs (https://rankmath.com/kb/score/): 항목별 가중치
- 자료 `범용_로직1.txt` L60-95: ContentMetrics 기본 필드와 호환

D3 범위: HTML 단일 입력 → 4개 카테고리 점수 + 총점.
정밀 SEO 분석이 필요하면 CustomSEOResult의 recommendations 참조.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup
from loguru import logger

# Power/Sentiment words that indicate "click-worthy" title
_POWER_WORDS = {
    "best", "ultimate", "guide", "tutorial", "complete", "definitive",
    "essential", "top", "easy", "quick", "fast", "free", "proven",
    "exclusive", "amazing", "incredible", "powerful", "최고", "완벽", "가이드", "튜토리얼", "추천", "비교", "리뷰", "방법",
}

# Common stopwords (skip from density calc)
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
    "for", "of", "with", "by", "is", "are", "was", "were", "be",
    "이", "가", "은", "는", "을", "를", "의", "에", "와", "과", "도", "로", "으로",
}


@dataclass
class SEOCheckItem:
    """개별 SEO 체크 항목 결과."""

    name: str
    passed: bool
    points_earned: float
    points_max: float
    detail: str = ""


@dataclass
class SEOResult:
    """Rank Math 스타일 SEO 점수 결과."""

    total_score: float
    category_scores: dict[str, float]
    category_maxima: dict[str, float]
    items: list[SEOCheckItem] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def passed(self) -> bool:
        return self.total_score >= 70

    def items_by_category(self, category: str) -> list[SEOCheckItem]:
        return [i for i in self.items if i.name.startswith(category + ".")]


class RankMathStyleAnalyzer:
    """Rank Math 점수화 로직 차용 (Python 포팅).

    사용법:
        analyzer = RankMathStyleAnalyzer()
        result = analyzer.analyze(html, focus_keyword="워드프레스 SEO")

    점수 분포 (100점 만점):
    - basic_seo: 30점 (URL, title 시작, title 포함, meta desc 시작, meta desc 길이, permalink, 첫 문단 키워드, 마지막 문단 키워드)
    - additional: 40점 (H2 키워드, density, 첫 10% 키워드, 마지막 10% 키워드, 내부 링크, 외부 링크, 이미지 alt)
    - title_readability: 15점 (숫자, 파워워드, 길이)
    - content_readability: 15점 (콘텐츠 길이 600+ 단어, 단락 길이, alt 개수, 콘텐츠가 비어있지 않음)

    점수 임계값 (Rank Math 기본과 동일):
    - 81+ : Great (green)
    - 51~80: Good (yellow)
    - 1~50:  Bad (red)
    - 0   :  N/A
    """

    # 카테고리 만점
    CATEGORY_MAX = {
        "basic_seo": 30,
        "additional": 40,
        "title_readability": 15,
        "content_readability": 15,
    }

    def __init__(self) -> None:
        logger.debug("RankMathStyleAnalyzer initialized")

    def analyze(self, html: str, focus_keyword: str | None = None) -> SEOResult:
        """HTML + focus_keyword → SEOResult."""
        if not focus_keyword:
            return SEOResult(
                total_score=0,
                category_scores=dict.fromkeys(self.CATEGORY_MAX, 0),
                category_maxima=self.CATEGORY_MAX,
                items=[],
                recommendations=["focus_keyword가 필요합니다."],
            )

        soup = BeautifulSoup(html, "lxml")
        items: list[SEOCheckItem] = []
        recommendations: list[str] = []

        # === Basic SEO (30점) ===
        items.extend(self._check_basic_seo(soup, focus_keyword, recommendations))

        # === Additional (40점) ===
        items.extend(self._check_additional(soup, focus_keyword, recommendations))

        # === Title Readability (15점) ===
        items.extend(self._check_title_readability(soup, recommendations))

        # === Content Readability (15점) ===
        items.extend(self._check_content_readability(soup, recommendations))

        # 카테고리별 점수 집계
        category_scores: dict[str, float] = dict.fromkeys(self.CATEGORY_MAX, 0.0)
        for item in items:
            cat = item.name.split(".")[0]
            if cat in category_scores:
                category_scores[cat] += item.points_earned

        # 카테고리 max clipping
        for cat, max_p in self.CATEGORY_MAX.items():
            category_scores[cat] = min(category_scores[cat], max_p)

        total = sum(category_scores.values())

        logger.info(
            "seo_analyze: keyword='{}' total={:.1f}",
            focus_keyword,
            total,
        )

        return SEOResult(
            total_score=round(total, 1),
            category_scores=category_scores,
            category_maxima=self.CATEGORY_MAX,
            items=items,
            recommendations=recommendations,
        )

    # === Basic SEO ===

    def _check_basic_seo(
        self, soup: BeautifulSoup, keyword: str, recommendations: list[str]
    ) -> list[SEOCheckItem]:
        items = []
        kw = keyword.lower()

        # 1. URL has keyword (4점) — slugs / canonical / og:url
        url_has_kw = False
        url = ""
        canonical = soup.find("link", rel="canonical")
        if canonical and canonical.get("href"):
            url = canonical["href"]
        og_url = soup.find("meta", property="og:url")
        if not url and og_url and og_url.get("content"):
            url = og_url["content"]
        if kw in url.lower():
            url_has_kw = True
        items.append(SEOCheckItem(
            name="basic_seo.url_has_keyword",
            passed=url_has_kw,
            points_earned=4 if url_has_kw else 0,
            points_max=4,
            detail=f"URL: {url[:60]}" if url else "URL 미발견",
        ))
        if not url_has_kw:
            recommendations.append("URL/슬러그에 메인 키워드를 포함하세요.")

        # 2. Title starts with keyword (4점)
        title = ""
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            title = title_tag.string.strip().lower()
        title_starts_kw = title.startswith(kw)
        items.append(SEOCheckItem(
            name="basic_seo.title_starts_with_keyword",
            passed=title_starts_kw,
            points_earned=4 if title_starts_kw else 0,
            points_max=4,
            detail=f"Title: {title[:60]}",
        ))
        if not title_starts_kw:
            recommendations.append("Title이 메인 키워드로 시작하면 좋습니다.")

        # 3. Title contains keyword (4점)
        title_contains_kw = kw in title
        items.append(SEOCheckItem(
            name="basic_seo.title_contains_keyword",
            passed=title_contains_kw,
            points_earned=4 if title_contains_kw else 0,
            points_max=4,
            detail=f"Title: {title[:60]}",
        ))
        if not title_contains_kw:
            recommendations.append("Title에 메인 키워드를 포함하세요.")

        # 4. Meta description starts with keyword (3점)
        meta = soup.find("meta", attrs={"name": "description"})
        meta_desc = (meta.get("content", "") if meta else "").strip().lower()
        meta_starts_kw = meta_desc.startswith(kw) if meta_desc else False
        items.append(SEOCheckItem(
            name="basic_seo.meta_description_starts_with_keyword",
            passed=meta_starts_kw,
            points_earned=3 if meta_starts_kw else 0,
            points_max=3,
            detail=f"Meta desc len: {len(meta_desc)}",
        ))

        # 5. Meta description length (4점) — 120-160자
        meta_len_ok = 120 <= len(meta_desc) <= 160
        items.append(SEOCheckItem(
            name="basic_seo.meta_description_length",
            passed=meta_len_ok,
            points_earned=4 if meta_len_ok else 0,
            points_max=4,
            detail=f"Length: {len(meta_desc)} chars (120-160 ideal)",
        ))
        if not meta_len_ok and meta_desc:
            recommendations.append("메타 설명 길이를 120-160자로 조정하세요.")

        # 6. Permalink short (4점) — slug 길이 < 75자
        permalink_short = True
        if "/" in url:
            slug = url.rstrip("/").split("/")[-1]
            permalink_short = len(slug) < 75
            items.append(SEOCheckItem(
                name="basic_seo.permalink_short",
                passed=permalink_short,
                points_earned=4 if permalink_short else 0,
                points_max=4,
                detail=f"Slug length: {len(slug)} chars",
            ))
        else:
            items.append(SEOCheckItem(
                name="basic_seo.permalink_short",
                passed=False,
                points_earned=0,
                points_max=4,
                detail="Slug 미발견",
            ))

        # 7. Focus keyword in first paragraph (4점)
        first_p = soup.find("p")
        first_p_text = first_p.get_text().lower() if first_p else ""
        first_p_kw = kw in first_p_text
        items.append(SEOCheckItem(
            name="basic_seo.first_paragraph_has_keyword",
            passed=first_p_kw,
            points_earned=4 if first_p_kw else 0,
            points_max=4,
        ))
        if not first_p_kw:
            recommendations.append("첫 문단에 메인 키워드를 포함하세요.")

        # 8. Focus keyword in last paragraph (3점)
        all_p = soup.find_all("p")
        last_p = all_p[-1] if all_p else None
        last_p_text = last_p.get_text().lower() if last_p else ""
        last_p_kw = kw in last_p_text
        items.append(SEOCheckItem(
            name="basic_seo.last_paragraph_has_keyword",
            passed=last_p_kw,
            points_earned=3 if last_p_kw else 0,
            points_max=3,
        ))

        return items

    # === Additional ===

    def _check_additional(
        self, soup: BeautifulSoup, keyword: str, recommendations: list[str]
    ) -> list[SEOCheckItem]:
        items = []
        kw = keyword.lower()

        # 본문 텍스트 (script/style 제거)
        body = soup.find("body") or soup
        for tag in body.find_all(["script", "style", "noscript"]):
            tag.decompose()
        full_text = body.get_text(separator=" ")
        full_text_lower = full_text.lower()

        # 1. Keyword in H2 (5점)
        h2_tags = soup.find_all("h2")
        h2_text = " ".join(h.get_text().lower() for h in h2_tags)
        h2_has_kw = kw in h2_text
        items.append(SEOCheckItem(
            name="additional.h2_has_keyword",
            passed=h2_has_kw,
            points_earned=5 if h2_has_kw else 0,
            points_max=5,
        ))
        if not h2_has_kw and h2_tags:
            recommendations.append("H2 헤딩 중 하나에 메인 키워드를 포함하세요.")

        # 2. Keyword density (5점) — 0.75% ~ 2.5% (Rank Math 기본)
        words = re.findall(r"\b\w+\b", full_text_lower)
        words = [w for w in words if w not in _STOPWORDS and len(w) > 1]
        kw_count = sum(1 for w in words if w == kw or kw in w)
        density = (kw_count / len(words) * 100) if words else 0
        density_ok = 0.75 <= density <= 2.5
        items.append(SEOCheckItem(
            name="additional.keyword_density",
            passed=density_ok,
            points_earned=5 if density_ok else 0,
            points_max=5,
            detail=f"Density: {density:.2f}% (0.75-2.5% ideal)",
        ))
        if not density_ok and words:
            if density < 0.75:
                recommendations.append("키워드 밀도가 낮습니다. 본문에 키워드를 더 추가하세요.")
            else:
                recommendations.append("키워드 밀도가 너무 높습니다. 자연스러운 분포로 줄이세요.")

        # 3. Keyword in first 10% of content (5점)
        first_10 = full_text_lower[: max(1, len(full_text_lower) // 10)]
        first_10_kw = kw in first_10
        items.append(SEOCheckItem(
            name="additional.first_10_percent_has_keyword",
            passed=first_10_kw,
            points_earned=5 if first_10_kw else 0,
            points_max=5,
        ))

        # 4. Keyword in last 10% of content (5점)
        last_10 = full_text_lower[-max(1, len(full_text_lower) // 10):]
        last_10_kw = kw in last_10
        items.append(SEOCheckItem(
            name="additional.last_10_percent_has_keyword",
            passed=last_10_kw,
            points_earned=5 if last_10_kw else 0,
            points_max=5,
        ))

        # 5. Internal links count (5점) — 최소 1개
        all_a = soup.find_all("a", href=True)
        internal_count = sum(
            1 for a in all_a
            if not a["href"].startswith(("http://", "https://", "//", "mailto:"))
        )
        internal_ok = internal_count >= 1
        items.append(SEOCheckItem(
            name="additional.internal_links",
            passed=internal_ok,
            points_earned=5 if internal_ok else 0,
            points_max=5,
            detail=f"Internal: {internal_count}",
        ))
        if not internal_ok:
            recommendations.append("최소 1개 이상의 내부 링크를 추가하세요.")

        # 6. External links count (5점) — 최소 1개
        external_count = sum(
            1 for a in all_a
            if a["href"].startswith(("http://", "https://", "//"))
        )
        external_ok = external_count >= 1
        items.append(SEOCheckItem(
            name="additional.external_links",
            passed=external_ok,
            points_earned=5 if external_ok else 0,
            points_max=5,
            detail=f"External: {external_count}",
        ))
        if not external_ok:
            recommendations.append("최소 1개 이상의 외부 링크를 추가하세요.")

        # 7. Image alt has keyword (5점) — <img> 중 alt에 키워드 포함
        imgs = soup.find_all("img")
        img_with_kw_alt = 0
        for img in imgs:
            alt = img.get("alt", "")
            if alt and kw in alt.lower():
                img_with_kw_alt += 1
        # 이미지가 있거나 1개 이상 alt에 키워드 있으면 만점
        img_alt_ok = (not imgs) or img_with_kw_alt >= 1
        items.append(SEOCheckItem(
            name="additional.image_alt_has_keyword",
            passed=img_alt_ok,
            points_earned=5 if img_alt_ok else 0,
            points_max=5,
            detail=f"이미지 {len(imgs)}개, alt에 키워드 {img_with_kw_alt}개",
        ))

        # 8. URL has keyword in slug part (5점) — additional 중복이지만 일부 점수
        # 여기선 보너스로: canonical URL의 마지막 segment에 키워드 포함
        url_has_slug_kw = False
        canonical = soup.find("link", rel="canonical")
        if canonical and canonical.get("href"):
            parts = canonical["href"].rstrip("/").split("/")
            if parts and any(kw in p.lower() for p in parts):
                url_has_slug_kw = True
        items.append(SEOCheckItem(
            name="additional.url_slug_has_keyword",
            passed=url_has_slug_kw,
            points_earned=5 if url_has_slug_kw else 0,
            points_max=5,
        ))

        return items

    # === Title Readability ===

    def _check_title_readability(
        self, soup: BeautifulSoup, recommendations: list[str]
    ) -> list[SEOCheckItem]:
        items = []
        title_tag = soup.find("title")
        title = title_tag.string.strip() if title_tag and title_tag.string else ""
        title_lower = title.lower()

        # 1. Number in title (5점)
        has_number = bool(re.search(r"\d", title))
        items.append(SEOCheckItem(
            name="title_readability.has_number",
            passed=has_number,
            points_earned=5 if has_number else 0,
            points_max=5,
        ))
        if not has_number:
            recommendations.append("Title에 숫자를 포함하면 CTR이 향상됩니다 (예: '7가지 방법').")

        # 2. Power words in title (5점)
        title_words = set(re.findall(r"\b\w+\b", title_lower))
        has_power = bool(title_words & _POWER_WORDS)
        items.append(SEOCheckItem(
            name="title_readability.has_power_word",
            passed=has_power,
            points_earned=5 if has_power else 0,
            points_max=5,
        ))

        # 3. Title length (5점) — 50-60자 (Rank Math 권장)
        length_ok = 50 <= len(title) <= 60
        items.append(SEOCheckItem(
            name="title_readability.title_length",
            passed=length_ok,
            points_earned=5 if length_ok else 0,
            points_max=5,
            detail=f"Length: {len(title)} chars (50-60 ideal)",
        ))
        if not length_ok and title:
            if len(title) < 50:
                recommendations.append("Title이 짧습니다. 50자 이상으로 늘려보세요.")
            else:
                recommendations.append("Title이 깁니다. 60자 이하로 줄이세요.")

        return items

    # === Content Readability ===

    def _check_content_readability(
        self, soup: BeautifulSoup, recommendations: list[str]
    ) -> list[SEOCheckItem]:
        items = []

        # 본문 텍스트
        body = soup.find("body") or soup
        for tag in body.find_all(["script", "style", "noscript"]):
            tag.decompose()
        full_text = body.get_text(separator=" ")
        # 단어/문장 카운트
        words = re.findall(r"\S+", full_text)
        sentences = re.split(r"[.!?。!?]", full_text)
        sentences = [s for s in sentences if s.strip()]

        # 1. Content length (5점) — 600+ 단어
        word_count = len(words)
        length_ok = word_count >= 600
        items.append(SEOCheckItem(
            name="content_readability.content_length",
            passed=length_ok,
            points_earned=5 if length_ok else 0,
            points_max=5,
            detail=f"Word count: {word_count} (600+ ideal)",
        ))
        if not length_ok:
            recommendations.append(f"콘텐츠가 짧습니다. 현재 {word_count}단어, 최소 600단어 권장.")

        # 2. Average paragraph length (5점) — 단락 평균 단어 수 <= 150
        paragraphs = body.find_all("p")
        if paragraphs:
            para_word_counts = [len(re.findall(r"\S+", p.get_text())) for p in paragraphs]
            avg_para = sum(para_word_counts) / len(para_word_counts)
            para_ok = avg_para <= 150
        else:
            avg_para = word_count
            para_ok = True
        items.append(SEOCheckItem(
            name="content_readability.paragraph_length",
            passed=para_ok,
            points_earned=5 if para_ok else 0,
            points_max=5,
            detail=f"Avg paragraph: {avg_para:.0f} words (≤150 ideal)",
        ))

        # 3. Images with alt (5점) — 모든 <img>에 alt 속성
        imgs = body.find_all("img")
        imgs_with_alt = sum(1 for img in imgs if img.get("alt", "").strip())
        all_alt_ok = (not imgs) or imgs_with_alt == len(imgs)
        items.append(SEOCheckItem(
            name="content_readability.all_images_have_alt",
            passed=all_alt_ok,
            points_earned=5 if all_alt_ok else 0,
            points_max=5,
            detail=f"Images: {len(imgs)}, with alt: {imgs_with_alt}",
        ))
        if not all_alt_ok:
            recommendations.append(f"이미지 {len(imgs) - imgs_with_alt}개에 alt 텍스트가 없습니다.")

        return items


__all__ = ["RankMathStyleAnalyzer", "SEOResult", "SEOCheckItem"]
