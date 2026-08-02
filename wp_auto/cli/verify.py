"""`wp-auto verify` 명령: HTML 파일 점수화.

사용법:
    wp-auto verify <html-file> [--focus-keyword KW] [--json]
    wp-auto verify <html-file> --save-report report.txt
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import click

from wp_auto.core.content_score import (
    ContentQualityLevel,
    SpecializedContentOptimizer,
)


@click.command()
@click.argument("html_file", type=click.Path(exists=True, readable=True, path_type=Path))
@click.option(
    "-k",
    "--focus-keyword",
    default=None,
    help="메인 키워드. 제공되면 main_keyword_in_title 자동 체크.",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="JSON 형식으로 결과 출력 (CI/CD 연동).",
)
@click.option(
    "-o",
    "--save-report",
    type=click.Path(path_type=Path),
    default=None,
    help="리포트를 파일로 저장 (마크다운 형식).",
)
def verify(
    html_file: Path,
    focus_keyword: Optional[str],
    as_json: bool,
    save_report: Optional[Path],
) -> None:
    """HTML 파일을 점수화합니다.

    HTML_FILE: 점수화할 HTML 파일 경로 (.html, .htm, 또는 원시 HTML)
    """
    html = html_file.read_text(encoding="utf-8")

    optimizer = SpecializedContentOptimizer()
    result = optimizer.verify_html(html, focus_keyword=focus_keyword)

    if as_json:
        # JSON 출력 (CI/CD)
        click.echo(
            json.dumps(
                {
                    "file": str(html_file),
                    "total_score": result.total_score,
                    "level": result.level.value,
                    "category_scores": result.category_scores,
                    "feedback": result.feedback,
                    "recommendations": result.recommendations,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        # 사람이 읽기 좋은 형식
        click.echo(f"파일: {html_file}")
        if focus_keyword:
            click.echo(f"포커스 키워드: {focus_keyword}")
        click.echo("")
        optimizer.print_report(result)

    # 마크다운 리포트 저장
    if save_report:
        _save_markdown_report(save_report, html_file, result)
        click.echo(f"\n리포트 저장: {save_report}")

    # 종료 코드
    if result.level == ContentQualityLevel.FAIL:
        sys.exit(1)
    sys.exit(0)


def _save_markdown_report(
    path: Path, html_file: Path, result
) -> None:
    """마크다운 리포트 저장."""
    lines = [
        f"# 점수화 리포트: {html_file.name}",
        "",
        f"**파일**: `{html_file}`  ",
        f"**총점**: {result.total_score} / 100  ",
        f"**판정**: {result.level.value}",
        "",
        "## 카테고리별 점수",
        "",
        "| 카테고리 | 점수 | 만점 |",
        "|---------|------|------|",
    ]
    weights = {"content_depth": 40, "eeat": 25, "seo": 20, "speed": 15}
    for cat, score in result.category_scores.items():
        lines.append(f"| {cat} | {score} | {weights[cat]} |")
    lines.append("")

    if result.feedback:
        lines.append("## 문제점")
        lines.append("")
        for f in result.feedback:
            lines.append(f"- {f}")
        lines.append("")

    if result.recommendations:
        lines.append("## 개선 권장사항")
        lines.append("")
        for r in result.recommendations:
            lines.append(f"- {r}")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
