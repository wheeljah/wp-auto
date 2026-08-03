"""`wp-auto publish-md` 명령: 직접 작성 markdown을 WP에 발행.

사용법:
    wp-auto publish-md <md-file> [--status draft|publish] [--score-threshold 75]
    wp-auto publish-md <md-file> --as-single    # 단일 stitch 모드
    wp-auto publish-md <md-file> --as-cluster   # pillar + N cluster 모드 (기본)
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click

from wp_auto.ai.markdown_loader import (
    MarkdownPost,
    load_markdown,
    md_to_cluster,
)
from wp_auto.core.content_score import (
    ContentQualityLevel,
    SpecializedContentOptimizer,
)
from wp_auto.wp.factory import get_wp_client


def _verify_html(html: str, focus_keyword: str | None) -> tuple[bool, float, list[str]]:
    """점수화 + 발행 가능 여부."""
    optimizer = SpecializedContentOptimizer()
    result = optimizer.verify_html(html, focus_keyword=focus_keyword)
    passed = result.level != ContentQualityLevel.FAIL
    return passed, result.total_score, result.recommendations


@click.command(name="publish-md")
@click.argument(
    "md_path",
    type=click.Path(exists=True, readable=True, path_type=Path),
)
@click.option(
    "--status",
    type=click.Choice(["draft", "publish", "future"]),
    default="draft",
    help="발행 상태 (draft/즉시/예약)",
)
@click.option(
    "--as-single",
    is_flag=True,
    help="단일 stitch 모드 (모든 chunk를 1 HTML에 합쳐서 1개 post)",
)
@click.option(
    "--as-cluster",
    "as_cluster",
    is_flag=True,
    default=True,
    help="pillar + N cluster 모드 (N+1개 posts, 기본)",
)
@click.option("--score-threshold", type=float, default=75.0, help="발행 차단 점수 (default 75)")
@click.option("--force", is_flag=True, help="점수 < 75여도 발행")
def publish_md_cmd(
    md_path: Path,
    status: str,
    as_single: bool,
    as_cluster: bool,
    score_threshold: float,
    force: bool,
) -> None:
    """Markdown 파일을 WP에 발행.

    MD_PATH: 직접 작성한 .md 파일 (frontmatter + H1/H2 섹션)
    """
    # 모드 충돌 체크
    if as_single and as_cluster:
        click.echo("[!] --as-single과 --as-cluster 동시 지정 불가", err=True)
        sys.exit(1)
    mode = "single" if as_single else "cluster"

    # 1) Markdown 로드
    click.echo(f"Markdown 로드: {md_path}")
    try:
        post: MarkdownPost = load_markdown(md_path)
    except Exception as e:
        click.echo(f"[!] 로드 실패: {e}", err=True)
        sys.exit(1)

    click.echo(f"  Title: {post.title}")
    click.echo(f"  Language: {post.language}")
    click.echo(f"  Sections (H2): {len(post.sections)}")
    click.echo(f"  Tags: {post.frontmatter.tags}")
    click.echo(f"  Categories: {post.frontmatter.categories}")

    # 2) Chunked cluster 변환
    cluster = md_to_cluster(
        post,
        language=post.language,
        author_name="1인 운영자 (직접 작성)",
    )

    # 3) 점수화 + 발행
    if mode == "single":
        html = cluster.stitch_single()
        passed, score, recs = _verify_html(html, post.frontmatter.keyword or None)
        click.echo(f"\n점수: {score:.0f}/100  (mode=single, threshold={score_threshold:.0f})")
        if not passed and not force and status != "draft":
            click.echo(f"[!] 점수 {score:.0f} < {score_threshold:.0f}: 발행 차단")
            _print_recs(recs)
            sys.exit(1)

        async def _publish_single() -> int:
            client = get_wp_client()
            post_id = await client.create_draft(
                title=cluster.pillar.title,
                content=html,
                slug=cluster.pillar.slug,
                excerpt=cluster.pillar.meta_description,
                status="draft",
            )
            if status == "publish":
                await client.publish(post_id)
            return post_id

        post_id = asyncio.run(_publish_single())
        click.echo(f"\n[OK] post_id={post_id} (single) 생성/발행 완료")

    else:  # cluster
        specs = cluster.to_wp_post_specs()
        click.echo(f"\nPillar + {len(cluster.chunks)} cluster ({len(specs)} posts) 발행...")

        async def _publish_cluster() -> list[int]:
            client = get_wp_client()
            post_ids: list[int] = []
            for spec in specs:
                # 점수화 (pillar만 게이트, cluster는 75점 미만이어도 발행 허용)
                if spec["type"] == "pillar":
                    passed, score, recs = _verify_html(spec["content"], post.frontmatter.keyword or None)
                    if not passed and not force and status != "draft":
                        click.echo(f"[!] Pillar 점수 {score:.0f} < {score_threshold:.0f}: 발행 차단")
                        _print_recs(recs)
                        sys.exit(1)
                    click.echo(f"  Pillar: {spec['title'][:40]}... (score={score:.0f})")

                post_id = await client.create_draft(
                    title=spec["title"],
                    content=spec["content"],
                    slug=spec["slug"],
                    excerpt=spec["excerpt"],
                    status="draft",
                )
                if status == "publish":
                    await client.publish(post_id)
                post_ids.append(post_id)
                click.echo(f"  [OK] {spec['type']:6s} → post_id={post_id} ({spec['title'][:40]})")

            return post_ids

        post_ids = asyncio.run(_publish_cluster())
        click.echo(f"\n[OK] {len(post_ids)}개 post 발행 완료")


def _print_recs(recs: list[str]) -> None:
    """권고사항 출력."""
    click.echo("    권고:")
    for r in recs[:5]:
        click.echo(f"      - {r}")


__all__ = ["publish_md_cmd"]
