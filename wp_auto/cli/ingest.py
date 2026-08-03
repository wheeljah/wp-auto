"""`wp-auto ingest-url`, `ingest-pdf`, `research` 명령.

URL/PDF 입력 → 텍스트 추출 → LLM으로 outline 자동 생성.

사용법:
    wp-auto ingest-url <url> [--keyword KW] [--intent I/C/T] [--language ko|en]
    wp-auto ingest-pdf <path> [--keyword KW] [--intent I/C/T]
    wp-auto research <topic> --source <url>... [--out outline.json]
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import click

from wp_auto.ai.ollama_client import OllamaClient
from wp_auto.ai.researcher import ResearchContext, Researcher
from wp_auto.ai.source_ingestor import (
    SourceRef,
    ingest_pdf,
    ingest_sources,
    ingest_url,
)


def _get_client(model: str) -> OllamaClient:
    """Ollama client (CPU-only mode safe)."""
    return OllamaClient(model=model)


@click.command(name="ingest-url")
@click.argument("url")
@click.option("--keyword", "-k", default=None, help="포커스 키워드 (없으면 URL의 title 사용)")
@click.option(
    "--intent",
    type=click.Choice(["informational", "commercial investigation", "transactional"]),
    default="informational",
    help="검색 의도 (informational/commercial/transactional)",
)
@click.option("--language", "-l", default="ko", type=click.Choice(["ko", "en"]))
@click.option(
    "--out",
    type=click.Path(path_type=Path),
    default=None,
    help="추출 결과 저장 경로 (JSON)",
)
@click.option("--model", default="qwen2.5:7b", help="Ollama 모델명")
def ingest_url_cmd(
    url: str,
    keyword: str | None,
    intent: str,
    language: str,
    out: Path | None,
    model: str,
) -> None:
    """URL에서 본문 추출 (Trafilatura).

    URL: 분석할 기사/문서 URL
    """
    try:
        ref = SourceRef.from_url(url, locale=language)
    except ValueError as e:
        click.echo(f"[!] URL 오류: {e}", err=True)
        sys.exit(1)

    click.echo(f"URL 추출 시작: {url}")
    try:
        extracted = ingest_url(ref)
    except Exception as e:
        click.echo(f"[!] 추출 실패: {e}", err=True)
        sys.exit(1)

    result = {
        "title": extracted.title,
        "body_chars": len(extracted.body),
        "summary": extracted.summary[:500] + "..." if len(extracted.summary) > 500 else extracted.summary,
        "key_facts": extracted.key_facts,
        "metadata": extracted.metadata,
        "language_hint": extracted.language_hint,
    }

    if out:
        out.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        click.echo(f"[OK] 저장: {out}")
    else:
        click.echo("\n=== 추출 결과 ===")
        click.echo(f"Title: {extracted.title}")
        click.echo(f"Body: {len(extracted.body):,}자")
        click.echo(f"Language: {extracted.language_hint}")
        click.echo(f"\nKey facts ({len(extracted.key_facts)}):")
        for i, f in enumerate(extracted.key_facts, 1):
            click.echo(f"  {i}. {f}")
        click.echo(f"\nSummary (앞 500자):\n{result['summary']}")


@click.command(name="ingest-pdf")
@click.argument("pdf_path", type=click.Path(exists=True, readable=True, path_type=Path))
@click.option("--keyword", "-k", default=None, help="포커스 키워드")
@click.option(
    "--intent",
    type=click.Choice(["informational", "commercial investigation", "transactional"]),
    default="informational",
)
@click.option("--language", "-l", default="ko", type=click.Choice(["ko", "en"]))
@click.option(
    "--out",
    type=click.Path(path_type=Path),
    default=None,
    help="추출 결과 저장 경로 (JSON)",
)
@click.option(
    "--max-pages",
    type=int,
    default=100,
    help="최대 PDF 페이지 수 (메모리 보호)",
)
def ingest_pdf_cmd(
    pdf_path: Path,
    keyword: str | None,
    intent: str,
    language: str,
    out: Path | None,
    max_pages: int,
) -> None:
    """PDF에서 본문 추출 (PyMuPDF).

    PDF_PATH: 분석할 PDF 파일 경로
    """
    try:
        ref = SourceRef.from_path(str(pdf_path), locale=language)
    except FileNotFoundError as e:
        click.echo(f"[!] 파일 오류: {e}", err=True)
        sys.exit(1)

    click.echo(f"PDF 추출 시작: {pdf_path}")
    try:
        extracted = ingest_pdf(ref, max_pages=max_pages)
    except Exception as e:
        click.echo(f"[!] 추출 실패: {e}", err=True)
        sys.exit(1)

    result = {
        "title": extracted.title,
        "body_chars": len(extracted.body),
        "page_count": extracted.metadata.get("page_count", "?"),
        "summary": extracted.summary[:500] + "..." if len(extracted.summary) > 500 else extracted.summary,
        "key_facts": extracted.key_facts,
        "metadata": extracted.metadata,
    }

    if out:
        out.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        click.echo(f"[OK] 저장: {out}")
    else:
        click.echo("\n=== 추출 결과 ===")
        click.echo(f"Title: {extracted.title}")
        click.echo(f"Pages: {extracted.metadata.get('page_count', '?')}")
        click.echo(f"Body: {len(extracted.body):,}자")
        click.echo(f"\nKey facts ({len(extracted.key_facts)}):")
        for i, f in enumerate(extracted.key_facts, 1):
            click.echo(f"  {i}. {f}")
        click.echo(f"\nSummary (앞 500자):\n{result['summary']}")


@click.command(name="research")
@click.argument("topic")
@click.option("--source", "-s", "sources", multiple=True, help="URL 또는 PDF 경로 (반복 가능)")
@click.option("--keyword", "-k", required=True, help="포커스 키워드")
@click.option(
    "--intent",
    type=click.Choice(["informational", "commercial investigation", "transactional"]),
    default="informational",
)
@click.option("--language", "-l", default="ko", type=click.Choice(["ko", "en"]))
@click.option("--target-length", type=int, default=2000, help="목표 분량 (자)")
@click.option("--notes", default="", help="추가 지시 (예: '한국 독자 대상')")
@click.option(
    "--out",
    type=click.Path(path_type=Path),
    default=None,
    help="outline 저장 경로 (JSON, 기본: topic-slug.json)",
)
@click.option("--model", default="qwen2.5:7b", help="Ollama 모델명")
def research_cmd(
    topic: str,
    sources: tuple[str, ...],
    keyword: str,
    intent: str,
    language: str,
    target_length: int,
    notes: str,
    out: Path | None,
    model: str,
) -> None:
    """URL/PDF source → outline 자동 생성 (LLM + fair use).

    TOPIC: 작성할 글 주제
    """
    if not sources:
        click.echo("[!] --source 최소 1개 필요 (URL 또는 PDF 경로)", err=True)
        sys.exit(1)

    # 1) source 분류 (URL vs PDF)
    refs: list[SourceRef] = []
    for src in sources:
        src_str = str(src).strip()
        if src_str.startswith("http://") or src_str.startswith("https://"):
            refs.append(SourceRef.from_url(src_str, locale=language))
        elif Path(src_str).is_file():
            refs.append(SourceRef.from_path(src_str, locale=language))
        else:
            click.echo(f"[!] 알 수 없는 source 형식 (skip): {src_str}", err=True)
            continue

    if not refs:
        click.echo("[!] 유효한 source 없음", err=True)
        sys.exit(1)

    # 2) source 추출
    click.echo(f"Source 추출 중... ({len(refs)}개)")
    extracted = ingest_sources(refs)
    if not extracted:
        click.echo("[!] 모든 source 추출 실패", err=True)
        sys.exit(1)

    # 3) LLM 호출
    click.echo(f"LLM으로 outline 생성 중... (model={model}, language={language})")
    client = _get_client(model)
    researcher = Researcher(client)

    ctx = ResearchContext(
        topic=topic,
        keyword=keyword,
        intent=intent,
        sources=extracted,
        language=language,
        target_length=target_length,
        notes=notes,
    )
    try:
        outline = researcher.research(ctx)
    except Exception as e:
        click.echo(f"[!] Research 실패: {e}", err=True)
        sys.exit(1)

    # 4) 저장
    out_path = out or Path(f"{_slugify_filename(topic)}.outline.json")
    out_data = {
        "topic": topic,
        "keyword": keyword,
        "intent": intent,
        "language": language,
        "sources_used": len(extracted),
        "outline": outline.to_dict(),
    }
    out_path.write_text(
        json.dumps(out_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    click.echo(f"\n[OK] outline 저장: {out_path}")
    click.echo(f"    title: {outline.title}")
    click.echo(f"    H2 sections: {len(outline.outline)}")
    click.echo(f"    FAQ: {len(outline.faq)}")
    click.echo(f"    Key takeaways: {len(outline.key_takeaways)}")
    click.echo("\n다음 단계: chunked-generator 또는 publish-md 로 사용")


def _slugify_filename(text: str) -> str:
    """파일명용 slug (영숫자+하이픈)."""
    import re as _re
    s = text.lower().strip()
    s = _re.sub(r"[^a-z0-9가-힣\s\-]", "", s)
    s = _re.sub(r"[\s_]+", "-", s)
    s = _re.sub(r"-+", "-", s)
    return s.strip("-")[:80] or "outline"


__all__ = ["ingest_url_cmd", "ingest_pdf_cmd", "research_cmd"]
