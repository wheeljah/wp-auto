"""`wp-auto verify` 명령: HTML 점수화 + SEO 분석.

사용법:
    wp-auto verify <html-file> [--focus-keyword KW] [--json] [--full] [--save-report FILE]

D6: --full 옵션으로 콘텐츠 점수화 + SEO 분석을 통합 점수 카드로 출력.
D7: --save-report로 마크다운 리포트 저장.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from wp_auto.core.content_score import (
    ContentQualityLevel,
    SpecializedContentOptimizer,
)
from wp_auto.core.seo_analyzer import RankMathStyleAnalyzer


@click.command()
@click.argument("html_file", type=click.Path(exists=True, readable=True, path_type=Path))
@click.option(
    "-k",
    "--focus-keyword",
    default=None,
    help="메인 키워드 (--full 모드에서 SEO 분석에 사용).",
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
    help="리포트를 마크다운 파일로 저장.",
)
@click.option(
    "--full",
    "full",
    is_flag=True,
    help="콘텐츠 점수화 + SEO 분석 통합 리포트 (focus-keyword 필수).",
)
def verify(
    html_file: Path,
    focus_keyword: str | None,
    as_json: bool,
    save_report: Path | None,
    full: bool,
) -> None:
    """HTML 파일을 점수화합니다.

    HTML_FILE: 점수화할 HTML 파일 경로

    기본 모드: 콘텐츠 품질 점수 (100점)
    --full: 콘텐츠 + SEO 통합 점수 (각 100점)
    """
    html = html_file.read_text(encoding="utf-8")

    if full:
        _run_full_report(html, html_file, focus_keyword, as_json, save_report)
    else:
        _run_content_only(html, html_file, focus_keyword, as_json, save_report)


def _run_content_only(
    html: str,
    html_file: Path,
    focus_keyword: str | None,
    as_json: bool,
    save_report: Path | None,
) -> None:
    """콘텐츠 점수화만 실행."""
    optimizer = SpecializedContentOptimizer()
    result = optimizer.verify_html(html, focus_keyword=focus_keyword)

    if as_json:
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
        click.echo(f"파일: {html_file}")
        if focus_keyword:
            click.echo(f"포커스 키워드: {focus_keyword}")
        click.echo("")
        optimizer.print_report(result)

    if save_report:
        _save_content_report(save_report, html_file, result)
        click.echo(f"\n리포트 저장: {save_report}")

    if result.level == ContentQualityLevel.FAIL:
        sys.exit(1)


def _run_full_report(
    html: str,
    html_file: Path,
    focus_keyword: str | None,
    as_json: bool,
    save_report: Path | None,
) -> None:
    """콘텐츠 + SEO 통합 점수 카드 (D6/D7)."""
    if not focus_keyword:
        click.echo("오류: --full 모드에는 --focus-keyword가 필요합니다.", err=True)
        sys.exit(2)

    content_opt = SpecializedContentOptimizer()
    content_result = content_opt.verify_html(html, focus_keyword=focus_keyword)

    seo_analyzer = RankMathStyleAnalyzer()
    seo_result = seo_analyzer.analyze(html, focus_keyword=focus_keyword)

    if as_json:
        click.echo(
            json.dumps(
                {
                    "file": str(html_file),
                    "focus_keyword": focus_keyword,
                    "content": {
                        "total_score": content_result.total_score,
                        "level": content_result.level.value,
                        "category_scores": content_result.category_scores,
                        "feedback": content_result.feedback,
                    },
                    "seo": {
                        "total_score": seo_result.total_score,
                        "category_scores": seo_result.category_scores,
                        "items": [
                            {
                                "name": i.name,
                                "passed": i.passed,
                                "points_earned": i.points_earned,
                                "points_max": i.points_max,
                                "detail": i.detail,
                            }
                            for i in seo_result.items
                        ],
                    },
                    "overall_recommendations": _merge_recommendations(
                        content_result.recommendations, seo_result.recommendations
                    ),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        # 통합 점수 카드 출력
        _print_integrated_card(html_file, focus_keyword, content_result, seo_result)

    if save_report:
        _save_integrated_report(
            save_report, html_file, focus_keyword, content_result, seo_result
        )
        click.echo(f"\n리포트 저장: {save_report}")

    # 종료 코드: 어느 하나라도 FAIL이면 1
    if content_result.level == ContentQualityLevel.FAIL or seo_result.total_score < 50:
        sys.exit(1)


def _print_integrated_card(
    html_file: Path,
    focus_keyword: str,
    content_result,
    seo_result,
) -> None:
    """사람이 읽기 좋은 통합 점수 카드."""
    click.echo("=" * 60)
    click.echo("  WP-AUTO 통합 점수 카드 (--full)")
    click.echo("=" * 60)
    click.echo(f"  파일: {html_file}")
    click.echo(f"  포커스 키워드: {focus_keyword}")
    click.echo("")

    # 콘텐츠 점수
    click.echo("┌─ 콘텐츠 품질 (100점) ────────────────────────")
    click.echo(f"│  총점: {content_result.total_score:.0f} / 100")
    click.echo(f"│  판정: {content_result.level.value}")
    for cat, score in content_result.category_scores.items():
        bar = "█" * int(score / 5)  # 5점당 1칸
        click.echo(f"│  {cat:18s}  {score:5.1f}  {bar}")
    click.echo("└───────────────────────────────────────────────")
    click.echo("")

    # SEO 점수
    click.echo("┌─ SEO 분석 (Rank Math 스타일, 100점) ──────────")
    click.echo(f"│  총점: {seo_result.total_score:.0f} / 100")
    seo_rating = (
        "Great" if seo_result.total_score >= 81
        else "Good" if seo_result.total_score >= 51
        else "Bad"
    )
    click.echo(f"│  판정: {seo_rating}")
    for cat, score in seo_result.category_scores.items():
        bar = "█" * int(score / 5)
        click.echo(f"│  {cat:25s}  {score:5.1f}  {bar}")
    click.echo("└───────────────────────────────────────────────")
    click.echo("")

    # 권고사항
    recs = _merge_recommendations(
        content_result.recommendations, seo_result.recommendations
    )
    if recs:
        click.echo("┌─ 개선 권고사항 ───────────────────────────────")
        for i, r in enumerate(recs, 1):
            click.echo(f"│  {i:2d}. {r}")
        click.echo("└───────────────────────────────────────────────")
    click.echo("")

    # 종합 판정
    overall = _overall_verdict(content_result.total_score, seo_result.total_score)
    click.echo(f"  >>> 종합 판정: {overall}")
    click.echo("=" * 60)


def _overall_verdict(content_score: float, seo_score: float) -> str:
    """콘텐츠 + SEO 종합 판정."""
    if content_score >= 80 and seo_score >= 81:
        return "우수 (발행 권장)"
    if content_score >= 75 and seo_score >= 51:
        return "발행 가능 (일부 개선 권장)"
    if content_score < 75 and seo_score < 51:
        return "보완 필요 (둘 다 미흡)"
    if content_score < 75:
        return "콘텐츠 보완 필요"
    return "SEO 보완 필요"


def _merge_recommendations(content_recs: list[str], seo_recs: list[str]) -> list[str]:
    """중복 제거 후 합치기 (SEO 권고 우선)."""
    seen = set()
    result = []
    for r in seo_recs + content_recs:
        key = r.strip()[:30]
        if key not in seen:
            seen.add(key)
            result.append(r)
    return result[:10]  # 최대 10개


def _save_content_report(
    path: Path, html_file: Path, result
) -> None:
    """콘텐츠 점수 리포트 (마크다운)."""
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
        for f in result.feedback:
            lines.append(f"- {f}")
        lines.append("")

    if result.recommendations:
        lines.append("## 개선 권장사항")
        for r in result.recommendations:
            lines.append(f"- {r}")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def _save_integrated_report(
    path: Path,
    html_file: Path,
    focus_keyword: str,
    content_result,
    seo_result,
) -> None:
    """통합 점수 리포트 (마크다운, D7)."""
    lines = [
        f"# 통합 점수 리포트: {html_file.name}",
        "",
        f"**파일**: `{html_file}`  ",
        f"**포커스 키워드**: `{focus_keyword}`  ",
        f"**작성일**: {Path(__file__).name}",
        "",
        "## 종합 판정",
        "",
        f"> {_overall_verdict(content_result.total_score, seo_result.total_score)}",
        "",
        "## 1. 콘텐츠 품질 점수",
        "",
        f"**총점**: {content_result.total_score:.0f} / 100  ",
        f"**판정**: {content_result.level.value}",
        "",
        "| 카테고리 | 점수 | 만점 | 비율 |",
        "|---------|------|------|------|",
    ]
    weights = {"content_depth": 40, "eeat": 25, "seo": 20, "speed": 15}
    for cat, score in content_result.category_scores.items():
        pct = score / weights[cat] * 100
        lines.append(f"| {cat} | {score:.0f} | {weights[cat]} | {pct:.0f}% |")
    lines.append("")

    if content_result.feedback:
        lines.append("### 콘텐츠 문제점")
        for f in content_result.feedback:
            lines.append(f"- {f}")
        lines.append("")

    lines.extend([
        "## 2. SEO 분석 (Rank Math 스타일)",
        "",
        f"**총점**: {seo_result.total_score:.0f} / 100",
        "",
        "| 카테고리 | 점수 | 만점 | 비율 |",
        "|---------|------|------|------|",
    ])
    for cat, score in seo_result.category_scores.items():
        max_p = seo_result.category_maxima[cat]
        pct = score / max_p * 100 if max_p > 0 else 0
        lines.append(f"| {cat} | {score:.0f} | {max_p} | {pct:.0f}% |")
    lines.append("")

    # SEO 항목별 결과
    lines.append("### SEO 체크 항목")
    lines.append("")
    lines.append("| 항목 | 결과 | 점수 |")
    lines.append("|------|------|------|")
    for item in seo_result.items:
        status = "✓" if item.passed else "✗"
        lines.append(f"| {item.name} | {status} | {item.points_earned:.0f} / {item.points_max:.0f} |")
    lines.append("")

    # 통합 권고
    recs = _merge_recommendations(
        content_result.recommendations, seo_result.recommendations
    )
    if recs:
        lines.append("## 개선 권고사항 (우선순위 순)")
        for i, r in enumerate(recs, 1):
            lines.append(f"{i}. {r}")
        lines.append("")

    lines.extend([
        "---",
        "",
        "*Generated by wp-auto v0.1.0 — wp-auto verify --full*",
    ])

    path.write_text("\n".join(lines), encoding="utf-8")
