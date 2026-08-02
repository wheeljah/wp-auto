"""Real WordPress REST API 클라이언트 (httpx + Application Password).

W4 범위: skeleton + rate limiter. 실 WP 사이트 세팅 후 사용.

인증: WordPress Application Password
- wp-admin → Users → Profile → Application Passwords → New
- 생성된 24자 토큰 (xxxx xxxx xxxx xxxx xxxx xxxx) 사용
- HTTP Basic Auth: username + application_password
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

import httpx
from loguru import logger

from wp_auto.wp.client import Category, Post


class RateLimiter:
    """토큰 버킷 rate limiter (5분당 100req = 평균 3초당 1req)."""

    def __init__(self, max_per_300s: int = 100) -> None:
        self.max = max_per_300s
        self.interval = 300.0
        self._lock = asyncio.Lock()
        self._timestamps: list[float] = []

    async def acquire(self) -> None:
        async with self._lock:
            now = asyncio.get_event_loop().time()
            # 5분 window에서 max개 이상이면 가장 오래된 것 expire까지 대기
            while len(self._timestamps) >= self.max:
                oldest = self._timestamps[0]
                wait = (oldest + self.interval) - now
                if wait > 0:
                    logger.debug("RateLimit: waiting {:.1f}s", wait)
                    await asyncio.sleep(wait)
                    now = asyncio.get_event_loop().time()
                else:
                    self._timestamps.pop(0)
            self._timestamps.append(now)


class RealWordPressClient:
    """실 WordPress REST API 클라이언트.

    사용법:
        client = RealWordPressClient(
            site_url="https://example.com",
            user="admin",
            app_password="xxxx xxxx xxxx xxxx xxxx xxxx",
        )
        post_id = await client.create_draft(title="...", content="<p>...</p>")

    인증: WordPress Application Password (HTTP Basic Auth)
    """

    def __init__(
        self,
        site_url: str,
        user: str,
        app_password: str,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = f"{site_url.rstrip('/')}/wp-json/wp/v2"
        # WP Application Password는 공백 포함 그대로 사용, HTTP Basic Auth는 그대로
        # httpx의 auth=(user, password) 사용
        self._auth = httpx.BasicAuth(user, app_password)
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            auth=self._auth,
            timeout=timeout,
            headers={"User-Agent": "wp-auto/0.1.0"},
        )
        self._limiter = RateLimiter()
        logger.info(
            "RealWordPressClient initialized: site={}, user={}",
            site_url, user,
        )

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """Rate-limited API 요청."""
        await self._limiter.acquire()
        resp = await self._client.request(method, path, **kwargs)
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    async def list_posts(
        self, status: str = "any", per_page: int = 100
    ) -> list[Post]:
        params: dict = {"per_page": per_page}
        if status != "any":
            params["status"] = status
        data = await self._request("GET", "/posts", params=params)
        return [self._to_post(p) for p in data]

    async def get_post(self, post_id: int) -> Post:
        data = await self._request("GET", f"/posts/{post_id}")
        return self._to_post(data)

    async def create_draft(
        self,
        title: str,
        content: str,
        *,
        slug: str = "",
        excerpt: str = "",
        status: str = "draft",
        meta: dict | None = None,
        categories: list[int] | None = None,
        tags: list[int] | None = None,
    ) -> int:
        payload: dict = {"title": title, "content": content, "status": status}
        if slug:
            payload["slug"] = slug
        if excerpt:
            payload["excerpt"] = excerpt
        if meta:
            payload["meta"] = meta
        if categories:
            payload["categories"] = categories
        if tags:
            payload["tags"] = tags
        data = await self._request("POST", "/posts", json=payload)
        return data["id"]

    async def update_post(self, post_id: int, **fields) -> Post:
        data = await self._request("POST", f"/posts/{post_id}", json=fields)
        return self._to_post(data)

    async def schedule_publish(self, post_id: int, at: datetime) -> Post:
        return await self.update_post(
            post_id,
            status="future",
            date=at.isoformat(),
            date_gmt=at.isoformat(),
        )

    async def publish(self, post_id: int) -> Post:
        return await self.update_post(
            post_id, status="publish", date_gmt=datetime.utcnow().isoformat()
        )

    async def upload_image(
        self, file_path: str, alt_text: str = ""
    ) -> int:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {file_path}")
        await self._limiter.acquire()
        with open(path, "rb") as f:
            resp = await self._client.post(
                "/media",
                files={"file": (path.name, f, "image/jpeg")},
                data={
                    "alt_text": alt_text,
                    "title": path.stem,
                },
            )
        resp.raise_for_status()
        return resp.json()["id"]

    async def list_categories(self) -> list[Category]:
        data = await self._request("GET", "/categories", params={"per_page": 100})
        return [
            Category(id=c["id"], name=c["name"], slug=c["slug"], count=c.get("count", 0))
            for c in data
        ]

    @staticmethod
    def _to_post(data: dict) -> Post:
        return Post(
            id=data["id"],
            title=data.get("title", {}).get("rendered", ""),
            content=data.get("content", {}).get("rendered", ""),
            status=data.get("status", "draft"),
            slug=data.get("slug", ""),
            excerpt=data.get("excerpt", {}).get("rendered", ""),
            author=data.get("author", 0),
            featured_media=data.get("featured_media", 0),
            meta=data.get("meta", {}) or {},
            categories=data.get("categories", []),
            tags=data.get("tags", []),
            url=data.get("link", ""),
        )

    async def close(self) -> None:
        await self._client.aclose()


__all__ = ["RealWordPressClient", "RateLimiter"]
