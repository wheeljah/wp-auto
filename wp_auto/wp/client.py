"""WordPress REST API 클라이언트 인터페이스.

도구 우선 빌드 패턴: 실 WP 사이트 세팅 전이라도 단독 실행 가능하도록
Protocol + MockWordPressClient + RealWordPressClient 분리.

사용법:
    from wp_auto.wp.client import WordPressClient, Post
    from wp_auto.wp.factory import get_wp_client

    client = get_wp_client()  # 환경변수에 따라 Mock 또는 Real
    post_id = await client.create_draft(title="...", content="<p>...</p>")
    post = await client.get_post(post_id)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass
class Post:
    """WordPress 글 (REST API 응답의 부분 집합)."""

    id: int
    title: str
    content: str
    status: str = "draft"  # draft | publish | future | private
    slug: str = ""
    excerpt: str = ""
    author: int = 0
    featured_media: int = 0
    meta: dict = field(default_factory=dict)
    categories: list[int] = field(default_factory=list)
    tags: list[int] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    published_at: datetime | None = None
    url: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": {"rendered": self.title},
            "content": {"rendered": self.content},
            "status": self.status,
            "slug": self.slug,
            "excerpt": {"rendered": self.excerpt},
            "author": self.author,
            "featured_media": self.featured_media,
            "meta": self.meta,
            "categories": self.categories,
            "tags": self.tags,
            "date": self.created_at.isoformat() if self.created_at else None,
            "date_gmt": self.published_at.isoformat() if self.published_at else None,
            "link": self.url,
        }


@dataclass
class Category:
    """WordPress 카테고리."""

    id: int
    name: str
    slug: str
    count: int = 0


@dataclass
class Media:
    """WordPress 미디어 (업로드된 이미지 등)."""

    id: int
    source_url: str
    alt_text: str = ""
    media_type: str = "image"
    title: str = ""


class WordPressClient(Protocol):
    """모든 WP 클라이언트가 구현해야 하는 인터페이스.

    Note: Protocol이므로 isinstance 체크는 불가능하지만, 구조적 타입 호환 OK.
    """

    async def list_posts(
        self, status: str = "any", per_page: int = 100
    ) -> list[Post]:
        """글 목록 조회."""
        ...

    async def get_post(self, post_id: int) -> Post:
        """글 단건 조회."""
        ...

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
        """초안 생성 → post_id 반환."""
        ...

    async def update_post(self, post_id: int, **fields) -> Post:
        """글 수정."""
        ...

    async def schedule_publish(
        self, post_id: int, at: datetime
    ) -> Post:
        """예약 발행 (status='future')."""
        ...

    async def publish(self, post_id: int) -> Post:
        """즉시 발행 (status='publish')."""
        ...

    async def upload_image(
        self, file_path: str, alt_text: str = ""
    ) -> int:
        """이미지 업로드 → media_id 반환."""
        ...

    async def list_categories(self) -> list[Category]:
        """카테고리 목록."""
        ...


__all__ = ["WordPressClient", "Post", "Category", "Media"]
