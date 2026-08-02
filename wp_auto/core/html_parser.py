"""HTML → ContentMetrics 자동 변환 파서.

목적: WP 글 HTML 한 개를 받아서 점수화에 필요한 메트릭을 자동으로 채움.
휴리스틱 기반 — 100% 정확하지 않지만, 단독으로 80+ 점 글/40- 점 글을 구분할 수 있는 수준.

자동 채움 항목:
- word_count (본문 글자 수, 공백/태그 제외)
- title (<title> 또는 첫 <h1>)
- h2_count
- internal_links, external_authority_links (<a> 태그)
- meta_description_length (<meta name="description">)
- images_optimized, lazy_load_applied (<img> 비율)
- has_comparison_table (<table>)
- has_faq (<details> 또는 FAQ 헤딩)
- has_step_by_step_guide (<ol> + 단계/Step 키워드)
- has_data_or_case (<blockquote> 또는 수치 패턴)
- has_original_analysis (긴 본문 + 인용)
- author_bio_present, author_experience_mentioned (휴리스틱)
- sources_cited (<cite> + 외부 링크 수)
- update_date_present (updated/수정일/2026-XX-XX)
- unnecessary_js_css (외부 script/link 스타일시트 5+ 개)
- estimated_lcp_ok (preload 태그 존재)
- mobile_friendly (viewport 메타)

D2 범위 — 정확도보다 "동작 + 단위 테스트 통과" 우선.
D3에서 SEO 분석기와 통합, W3에서 CWV 측정기와 통합.
"""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from wp_auto.core.content_score import ContentMetrics


# 한국어/영어 1인칭 + 직접 경험 패턴
_EXPERIENCE_PATTERNS = [
    r"제가\s",  # "제가 직접"
    r"직접\s",  # "직접 해본"
    r"저희\s",  # "저희 팀이"
    r"본인\s",  # "본인이"
    r"\bI\s",  # "I tested"
    r"\bwe\s",  # "we tried"
    r"\bmy\s",  # "my experience"
]

# 업데이트 날짜 패턴
_UPDATE_DATE_PATTERNS = [
    r"updated",
    r"수정일",
    r"최종\s*수정",
    r"\d{4}-\d{2}-\d{2}",  # 2026-08-02
    r"\d{4}\.\s?\d{1,2}\.\s?\d{1,2}\.",  # 2026. 8. 2.
]

# 한국어/영어 단계/스텝 패턴
_STEP_PATTERNS = [
    r"단계\s*\d",
    r"step\s*\d",
    r"^\s*\d+\.\s",  # "1. xxx"
    r"^\s*①|②|③",
]

# 수치/통계 패턴 (간단)
_DATA_PATTERNS = [
    r"\d+%",  # 50%
    r"\d+\s*배",  # 3배
    r"\$\d+",  # $100
    r"\d{1,3},\d{3}",  # 1,000
    r"통계",
    r"연구",
    r"실험",
    r"research",
    r"study",
    r"benchmark",
]


