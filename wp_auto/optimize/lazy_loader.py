"""HTML lazy loading + width/height 자동 주입.

BCP: <img>에 loading="lazy" + 명시적 width/height → CLS 0에 가까움.

사용법:
    from wp_auto.optimize.lazy_loader import inject_lazy_loading
    new_html = inject_lazy_loading(html, exclude_first=True)
"""

from __future__ import annotations

from bs4 import BeautifulSoup
from loguru import logger


def inject_lazy_loading(
    html: str,
    exclude_first: bool = True,
    default_width: int = 1200,
    default_height: int = 675,
    add_dimensions: bool = True,
) -> str:
    """HTML의 <img> 태그에 lazy loading + width/height 주입.

    Args:
        html: HTML 문자열
        exclude_first: 첫 번째 <img>는 LCP일 가능성 → lazy 제외, fetchpriority="high" 추가
        default_width: img에 width 없을 때 기본값
        default_height: img에 height 없을 때 기본값
        add_dimensions: width/height 속성 자동 추가 여부

    Returns:
        변환된 HTML 문자열
    """
    soup = BeautifulSoup(html, "lxml")
    imgs = soup.find_all("img")
    if not imgs:
        return html

    for i, img in enumerate(imgs):
        # LCP 이미지: 첫 번째는 lazy 제외
        if i == 0 and exclude_first:
            img["loading"] = "eager"
            img["fetchpriority"] = "high"
        else:
            if img.get("loading") != "eager":
                img["loading"] = "lazy"

        # width/height 추가
        if add_dimensions:
            if not img.get("width"):
                img["width"] = str(default_width)
            if not img.get("height"):
                img["height"] = str(default_height)

    logger.debug("inject_lazy_loading: {} images processed", len(imgs))
    return str(soup)


def strip_dimensions(html: str) -> str:
    """img의 width/height 속성 제거 (반대 작업, 디버깅용)."""
    soup = BeautifulSoup(html, "lxml")
    for img in soup.find_all("img"):
        img.attrs.pop("width", None)
        img.attrs.pop("height", None)
        img.attrs.pop("loading", None)
        img.attrs.pop("fetchpriority", None)
    return str(soup)


__all__ = ["inject_lazy_loading", "strip_dimensions"]
