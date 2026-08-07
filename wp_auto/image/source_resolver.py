"""ImageSourceResolver — Pexels + Wikimedia + NASA 통합 검색.

순서 (KEY 있으면 Pexels 우선, 없으면 Wikimedia → NASA):
1. Pexels (KEY 필요, 가장 다양한 사진, 200/hour rate limit)
2. Wikimedia Commons (KEY 불필요, CC0/CC BY/CC BY-SA만)
3. NASA Images (KEY 불필요, public domain, 우주/지구 위주)

각 source의 응답 파싱 + 라이선스 검증 + attribution 생성.
"""
from __future__ import annotations

import re
from typing import Iterable

import httpx
from loguru import logger

from .models import ImageResult, LicenseKind, SourceName


# === 각 source의 endpoint ===
PEXELS_SEARCH = "https://api.pexels.com/v1/search"
WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"
NASA_IMAGES_API = "https://images-api.nasa.gov/search"


class ImageSourceResolver:
    """Pexels + Wikimedia + NASA 통합 이미지 검색.

    사용법:
        resolver = ImageSourceResolver(pexels_api_key="...")
        images = resolver.search("OpenAI GPT-6", max_results=2)
    """

    def __init__(
        self,
        pexels_api_key: str | None = None,
        unsplash_api_key: str | None = None,
        pixabay_api_key: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.pexels_api_key = pexels_api_key
        self.unsplash_api_key = unsplash_api_key
        self.pixabay_api_key = pixabay_api_key
        self.timeout = timeout
        # Wikimedia API는 User-Agent 필수 (1차 출처: https://meta.wikimedia.org/wiki/User-Agent_policy)
        # 정책: "specific tool/version + contact-info" 형식. generic browser UA는 차단.
        headers = {
            "User-Agent": "wp-auto/1.0 (https://github.com/wheeljah/wp-auto; wheeljah@gmail.com) Python/3.14",
            "Accept": "application/json",
        }
        self._client = httpx.Client(timeout=timeout, follow_redirects=True, headers=headers)
        logger.info(
            "ImageSourceResolver: pexels={}, unsplash={}, pixabay={}",
            bool(pexels_api_key),
            bool(unsplash_api_key),
            bool(pixabay_api_key),
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def search(self, keyword: str, max_results: int = 3) -> list[ImageResult]:
        """키워드로 여러 source 순서대로 시도. 최대 max_results."""
        results: list[ImageResult] = []
        sources: list[tuple[str, callable]] = []
        if self.pexels_api_key:
            sources.append(("pexels", self._search_pexels))
        sources.append(("wikimedia", self._search_wikimedia))
        sources.append(("nasa", self._search_nasa))
        if self.unsplash_api_key:
            sources.append(("unsplash", self._search_unsplash))
        if self.pixabay_api_key:
            sources.append(("pixabay", self._search_pixabay))

        for name, fn in sources:
            try:
                got = fn(keyword, max_results - len(results))
                results.extend(got)
                logger.info("{} search returned {} images", name, len(got))
            except Exception as e:
                logger.warning("{} search failed: {}", name, e)
            if len(results) >= max_results:
                break

        return results[:max_results]

    # ==================== Pexels ====================
    def _search_pexels(self, keyword: str, max_results: int) -> list[ImageResult]:
        if not self.pexels_api_key:
            return []
        if max_results <= 0:
            return []
        headers = {"Authorization": self.pexels_api_key}
        params = {"query": keyword, "per_page": max_results, "page": 1}
        r = self._client.get(PEXELS_SEARCH, headers=headers, params=params)
        r.raise_for_status()
        data = r.json()
        results: list[ImageResult] = []
        for photo in data.get("photos", []):
            src = photo.get("src", {})
            # large2x 우선 (고해상도), fallback to large
            img_url = src.get("large2x") or src.get("large") or src.get("original") or ""
            photographer = photo.get("photographer", "Unknown")
            photo_url = photo.get("url", "")
            alt = photo.get("alt", "") or keyword
            results.append(ImageResult(
                source="pexels",
                license="Pexels",
                photographer=photographer,
                source_url=photo_url,
                image_url=img_url,
                width=photo.get("width", 0),
                height=photo.get("height", 0),
                alt=alt,
                attribution=f"by {photographer} via Pexels",
            ))
        return results

    # ==================== Wikimedia Commons ====================
    def _search_wikimedia(self, keyword: str, max_results: int) -> list[ImageResult]:
        if max_results <= 0:
            return []
        params = {
            "action": "query",
            "format": "json",
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|size",
            "generator": "search",
            "gsrsearch": f"{keyword} filetype:bitmap",
            "gsrnamespace": "6",  # File namespace
            "gsrlimit": str(max(max_results * 2, 10)),  # 라이선스 필터 후 부족 대비
        }
        r = self._client.get(WIKIMEDIA_API, params=params)
        r.raise_for_status()
        data = r.json()
        results: list[ImageResult] = []
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            if len(results) >= max_results:
                break
            for img_info in page.get("imageinfo", []):
                if len(results) >= max_results:
                    break
                ext = img_info.get("extmetadata", {})
                license_short = ext.get("LicenseShortName", {}).get("value", "")
                # 라이선스 검증: CC0/PD/CC BY/CC BY-SA만 통과
                license = self._wikimedia_license(license_short)
                if license is None:
                    continue
                # size 확인 (너무 작은 거 skip)
                width = img_info.get("width", 0)
                height = img_info.get("height", 0)
                if width > 0 and width < 400:
                    continue
                artist = self._clean_artist(ext.get("Artist", {}).get("value", "Unknown"))
                results.append(ImageResult(
                    source="wikimedia",
                    license=license,
                    photographer=artist,
                    source_url=img_info.get("descriptionurl", ""),
                    image_url=img_info.get("url", ""),
                    width=width,
                    height=height,
                    alt=ext.get("ImageDescription", {}).get("value", "")[:200] or keyword,
                    attribution=f"by {artist} via Wikimedia Commons ({license})",
                ))
        return results

    @staticmethod
    def _wikimedia_license(license_short: str) -> LicenseKind | None:
        """Wikimedia 라이선스 단축명 → wp-auto License. 비자유 라이선스 skip.

        우선순위 (정확한 매칭 우선):
        1. CC0 / Public Domain
        2. CC BY-SA 4.0
        3. CC BY 4.0
        4. CC BY-NC-SA / CC BY-NC / GFDL → None (상업용 불가)
        """
        s = license_short.lower()
        # 1) CC0 / Public Domain
        if "cc0" in s:
            return "CC0"
        if "public domain" in s or s == "pd" or s.startswith("pd-"):
            return "Public Domain"
        # 2) Non-Commercial variants 먼저 reject (BY-NC, BY-NC-SA, BY-ND-NC 등)
        if "cc by-nc" in s or "cc by-nd-nc" in s:
            return None
        # 3) CC BY-SA (BY-SA-NC는 CC BY-SA-NC = NC variant → reject)
        if "cc by-sa" in s:
            if "nc" in s:
                return None
            return "CC-BY-SA"
        # 4) CC BY (BY-ND는 NC 아니면 OK, BY만 가장 자유)
        if "cc by" in s:
            if "nd" in s:
                # CC BY-ND: derivatives 금지 → 매체 사용에 제약. 일단 skip (안전).
                return None
            return "CC-BY"
        # 5) GFDL, fair use 등 기타 → None
        return None

    @staticmethod
    def _clean_artist(html: str) -> str:
        """Wikimedia Artist 필드는 HTML 형식. plain text로."""
        # <a> 태그 제거하고 텍스트만
        text = re.sub(r'<[^>]+>', '', html).strip()
        return text or "Unknown"

    # ==================== NASA Images ====================
    def _search_nasa(self, keyword: str, max_results: int) -> list[ImageResult]:
        if max_results <= 0:
            return []
        params = {"q": keyword, "media_type": "image"}
        r = self._client.get(NASA_IMAGES_API, params=params)
        r.raise_for_status()
        data = r.json()
        results: list[ImageResult] = []
        items = data.get("collection", {}).get("items", [])
        for item in items:
            if len(results) >= max_results:
                break
            data_list = item.get("data", [{}])[0]
            links = item.get("links", [{}])[0]
            nasa_id = data_list.get("nasa_id", "")
            title = data_list.get("title", "Untitled")
            if not nasa_id:
                continue
            # NASA image asset URL 패턴
            # https://images-assets.nasa.gov/image/{nasa_id}/{nasa_id}~orig.jpg
            image_url = f"https://images-assets.nasa.gov/image/{nasa_id}/{nasa_id}~medium.jpg"
            results.append(ImageResult(
                source="nasa",
                license="PD-NASA",
                photographer="NASA",
                source_url=links.get("href", "") or f"https://images.nasa.gov/details/{nasa_id}",
                image_url=image_url,
                width=0,
                height=0,
                alt=title[:200],
                attribution=f"by NASA (Public Domain) — {title[:80]}",
            ))
        return results

    # ==================== Unsplash (placeholder) ====================
    def _search_unsplash(self, keyword: str, max_results: int) -> list[ImageResult]:
        """Unsplash API 호출 (KEY 있을 때). 추후 구현."""
        logger.debug("Unsplash search not yet implemented")
        return []

    # ==================== Pixabay (placeholder) ====================
    def _search_pixabay(self, keyword: str, max_results: int) -> list[ImageResult]:
        """Pixabay API 호출 (KEY 있을 때). 추후 구현."""
        logger.debug("Pixabay search not yet implemented")
        return []
