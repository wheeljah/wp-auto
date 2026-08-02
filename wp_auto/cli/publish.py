"""`wp-auto publish` 명령: HTML/초안을 WP에 발행 (Mock 또는 Real).

사용법:
    wp-auto publish <html-file> [--title TITLE] [--focus-keyword KW] [--status draft|publish|future]
    wp-auto publish <post-id>                        # 기존 draft → publish
    wp-auto list-posts                                # Mock DB 또는 실 WP의 글 목록
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

import click

from wp_auto.core.content_score import (
    ContentQualityLevel,
    SpecializedContentOptimizer,
)
from wp_auto.wp.factory import get_wp_client


def _extract_title_from_html(html: str) -> str:
    """HTML에서 첫 <h1> 또는 <title> 추출."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    title = soup.find("title")
    if title and title.string:
        return title.string.strip()
    return "Untitled"


def _extract_meta_description_from_html(html: str) -> str:
    """HTML에서 <meta name='description'> 추출."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return meta["content"].strip()
    return ""


def _extract_slug_from_html(html: str) -> str:
    """HTML에서 slug (canonical) 추출."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    canonical = soup.find("link", rel="canonical")
    if canonical and canonical.get("href"):
        url = canonical["href"]
        return url.rstrip("/").split("/")[-1][:200]  # WP slug max 200
    return ""


def _verify_html(html: str, focus_keyword: str | None) -> tuple[bool, float, list[str]]:
    """점수화 + 발행 가능 여부."""
    optimizer = SpecializedContentOptimizer()
    result = optimizer.verify_html(html, focus_keyword=focus_keyword)
    passed = result.level != ContentQualityLevel.FAIL
    return passed, result.total_score, result.recommendations


@click.command()
@click.argument("input_path", type=click.Path(exists=True, readable=True, path_type=Path))
@click.option("--title", default=None, help="글 제목 (기본: HTML에서 <h1>/<title> 추출)")
@click.option("--focus-keyword", "-k", default=None, help="메인 키워드")
@click.option(
    "--status",
    type=click.Choice(["draft", "publish", "future"]),
    default="draft",
    help="발행 상태 (draft/즉시/예약)",
)
@click.option(
    "--at",
    type=click.DateTime(formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"]),
    default=None,
    help="예약 시간 (status=future일 때)",
)
@click.option(
    "--force",
    is_flag=True,
    help="점수 < 75여도 발행",
)
@click.option(
    "--score-threshold",
    type=float,
    default=75.0,
    help="발행 차단 점수 임계값 (default 75)",
)
def publish(
    input_path: Path,
    title: str | None,
    focus_keyword: str | None,
    status: str,
    at: datetime | None,
    force: bool,
    score_threshold: float,
) -> None:
    """HTML 파일을 WP에 발행.

    INPUT_PATH: HTML 파일 또는 기존 draft의 post_id
    """
    # post_id (정수) vs HTML 파일 분기
    if str(input_path).isdigit():
        post_id = int(str(input_path))
        asyncio.run(_publish_existing(post_id, status, at))
        return

    html = input_path.read_text(encoding="utf-8")

    # 1) 점수화 (게이트)
    passed, score, recs = _verify_html(html, focus_keyword)
    click.echo(f"점수: {score:.0f}/100  (임계값: {score_threshold:.0f})")
    if not passed and not force and status != "draft":
        click.echo(f"\n[!] 점수 {score:.0f} < {score_threshold:.0f}: 발행 차단")
        click.echo("    권고:")
        for r in recs[:5]:
            click.echo(f"      - {r}")
        click.echo("\n--force 옵션으로 무시하고 발행하거나, --status draft로 초안만 저장하세요.")
        sys.exit(1)

    # 2) WP 발행
    final_title = title or _extract_title_from_html(html)
    meta_desc = _extract_meta_description_from_html(html)
    slug = _extract_slug_from_html(html)
    click.echo(f"제목: {final_title}")
    click.echo(f"Slug: {slug or '(auto)'}")
    click.echo(f"상태: {status}")

    post_id = asyncio.run(
        _publish_new(
            title=final_title,
            content=html,
            slug=slug,
            excerpt=meta_desc,
            status=status,
            at=at,
        )
    )
    click.echo(f"\n[OK] post_id={post_id} 생성/발행 완료")


async def _publish_new(
    title: str,
    content: str,
    slug: str,
    excerpt: str,
    status: str,
    at: datetime | None,
) -> int:
    """새 글 발행."""
    client = get_wp_client()
    post_id = await client.create_draft(
        title=title,
        content=content,
        slug=slug,
        excerpt=excerpt,
        status="draft",  # 먼저 draft로 생성
    )
    if status == "publish":
        await client.publish(post_id)
    elif status == "future" and at:
        await client.schedule_publish(post_id, at)
    return post_id


async def _publish_existing(
    post_id: int, status: str, at: datetime | None
) -> None:
    """기존 draft → publish 또는 future."""
    client = get_wp_client()
    post = await client.get_post(post_id)
    click.echo(f"기존 글: {post.title} (status={post.status})")
    if status == "publish":
        published = await client.publish(post_id)
        click.echo(f"[OK] 발행 완료: {published.url or post_id}")
    elif status == "future" and at:
        scheduled = await client.schedule_publish(post_id, at)
        click.echo(f"[OK] 예약 완료 ({at}): {scheduled.url or post_id}")
    else:
        click.echo(f"상태 변경 없음: {post.status}")


@click.command(name="list-posts")
@click.option("--status", default="any", help="draft|publish|future|any")
@click.option("--limit", type=int, default=20, help="최대 결과 수")
def list_posts_cmd(status: str, limit: int) -> None:
    """글 목록 (Mock DB 또는 실 WP)."""

    async def _list() -> None:
        client = get_wp_client()
        posts = await client.list_posts(status=status, per_page=limit)
        if not posts:
            click.echo("(글 없음)")
            return
        click.echo(f"{'ID':>5}  {'Status':12s}  {'Title':50s}  Created")
        click.echo("-" * 90)
        for p in posts:
            created = p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else "-"
            title_truncated = p.title[:50]
            click.echo(f"{p.id:>5}  {p.status:12s}  {title_truncated:50s}  {created}")

    asyncio.run(_list())


__all__ = ["publish", "list_posts_cmd"]
