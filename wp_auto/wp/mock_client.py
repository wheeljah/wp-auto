"""Mock WordPress 클라이언트 (in-memory + SQLite 옵션).

도구 우선 빌드: 실 WP 사이트 없이도 전체 흐름 검증 가능.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from loguru import logger

from wp_auto.wp.client import Category, Media, Post


class MockWordPressClient:
    """인메모리 dict 기반 mock 클라이언트.

    옵션: db_path 지정 시 SQLite로 영속화.

    사용법:
        client = MockWordPressClient()  # in-memory
        # 또는
        client = MockWordPressClient(db_path=Path("./data/wp.db"))  # SQLite
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._posts: dict[int, Post] = {}
        self._media: dict[int, Media] = {}
        self._categories: dict[int, Category] = {
            1: Category(id=1, name="미분류", slug="uncategorized", count=0)
        }
        self._next_post_id = 1
        self._next_media_id = 1
        self._next_cat_id = 2
        self._db: sqlite3.Connection | None = None
        self._log_prefix = "[MOCK-WP]"

        if db_path:
            self._db = sqlite3.connect(str(db_path), check_same_thread=False)
            self._db.row_factory = sqlite3.Row
            self._init_db()
            self._load_from_db()
            logger.info("{} MockWordPressClient with SQLite: {}", self._log_prefix, db_path)
        else:
            logger.info("{} MockWordPressClient (in-memory)", self._log_prefix)

    def _init_db(self) -> None:
        """SQLite 테이블 생성."""
        assert self._db is not None
        cur = self._db.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT NOT NULL,
                slug TEXT,
                excerpt TEXT,
                author INTEGER DEFAULT 0,
                featured_media INTEGER DEFAULT 0,
                meta TEXT,
                categories TEXT,
                tags TEXT,
                created_at TEXT,
                updated_at TEXT,
                published_at TEXT,
                url TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS media (
                id INTEGER PRIMARY KEY,
                source_url TEXT NOT NULL,
                alt_text TEXT DEFAULT '',
                media_type TEXT DEFAULT 'image',
                title TEXT DEFAULT ''
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                slug TEXT NOT NULL,
                count INTEGER DEFAULT 0
            )
        """)
        self._db.commit()

    def _load_from_db(self) -> None:
        """DB에서 인메모리 캐시로 로드."""
        assert self._db is not None
        cur = self._db.cursor()
        for row in cur.execute("SELECT * FROM posts"):
            self._posts[row["id"]] = Post(
                id=row["id"],
                title=row["title"],
                content=row["content"],
                status=row["status"],
                slug=row["slug"] or "",
                excerpt=row["excerpt"] or "",
                author=row["author"] or 0,
                featured_media=row["featured_media"] or 0,
                meta=json.loads(row["meta"]) if row["meta"] else {},
                categories=json.loads(row["categories"]) if row["categories"] else [],
                tags=json.loads(row["tags"]) if row["tags"] else [],
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
                updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
                published_at=datetime.fromisoformat(row["published_at"]) if row["published_at"] else None,
                url=row["url"] or "",
            )
            self._next_post_id = max(self._next_post_id, row["id"] + 1)
        for row in cur.execute("SELECT * FROM media"):
            self._media[row["id"]] = Media(
                id=row["id"],
                source_url=row["source_url"],
                alt_text=row["alt_text"] or "",
                media_type=row["media_type"] or "image",
                title=row["title"] or "",
            )
            self._next_media_id = max(self._next_media_id, row["id"] + 1)
        for row in cur.execute("SELECT * FROM categories"):
            self._categories[row["id"]] = Category(
                id=row["id"],
                name=row["name"],
                slug=row["slug"],
                count=row["count"] or 0,
            )
            self._next_cat_id = max(self._next_cat_id, row["id"] + 1)

    def _persist_post(self, post: Post) -> None:
        """SQLite에 post 저장."""
        if not self._db:
            return
        cur = self._db.cursor()
        cur.execute(
            """
            INSERT OR REPLACE INTO posts
            (id, title, content, status, slug, excerpt, author, featured_media, meta, categories, tags, created_at, updated_at, published_at, url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                post.id,
                post.title,
                post.content,
                post.status,
                post.slug,
                post.excerpt,
                post.author,
                post.featured_media,
                json.dumps(post.meta, ensure_ascii=False),
                json.dumps(post.categories),
                json.dumps(post.tags),
                post.created_at.isoformat() if post.created_at else None,
                post.updated_at.isoformat() if post.updated_at else None,
                post.published_at.isoformat() if post.published_at else None,
                post.url,
            ),
        )
        self._db.commit()

    def _persist_media(self, media: Media) -> None:
        if not self._db:
            return
        cur = self._db.cursor()
        cur.execute(
            """
            INSERT OR REPLACE INTO media (id, source_url, alt_text, media_type, title)
            VALUES (?, ?, ?, ?, ?)
            """,
            (media.id, media.source_url, media.alt_text, media.media_type, media.title),
        )
        self._db.commit()

    async def list_posts(
        self, status: str = "any", per_page: int = 100
    ) -> list[Post]:
        posts = list(self._posts.values())
        if status != "any":
            posts = [p for p in posts if p.status == status]
        # 최신 순
        posts.sort(key=lambda p: p.created_at or datetime.min, reverse=True)
        return posts[:per_page]

    async def get_post(self, post_id: int) -> Post:
        if post_id not in self._posts:
            raise KeyError(f"Post {post_id} not found")
        return self._posts[post_id]

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
        post_id = self._next_post_id
        self._next_post_id += 1
        now = datetime.now()
        post = Post(
            id=post_id,
            title=title,
            content=content,
            status=status,
            slug=slug or f"post-{post_id}",
            excerpt=excerpt,
            meta=meta or {},
            categories=categories or [],
            tags=tags or [],
            created_at=now,
            updated_at=now,
            url=f"/wp-json/wp/v2/posts/{post_id}",
        )
        self._posts[post_id] = post
        self._persist_post(post)
        logger.info("{} Created draft post_id={}: '{}'", self._log_prefix, post_id, title[:40])
        return post_id

    async def update_post(self, post_id: int, **fields) -> Post:
        if post_id not in self._posts:
            raise KeyError(f"Post {post_id} not found")
        post = self._posts[post_id]
        for key, value in fields.items():
            if hasattr(post, key):
                setattr(post, key, value)
        post.updated_at = datetime.now()
        self._persist_post(post)
        logger.info("{} Updated post_id={}", self._log_prefix, post_id)
        return post

    async def schedule_publish(self, post_id: int, at: datetime) -> Post:
        return await self.update_post(
            post_id, status="future", published_at=at
        )

    async def publish(self, post_id: int) -> Post:
        return await self.update_post(
            post_id, status="publish", published_at=datetime.now()
        )

    async def upload_image(
        self, file_path: str, alt_text: str = ""
    ) -> int:
        media_id = self._next_media_id
        self._next_media_id += 1
        path = Path(file_path)
        # mock: file:// URL
        source_url = f"file://{path.absolute()}" if path.exists() else f"/uploads/{path.name}"
        media = Media(
            id=media_id,
            source_url=source_url,
            alt_text=alt_text,
            title=path.stem,
        )
        self._media[media_id] = media
        self._persist_media(media)
        logger.info(
            "{} Uploaded media_id={}: {} (alt='{}')",
            self._log_prefix, media_id, file_path, alt_text[:30],
        )
        return media_id

    async def list_categories(self) -> list[Category]:
        return list(self._categories.values())

    def get_storage_stats(self) -> dict:
        """테스트/디버깅용."""
        return {
            "posts": len(self._posts),
            "media": len(self._media),
            "categories": len(self._categories),
            "next_post_id": self._next_post_id,
            "next_media_id": self._next_media_id,
            "sqlite": self._db is not None,
        }

    async def delete_post(self, post_id: int) -> bool:
        """MockWP에서 post 삭제. SQLite도 함께 정리.

        Args:
            post_id: 삭제할 post ID

        Returns:
            True if deleted, False if not found
        """
        if post_id not in self._posts:
            return False
        del self._posts[post_id]
        # SQLite도 삭제
        if self._db:
            cur = self._db.cursor()
            cur.execute("DELETE FROM posts WHERE id = ?", (post_id,))
            self._db.commit()
        logger.info("{} Deleted post_id={}", self._log_prefix, post_id)
        return True

    async def delete_posts(
        self,
        *,
        status: str = "any",
        keep_last: int = 0,
        slug_prefix: str = "",
    ) -> list[int]:
        """조건에 맞는 여러 posts 삭제.

        Args:
            status: 'draft'/'publish'/'future'/'any'
            keep_last: 최근 N개 유지 (0 = 전부 삭제)
            slug_prefix: slug 시작이 이 prefix인 것만 (빈 문자열 = 모두)

        Returns:
            삭제된 post_id list
        """
        candidates = list(self._posts.values())
        if status != "any":
            candidates = [p for p in candidates if p.status == status]
        if slug_prefix:
            candidates = [p for p in candidates if (p.slug or "").startswith(slug_prefix)]
        # 최신 순 정렬
        candidates.sort(key=lambda p: p.created_at or datetime.min, reverse=True)
        # keep_last N개 제외
        to_delete = candidates[keep_last:] if keep_last > 0 else candidates

        deleted_ids: list[int] = []
        for post in to_delete:
            if await self.delete_post(post.id):
                deleted_ids.append(post.id)
        return deleted_ids


__all__ = ["MockWordPressClient"]
