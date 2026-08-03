"""wp-auto 최상위 CLI 진입점.

Day 1 범위: 점수화 코어 스모크 테스트 (`wp-auto example`).
W2에서 추가: `wp-auto verify <html-file>`, `wp-auto generate`, `wp-auto publish --mock`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click
from loguru import logger

from wp_auto import __version__
from wp_auto.cli.publish import list_posts_cmd, publish
from wp_auto.cli.ui import ui
from wp_auto.cli.verify import verify
from wp_auto.cli.clean_mock import clean_mock
from wp_auto.cli.ingest import (
    ingest_url_cmd,
    ingest_pdf_cmd,
    research_cmd,
)
from wp_auto.cli.publish_md import publish_md_cmd
from wp_auto.core.content_score import (
    ContentMetrics,
    ContentQualityLevel,
    SpecializedContentOptimizer,
)


def _load_dotenv() -> None:
    """wp-auto CLI 실행 시 .env 자동 로드 (있으면 환경변수로 set).

    우선순위: 이미 환경변수 set된 값 유지, .env에 없으면 set.
    chunked 시연 스크립트들과 동일 DB_PATH를 쓰기 위해 필요.
    """
    # CWD부터 부모 디렉토리 순으로 .env 탐색
    cwd = Path.cwd()
    for candidate in [cwd, *cwd.parents]:
        env_file = candidate / ".env"
        if env_file.is_file():
            try:
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip()
                    # setdefault: 이미 환경변수 있으면 유지, 없으면 .env 값 사용
                    os.environ.setdefault(k, v)
            except Exception as e:
                logger.debug(".env read failed ({}): {}", env_file, e)
            return  # 첫 번째 .env에서 멈춤


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
    _load_dotenv()  # .env 자동 로드 (Mock DB_PATH 등 환경변수 일관성)
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

# W4에서 추가: publish, list-posts
cli.add_command(publish, name="publish")
cli.add_command(list_posts_cmd, name="list-posts")

# v0.3.0: Web UI
cli.add_command(ui, name="ui")

# v0.3.0+: MockWP 정리 (시연/테스트 누적 posts 청소)
cli.add_command(clean_mock, name="clean-mock")

# v0.9.0: URL/PDF 입력 + 직접 작성 배포
cli.add_command(ingest_url_cmd, name="ingest-url")
cli.add_command(ingest_pdf_cmd, name="ingest-pdf")
cli.add_command(research_cmd, name="research")
cli.add_command(publish_md_cmd, name="publish-md")


if __name__ == "__main__":
    cli()