def _count_chars(html: str) -> int:
    """본문 텍스트의 글자 수 (태그/script/style 제외, 공백 압축).

    HTML 문자열을 직접 받아서 새 soup를 파싱하므로, 호출자의 soup에 영향 없음
    (decompose()가 원본 soup를 변형시키는 문제 회피).

    한국어: 1글자 = 1자. 영어: 단어 단위가 아닌 character count.
    원본 점수화 로직의 word_count와 명명 일치 (자료의 word_count는 사실상 char count).
    """
    soup = BeautifulSoup(html, "lxml")
    # script/style/head 제거
    for tag in soup(["script", "style", "head", "meta", "link", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    # 공백 압축
    text = re.sub(r"\s+", " ", text).strip()
    return len(text)


def _get_title(soup: BeautifulSoup) -> str:
    """<title> 또는 첫 <h1>."""
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        return title_tag.string.strip()
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return ""


def _count_internal_external_links(soup: BeautifulSoup) -> tuple[int, int]:
    """내부/외부 링크 수. 같은 도메인 비교용 base_url은 Day 1 범위 밖 → 단순 분류.

    휴리스틱:
    - / 로 시작 → 내부 (상대 경로)
    - # 으로 시작 → 내부 (앵커)
    - http(s):// → 외부
    - / 로 시작 안 함 → 내부 (mail 같은 예외 케이스 무시)
    """
    internal = 0
    external = 0
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith(("http://", "https://", "//")):
            external += 1
        else:
            # /path, #anchor, mailto 등은 내부로 카운트
            internal += 1
    return internal, external


def _get_meta_description_length(soup: BeautifulSoup) -> int:
    """<meta name='description' content='...'>의 content 길이."""
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return len(meta["content"].strip())
    return 0


def _check_images(soup: BeautifulSoup) -> tuple[bool, bool]:
    """이미지 최적화 + lazy 적용 여부.

    Returns: (images_optimized, lazy_load_applied)
    - images_optimized: <img>의 50%+ 가 .webp/.avif src 사용
    - lazy_load_applied: <img>의 50%+ 가 loading='lazy' 속성 보유
    """
    imgs = soup.find_all("img")
    if not imgs:
        return True, True  # 이미지가 없으면 최적화로 간주 (False가 아닌 True)

    webp_or_avif = 0
    lazy = 0
    for img in imgs:
        src = img.get("src", "")
        loading = img.get("loading", "")
        if ".webp" in src.lower() or ".avif" in src.lower():
            webp_or_avif += 1
        if loading == "lazy":
            lazy += 1

    n = len(imgs)
    return webp_or_avif / n >= 0.5, lazy / n >= 0.5


def _has_table(soup: BeautifulSoup) -> bool:
    """<table> 존재 여부 (비교표)."""
    return bool(soup.find("table"))


def _has_faq(soup: BeautifulSoup) -> bool:
    """FAQ 존재 휴리스틱: <details> 또는 FAQ 헤딩."""
    if soup.find("details"):
        return True
    # h2/h3 중 "FAQ", "자주 묻는" 텍스트
    for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
        text = tag.get_text().lower()
        if "faq" in text or "자주 묻는" in text or "q&a" in text or "qna" in text:
            return True
    return False


def _has_step_by_step(soup: BeautifulSoup) -> bool:
    """단계별 가이드 휴리스틱: <ol> + 단계/Step 키워드 또는 <ol>의 직속 <li> 3+ 개."""
    ols = soup.find_all("ol")
    if not ols:
        return False
    # <ol> 본문에 단계/step/Step/①/1. 패턴
    full_text = " ".join(ol.get_text() for ol in ols)
    for pattern in _STEP_PATTERNS:
        if re.search(pattern, full_text, re.IGNORECASE | re.MULTILINE):
            return True
    # 또는 <ol> 안에 <li> 3+ 개
    for ol in ols:
        if len(ol.find_all("li", recursive=False)) >= 3:
            return True
    return False


def _has_data_or_case(soup: BeautifulSoup) -> bool:
    """데이터/사례 휴리스틱: <blockquote> 또는 수치/통계 패턴 3+ 개 매칭."""
    if soup.find("blockquote"):
        return True
    full_text = soup.get_text()
    matches = 0
    for pattern in _DATA_PATTERNS:
        matches += len(re.findall(pattern, full_text, re.IGNORECASE))
    return matches >= 3


def _has_original_analysis(soup: BeautifulSoup, html: str) -> bool:
    """원본 분석 휴리스틱: 본문 1500자+ AND (blockquote OR 인용 패턴 OR 1인칭).

    html 인자를 받아 _count_chars()에 전달 (soup 변형 회피).
    """
    text = _count_chars(html)
    if text < 1500:
        return False
    if soup.find("blockquote"):
        return True
    if soup.find(["q", "cite"]):
        return True
    for pattern in _EXPERIENCE_PATTERNS:
        if re.search(pattern, soup.get_text(), re.IGNORECASE):
            return True
    return False


def _has_author_bio(soup: BeautifulSoup) -> bool:
    """저자 박스 휴리스틱: 'author', 'by', '작성자' class/id 또는 텍스트."""
    # class 또는 id에 author/bio
    for tag in soup.find_all(True):
        cls = " ".join(tag.get("class", []) or [])
        tid = tag.get("id", "") or ""
        if any(kw in cls.lower() for kw in ["author", "bio", "byline", "작성자", "저자"]):
            return True
        if any(kw in tid.lower() for kw in ["author", "bio", "byline"]):
            return True
    # footer/header 텍스트에 "by xxx" 또는 "작성자: xxx"
    text = soup.get_text()
    if re.search(r"\bby\s+[A-Z][a-z]+", text):
        return True
    if re.search(r"작성자\s*[:：]", text):
        return True
    if re.search(r"저자\s*[:：]", text):
        return True
    return False


def _has_author_experience(soup: BeautifulSoup) -> bool:
    """1인칭/직접 경험 패턴 매칭."""
    text = soup.get_text()
    for pattern in _EXPERIENCE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def _count_sources(soup: BeautifulSoup) -> int:
    """출처 개수 휴리스틱: <cite> 개수 + 외부 링크 개수 (단순 합산).

    Rank Math는 출처 링크를 권위 사이트로 카운트하지만 Day 2에서는 단순 외부 링크 = 출처.
    """
    cites = len(soup.find_all("cite"))
    _, external = _count_internal_external_links(soup)
    return cites + external


def _has_update_date(soup: BeautifulSoup) -> bool:
    """업데이트 날짜 패턴 매칭."""
    text = soup.get_text()
    for pattern in _UPDATE_DATE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    # time 태그
    if soup.find("time"):
        return True
    return False


def _has_unnecessary_js_css(soup: BeautifulSoup) -> bool:
    """불필요 JS/CSS 휴리스틱: 외부 <script src> + <link rel=stylesheet> 가 5+ 개.

    외부 의존이 많으면 (분석, 광고, 위젯 등) True (문제 있음).
    """
    external_scripts = 0
    for s in soup.find_all("script", src=True):
        src = s.get("src", "")
        if src.startswith(("http://", "https://", "//")):
            external_scripts += 1
    stylesheets = len(soup.find_all("link", rel="stylesheet"))
    return (external_scripts + stylesheets) >= 5


def _is_lcp_ok(soup: BeautifulSoup) -> bool:
    """LCP < 2.5s 가능 휴리스틱: <link rel=preload as=image> 또는 큰 이미지 1개 + fetchpriority."""
    if soup.find("link", attrs={"rel": "preload", "as": "image"}):
        return True
    for img in soup.find_all("img"):
        if img.get("fetchpriority") == "high":
            return True
    return False


def _is_mobile_friendly(soup: BeautifulSoup) -> bool:
    """<meta name='viewport'> 존재 여부."""
    return bool(soup.find("meta", attrs={"name": "viewport"}))


def parse_html_to_metrics(
    html: str,
    focus_keyword: Optional[str] = None,
) -> ContentMetrics:
    """HTML 문자열 → ContentMetrics 자동 채움.

    Args:
        html: HTML 문자열 (파일 또는 fetch 결과)
        focus_keyword: 메인 키워드 (선택). 제공되면 title 포함 여부 자동 체크.

    Returns:
        ContentMetrics (모든 필드 자동 채워짐)
    """
    soup = BeautifulSoup(html, "lxml")

    title = _get_title(soup)
    # word_count는 html 직접 전달 (soup 변형 회피)
    word_count = _count_chars(html)
    h2_count = len(soup.find_all("h2"))
    internal_links, external_links = _count_internal_external_links(soup)
    meta_description_length = _get_meta_description_length(soup)
    images_optimized, lazy_load_applied = _check_images(soup)

    main_keyword_in_title = False
    if focus_keyword:
        main_keyword_in_title = focus_keyword.lower() in title.lower()

    return ContentMetrics(
        title=title,
        word_count=word_count,
        has_original_analysis=_has_original_analysis(soup, html),
        has_step_by_step_guide=_has_step_by_step(soup),
        has_data_or_case=_has_data_or_case(soup),
        has_comparison_table=_has_table(soup),
        has_faq=_has_faq(soup),
        author_experience_mentioned=_has_author_experience(soup),
        author_bio_present=_has_author_bio(soup),
        sources_cited=_count_sources(soup),
        update_date_present=_has_update_date(soup),
        main_keyword_in_title=main_keyword_in_title,
        h2_count=h2_count,
        internal_links=internal_links,
        external_authority_links=external_links,
        meta_description_length=meta_description_length,
        images_optimized=images_optimized,
        lazy_load_applied=lazy_load_applied,
        unnecessary_js_css=_has_unnecessary_js_css(soup),
        estimated_lcp_ok=_is_lcp_ok(soup),
        mobile_friendly=_is_mobile_friendly(soup),
    )


__all__ = ["parse_html_to_metrics"]
