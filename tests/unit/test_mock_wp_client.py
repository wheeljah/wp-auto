"""MockWordPressClient + Factory 단위 테스트."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from wp_auto.wp.factory import get_wp_client
from wp_auto.wp.mock_client import MockWordPressClient

# === 1. MockWordPressClient (in-memory) ===

@pytest.fixture
def client() -> MockWordPressClient:
    return MockWordPressClient()


@pytest.mark.asyncio
async def test_create_draft_assigns_incrementing_id(client: MockWordPressClient) -> None:
    """create_draft → 단조 증가 ID."""
    id1 = await client.create_draft(title="A", content="<p>A</p>")
    id2 = await client.create_draft(title="B", content="<p>B</p>")
    assert id2 == id1 + 1


@pytest.mark.asyncio
async def test_create_draft_default_status_is_draft(client: MockWordPressClient) -> None:
    """기본 status='draft'."""
    post_id = await client.create_draft(title="X", content="<p>X</p>")
    post = await client.get_post(post_id)
    assert post.status == "draft"
    assert post.title == "X"


@pytest.mark.asyncio
async def test_get_post_returns_correct_post(client: MockWordPressClient) -> None:
    """get_post → 정확히 매칭되는 post."""
    post_id = await client.create_draft(
        title="My Title", content="<p>Content</p>", slug="my-slug"
    )
    post = await client.get_post(post_id)
    assert post.title == "My Title"
    assert post.content == "<p>Content</p>"
    assert post.slug == "my-slug"


@pytest.mark.asyncio
async def test_get_post_raises_keyerror_for_missing(client: MockWordPressClient) -> None:
    """존재하지 않는 post_id → KeyError."""
    with pytest.raises(KeyError):
        await client.get_post(9999)


@pytest.mark.asyncio
async def test_list_posts_filters_by_status(client: MockWordPressClient) -> None:
    """list_posts status 필터."""
    draft_id = await client.create_draft(title="Draft", content="")
    publish_id = await client.create_draft(title="To publish", content="")
    await client.publish(publish_id)

    drafts = await client.list_posts(status="draft")
    published = await client.list_posts(status="publish")

    assert any(p.id == draft_id for p in drafts)
    assert not any(p.id == publish_id for p in drafts)
    assert any(p.id == publish_id for p in published)


@pytest.mark.asyncio
async def test_list_posts_any_returns_all(client: MockWordPressClient) -> None:
    """status='any' → 모든 status."""
    await client.create_draft(title="D1", content="")
    pid = await client.create_draft(title="P1", content="")
    await client.publish(pid)
    all_posts = await client.list_posts(status="any")
    assert len(all_posts) == 2


@pytest.mark.asyncio
async def test_update_post_changes_fields(client: MockWordPressClient) -> None:
    """update_post → 필드 변경."""
    post_id = await client.create_draft(title="Old", content="<p>Old</p>")
    updated = await client.update_post(post_id, title="New", content="<p>New</p>")
    assert updated.title == "New"
    assert updated.content == "<p>New</p>"


@pytest.mark.asyncio
async def test_publish_sets_status_and_published_at(client: MockWordPressClient) -> None:
    """publish → status='publish' + published_at 설정."""
    post_id = await client.create_draft(title="X", content="<p>X</p>")
    published = await client.publish(post_id)
    assert published.status == "publish"
    assert published.published_at is not None


@pytest.mark.asyncio
async def test_schedule_publish_sets_future_status(client: MockWordPressClient) -> None:
    """schedule_publish → status='future'."""
    post_id = await client.create_draft(title="X", content="<p>X</p>")
    future_time = datetime.now() + timedelta(days=1)
    scheduled = await client.schedule_publish(post_id, future_time)
    assert scheduled.status == "future"
    assert scheduled.published_at == future_time


@pytest.mark.asyncio
async def test_upload_image_assigns_media_id(client: MockWordPressClient) -> None:
    """upload_image → media_id."""
    media_id = await client.upload_image("/tmp/test.jpg", alt_text="Test")
    assert media_id >= 1
    assert media_id in client._media


@pytest.mark.asyncio
async def test_upload_image_mock_creates_entry_for_any_path(client: MockWordPressClient) -> None:
    """Mock은 실제 파일 검사 안 함 — 어떤 경로든 media_id 발급.

    (RealWordPressClient는 실제 파일 존재 확인)
    """
    media_id = await client.upload_image("/nonexistent/file.jpg", alt_text="Mock")
    assert media_id >= 1
    assert media_id in client._media
    # file:// URL 또는 /uploads/ 폴백
    media = client._media[media_id]
    assert "/nonexistent/file.jpg" in media.source_url or "file.jpg" in media.source_url


@pytest.mark.asyncio
async def test_list_categories_includes_uncategorized(client: MockWordPressClient) -> None:
    """기본 '미분류' 카테고리 존재."""
    cats = await client.list_categories()
    assert any(c.slug == "uncategorized" for c in cats)


def test_get_storage_stats(client: MockWordPressClient) -> None:
    """storage stats."""
    stats = client.get_storage_stats()
    assert "posts" in stats
    assert "media" in stats
    assert stats["sqlite"] is False


# === 2. SQLite 영속화 ===

@pytest.mark.asyncio
async def test_sqlite_persistence(tmp_path: Path) -> None:
    """SQLite로 영속화 + 재로드."""
    db_path = tmp_path / "test.db"

    # 1) 글 생성 + close
    c1 = MockWordPressClient(db_path=db_path)
    post_id = await c1.create_draft(title="Persistent", content="<p>P</p>")

    # 2) 새 인스턴스로 다시 로드
    c2 = MockWordPressClient(db_path=db_path)
    post = await c2.get_post(post_id)
    assert post.title == "Persistent"
    assert post.content == "<p>P</p>"


# === 3. Factory ===

def test_factory_returns_mock_by_default(monkeypatch) -> None:
    """환경변수 없으면 Mock."""
    for key in ["WP_SITE_URL", "WP_USER", "WP_APP_PASSWORD", "WP_MOCK"]:
        monkeypatch.delenv(key, raising=False)
    client = get_wp_client()
    assert isinstance(client, MockWordPressClient)


def test_factory_returns_mock_when_wp_mock_true(monkeypatch) -> None:
    """WP_MOCK=true → Mock."""
    monkeypatch.setenv("WP_MOCK", "true")
    monkeypatch.delenv("WP_SITE_URL", raising=False)
    client = get_wp_client()
    assert isinstance(client, MockWordPressClient)


def test_factory_returns_mock_when_site_url_empty(monkeypatch) -> None:
    """WP_SITE_URL 비어있으면 Mock."""
    monkeypatch.setenv("WP_MOCK", "false")
    monkeypatch.setenv("WP_SITE_URL", "")
    client = get_wp_client()
    assert isinstance(client, MockWordPressClient)


def test_factory_returns_real_when_all_set(monkeypatch) -> None:
    """모든 환경변수 설정 시 Real."""
    monkeypatch.setenv("WP_MOCK", "false")
    monkeypatch.setenv("WP_SITE_URL", "https://example.com")
    monkeypatch.setenv("WP_USER", "admin")
    monkeypatch.setenv("WP_APP_PASSWORD", "xxxx xxxx xxxx xxxx xxxx xxxx")
    client = get_wp_client()
    from wp_auto.wp.real_client import RealWordPressClient
    assert isinstance(client, RealWordPressClient)
