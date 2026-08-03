"""`wp-auto clean-mock` 명령: MockWordPressClient DB의 posts 정리.

1인 self-use에서 chunked 시연 등으로 mock posts가 누적될 때 정리용.

사용법:
    wp-auto clean-mock --dry-run                      # 미리보기 (기본)
    wp-auto clean-mock --keep-last 5 --yes            # 최근 5개만 남기고 삭제
    wp-auto clean-mock --status draft --yes           # draft만 전부 삭제
    wp-auto clean-mock --prefix c-short- --yes        # slug prefix 필터
    wp-auto clean-mock --all --yes                    # 전체 삭제 (--keep-last 0과 동일)
"""

from __future__ import annotations

import asyncio

import click

from wp_auto.wp.factory import get_wp_client


def _format_post(p) -> str:
    """Post 1개 → 한 줄 표시."""
    title_short = (p.title or "")[:50]
    slug_short = (p.slug or "")[:30]
    created = p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else "-"
    return f"  #{p.id:<4d}  {p.status:8s}  {created}  {title_short}  ({slug_short})"


@click.command(name="clean-mock")
@click.option(
    "--status",
    type=click.Choice(["draft", "publish", "future", "any"]),
    default="any",
    help="삭제 대상 status (default: any)",
)
@click.option(
    "--prefix",
    default="",
    help="slug prefix 필터 (예: c-short-, d-long-). 빈 문자열 = 전체",
)
@click.option(
    "--keep-last",
    type=int,
    default=0,
    help="최근 N개 유지 (default: 0 = 전부 삭제 대상)",
)
@click.option(
    "--all",
    "delete_all",
    is_flag=True,
    help="전체 삭제 (--keep-last 0과 동일, 가독성 옵션)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="미리보기만 (기본 동작이므로 보통 생략 가능)",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="실제 삭제 실행 (없으면 dry-run)",
)
def clean_mock(
    status: str, prefix: str, keep_last: int, delete_all: bool, dry_run: bool, yes: bool
) -> None:
    """MockWordPressClient DB의 posts 정리.

    기본은 dry-run: 어떤 posts가 삭제 대상인지 미리보기.
    --yes 또는 -y 옵션으로 실제 삭제 실행.
    """
    effective_keep_last = 0 if delete_all else keep_last
    apply = yes  # --yes 없으면 dry-run

    click.echo("===== clean-mock =====")
    click.echo(f"  status:        {status}")
    click.echo(f"  prefix:        '{prefix}'")
    click.echo(f"  keep_last:     {effective_keep_last}")
    click.echo(f"  mode:          {'APPLY (실제 삭제)' if apply else 'DRY-RUN (미리보기)'}")
    click.echo("")

    async def _run() -> None:
        client = get_wp_client()
        # 전체 post 수 표시
        all_posts = await client.list_posts(status="any", per_page=10000)
        click.echo(f"  전체 posts: {len(all_posts)}")
        # status별 카운트
        status_counts: dict[str, int] = {}
        for p in all_posts:
            status_counts[p.status] = status_counts.get(p.status, 0) + 1
        for st, cnt in sorted(status_counts.items()):
            click.echo(f"    {st:8s} {cnt}")
        click.echo("")

        if apply:
            deleted_ids = await client.delete_posts(
                status=status, keep_last=effective_keep_last, slug_prefix=prefix
            )
            click.echo(f"[OK] {len(deleted_ids)} posts 삭제됨: {deleted_ids}")
        else:
            # dry-run: 삭제 후보만 미리보기
            candidates = list(client._posts.values())  # noqa: SLF001
            if status != "any":
                candidates = [p for p in candidates if p.status == status]
            if prefix:
                candidates = [p for p in candidates if (p.slug or "").startswith(prefix)]
            candidates.sort(key=lambda p: p.created_at, reverse=True)
            to_delete = (
                candidates[effective_keep_last:] if effective_keep_last > 0 else candidates
            )
            click.echo(f"  [DRY-RUN] 삭제 후보: {len(to_delete)} posts")
            if to_delete:
                click.echo("")
                for p in to_delete[:20]:
                    click.echo(_format_post(p))
                if len(to_delete) > 20:
                    click.echo(f"  ... ({len(to_delete) - 20} more)")
                click.echo("")
                click.echo("  실제 삭제하려면 --yes 또는 -y 옵션을 추가하세요.")
            else:
                click.echo("  (삭제 대상 없음)")

    asyncio.run(_run())


__all__ = ["clean_mock"]
