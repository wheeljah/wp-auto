"""외부 링크 검증기 — HEAD request로 200/3xx만 통과.

LLM이 생성한 chunk body에 의심스러운/가짜 URL이 포함될 수 있음.
이 모듈은 HTML에서 외부 링크를 추출 → HTTP HEAD/GET으로 검증 →
broken link는 텍스트로 변환하거나 제거.

사용법:
    from wp_auto.ai.link_verifier import LinkVerifier

    verifier = LinkVerifier(timeout=5.0, max_concurrent=5)
    cleaned_html, removed = verifier.verify_and_clean_html(html)
    print(f"Removed {len(removed)} broken links")
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Iterable

import httpx
from loguru import logger

# HTML anchor pattern
ANCHOR_PATTERN = re.compile(
    r'<a\s+([^>]*?)href=(["\'])([^"\']+?)\2([^>]*)>(.*?)</a>',
    flags=re.IGNORECASE | re.DOTALL,
)

# 알려진 가짜/플레이스홀더 도메인 (무조건 broken 처리)
KNOWN_PLACEHOLDER_DOMAINS = (
    "example.com",
    "example.org",
    "example.net",
    "yourdomain.com",
    "mysite.com",
    "placeholder.com",
    "test.com",
    "localhost",
    "127.0.0.1",
)


@dataclass
class LinkCheckResult:
    """단일 URL 검증 결과."""

    url: str
    anchor_text: str
    is_valid: bool
    status_code: int = 0
    error: str = ""


class LinkVerifier:
    """외부 링크 일괄 검증 (HEAD → fallback GET)."""

    def __init__(
        self,
        timeout: float = 5.0,
        max_concurrent: int = 5,
        user_agent: str = "WP-Auto LinkVerifier/1.0 (+https://github.com/wheeljah/wp-auto)",
    ) -> None:
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.user_agent = user_agent

    def _is_placeholder(self, url: str) -> bool:
        """예약된 placeholder 도메인 → 무조건 broken."""
        lower = url.lower()
        return any(d in lower for d in KNOWN_PLACEHOLDER_DOMAINS)

    async def _check_url(self, client: httpx.AsyncClient, url: str) -> LinkCheckResult:
        """단일 URL HEAD 시도. 실패 시 GET with stream."""
        if self._is_placeholder(url):
            return LinkCheckResult(
                url=url, anchor_text="", is_valid=False, error="placeholder domain"
            )
        # 먼저 HEAD 시도
        try:
            r = await client.head(url, timeout=self.timeout, follow_redirects=True)
            if r.status_code < 400:
                return LinkCheckResult(url=url, anchor_text="", is_valid=True, status_code=r.status_code)
        except httpx.TimeoutException:
            return LinkCheckResult(url=url, anchor_text="", is_valid=False, error="timeout")
        except Exception as e:
            # HEAD 실패는 흔함 (일부 서버 비허용) → GET으로 fallback
            logger.debug("HEAD failed for {}, trying GET: {}", url, e)
        # HEAD 실패 또는 4xx → GET with stream
        try:
            async with client.stream("GET", url, timeout=self.timeout, follow_redirects=True) as r:
                if r.status_code < 400:
                    return LinkCheckResult(
                        url=url, anchor_text="", is_valid=True, status_code=r.status_code
                    )
                return LinkCheckResult(
                    url=url, anchor_text="", is_valid=False, status_code=r.status_code, error="non-2xx"
                )
        except Exception as e:
            return LinkCheckResult(url=url, anchor_text="", is_valid=False, error=str(e)[:100])

    async def _check_all(self, urls: list[str]) -> dict[str, LinkCheckResult]:
        """여러 URL을 동시 검증 (semaphore로 동시성 제한)."""
        sem = asyncio.Semaphore(self.max_concurrent)
        results: dict[str, LinkCheckResult] = {}

        async def _one(client: httpx.AsyncClient, url: str) -> None:
            async with sem:
                results[url] = await self._check_url(client, url)

        async with httpx.AsyncClient(
            headers={"User-Agent": self.user_agent}, follow_redirects=True
        ) as client:
            await asyncio.gather(*[_one(client, u) for u in urls])
        return results

    def check_urls(self, urls: Iterable[str]) -> dict[str, LinkCheckResult]:
        """동기 API — async 일괄 검증 후 결과 반환."""
        url_list = list(set(urls))
        if not url_list:
            return {}
        return asyncio.run(self._check_all(url_list))

    def verify_and_clean_html(self, html: str) -> tuple[str, list[LinkCheckResult]]:
        """HTML에서 외부 링크 추출 → 검증 → broken link는 텍스트로 변환.

        Args:
            html: 원본 HTML

        Returns:
            (cleaned_html, removed_results)
            - cleaned_html: broken link가 anchor text로 변환된 HTML
            - removed_results: 제거된 링크의 LinkCheckResult 리스트
        """
        # 1) 모든 anchor 추출
        anchors: list[tuple[str, str, str, str]] = []  # (full_match, prefix, url, body)
        for m in ANCHOR_PATTERN.finditer(html):
            full = m.group(0)
            url = m.group(3)
            # 내부 링크 (http로 시작 안 함) → 검증 스킵
            if not url.startswith(("http://", "https://")):
                continue
            anchors.append((full, m.group(1) or "", url, m.group(4) or ""))
        if not anchors:
            return html, []
        # 2) URL 일괄 검증
        urls = [a[2] for a in anchors]
        results = self.check_urls(urls)
        # 3) broken link 치환
        removed: list[LinkCheckResult] = []
        cleaned = html
        for full, prefix, url, suffix in anchors:
            r = results.get(url)
            if r is None or not r.is_valid:
                # anchor text만 남김
                m = re.match(r"<a\s+[^>]*>(.*?)</a>", full, flags=re.DOTALL)
                if m:
                    cleaned = cleaned.replace(full, m.group(1))
                if r is not None:
                    removed.append(r)
                else:
                    removed.append(LinkCheckResult(url=url, anchor_text="", is_valid=False, error="not checked"))
                logger.warning("Removed broken link: {} (status={}, error={})", url, r.status_code if r else "?", r.error if r else "n/a")
        return cleaned, removed


__all__ = [
    "LinkVerifier",
    "LinkCheckResult",
    "KNOWN_PLACEHOLDER_DOMAINS",
]
