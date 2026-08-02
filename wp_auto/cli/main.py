"""wp-auto 최상위 CLI 진입점.

Day 1 범위: 점수화 코어 스모크 테스트 (`wp-auto example`).
W2에서 추가: `wp-auto verify <html-file>`, `wp-auto generate`, `wp-auto publish --mock`.
"""

from __future__ import annotations

import sys

import click
from loguru import logger

from wp_auto import __version__
from wp_auto.core.content_score import (
    ContentMetrics,
    ContentQualityLevel,
    SpecializedContentOptimizer,
)
from wp_auto.cli.verify import verify


def _configure_logger(verbose: bool) -> None:
    """loguru 기본 설정."""
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(sys.stderr, level=level, format="<level>{message}</level>")


@click.group()
@click.version_option(version=__version__, prog_name="wp-auto")
@click.option("-v", "--verbose", is_flag=True, help="DEBUG 로깅 활성화")
def cli(verbose: bool) -> None:
    """WP-Free-Blog-Automation: 워드프레스 블로그 자동화 도구."""
    _configure_logger(verbose)


@cli.command()
def example() -> None:
    """점수화 코어 동작 예시 (EXCELLENT 케이스).

    `범용_로직1.txt` L246-272 의 sample 데이터를 그대로 실행해서
    점수화 파이프라인이 정상 동작하는지 확인.
    """
    metrics = ContentMetrics(
        title="2026년 특화 니치 블로그 수익화 완벽 가이드",
        word_count=3200,
        has_original_analysis=True,
        has_step_by_step_guide=True,
        has_data_or_case=True,
        has_comparison_table=True,
        has_faq=True,
        author_experience_mentioned=True,
        author_bio_present=True,
        sources_cited=5,
        update_date_present=True,
        main_keyword_in_title=True,
        h2_count=7,
        internal_links=4,
        external_authority_links=3,
        meta_description_length=155,
        images_optimized=True,
        lazy_load_applied=True,
        unnecessary_js_css=False,
        estimated_lcp_ok=True,
        mobile_friendly=True,
    )
    optimizer = SpecializedContentOptimizer()
    result = optimizer.verify(metrics)
    optimizer.print_report(result)

    # 종료 코드: 0 (PASS 이상), 1 (FAIL)
    if result.level == ContentQualityLevel.FAIL:
        sys.exit(1)
    sys.exit(0)


@cli.command()
def doctor() -> None:
    """환경 진단: 의존성, 설정, WP 모드."""
    click.echo(f"wp-auto v{__version__}")
    click.echo("")

    # 의존성 체크
    deps = [
        ("click", "click"),
        ("loguru", "loguru"),
        ("pydantic", "pydantic"),
        ("pydantic-settings", "pydantic_settings"),
        ("beautifulsoup4", "bs4"),
        ("lxml", "lxml"),
    ]
    click.echo("=== 의존성 ===")
    for display_name, module_name in deps:
        try:
            mod = __import__(module_name)
            version = getattr(mod, "__version__", "?")
            click.echo(f"  [OK] {display_name:20s} {version}")
        except ImportError:
            click.echo(f"  [NG] {display_name:20s} NOT INSTALLED")

    # WP 모드 (Day 1은 항상 mock)
    click.echo("")
    click.echo("=== WP 모드 ===")
    click.echo("  - Day 1: Mock 모드 (WP 의존성 0개)")
    click.echo("  - 사용자가 WP 사이트 세팅 후 .env의 WP_MOCK=false로 전환")

    # 점수화 코어 점검
    click.echo("")
    click.echo("=== 점수화 코어 ===")
    try:
        opt = SpecializedContentOptimizer()
        click.echo(f"  [OK] SpecializedContentOptimizer 가중치: {opt.weights}")
    except Exception as e:
        click.echo(f"  [NG] 점수화 코어 로드 실패: {e}")
        sys.exit(1)

    click.echo("")
    click.echo("환경 진단 완료.")


# D2에서 추가: verify 서브커맨드 등록
cli.add_command(verify, name="verify")


if __name__ == "__main__":
    cli()
