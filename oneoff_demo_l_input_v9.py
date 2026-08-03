"""시연 L: URL/PDF + markdown 입력 end-to-end (v0.9 신규 기능).

시연 시나리오:
1. L1: 작성한 markdown (`oneoff/sample_l_input.md`) → publish-md (cluster mode, Mock WP)
2. L2: 외부 URL (한국경제 또는 위키피디아) → ingest-url → key facts 추출

각 단계에서:
- mock WP DB에 publish → list-posts로 확인
- elapsed time 측정

v0.9 신규 모듈:
- wp_auto.ai.source_ingestor (Trafilatura + PyMuPDF)
- wp_auto.ai.researcher (source → outline, fair use 준수)
- wp_auto.ai.markdown_loader (markdown → cluster)
- wp_auto.cli.ingest (ingest-url, ingest-pdf, research)
- wp_auto.cli.publish_md (publish-md)
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Windows UTF-8
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"

# loguru stderr redirect (PowerShell cp949 깨짐 방지)
import sys as _sys
from loguru import logger as _logger
_logger.remove()
_logger.add(_sys.stdout, level="WARNING", format="{message}")

# .env 자동 로드 (chunked 시연 스크립트들과 동일 DB_PATH)
WP_AUTO = Path(r"D:\Google_blog\wp-auto")
env_path = WP_AUTO / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

# 모듈 import
from wp_auto.ai.source_ingestor import (
    ExtractedText,
    SourceRef,
    extract_key_facts,
    ingest_pdf,
    ingest_url,
)
from wp_auto.ai.markdown_loader import load_markdown, md_to_cluster

# 출력 경로
ONEFF_DIR = WP_AUTO / "oneoff"
SAMPLE_MD = ONEFF_DIR / "sample_l_input.md"
RESULTS_DIR = ONEFF_DIR / "results"


def section(title: str) -> None:
    """섹션 구분선 출력."""
    print("\n" + "=" * 70, flush=True)
    print(f"  {title}", flush=True)
    print("=" * 70, flush=True)


def elapsed(start: float) -> str:
    """경과 시간."""
    return f"{time.time() - start:.1f}s"


async def demo_l1_markdown_publish() -> None:
    """L1: 직접 작성 markdown → publish-md (cluster mode)."""
    section("L1: 직접 작성 markdown → publish-md (cluster mode)")

    if not SAMPLE_MD.is_file():
        print(f"[!] 샘플 markdown 없음: {SAMPLE_MD}", flush=True)
        return

    print(f"  Input: {SAMPLE_MD}", flush=True)

    # 1) markdown 로드
    start = time.time()
    post = load_markdown(SAMPLE_MD)
    print(f"  로드: {elapsed(start)}", flush=True)
    print(f"    Title: {post.title}", flush=True)
    print(f"    Sections: {len(post.sections)}", flush=True)
    print(f"    Language: {post.language}", flush=True)
    print(f"    Tags: {post.frontmatter.tags}", flush=True)
    print(f"    Categories: {post.frontmatter.categories}", flush=True)

    # 2) chunked cluster 변환
    start = time.time()
    cluster = md_to_cluster(post, language=post.language)
    print(f"  cluster 변환: {elapsed(start)}", flush=True)
    print(f"    Pillar: {cluster.pillar.title[:50]}", flush=True)
    print(f"    Chunks: {len(cluster.chunks)}", flush=True)

    # 3) WP publish (mock)
    start = time.time()
    from wp_auto.wp.factory import get_wp_client
    client = get_wp_client()
    post_ids = []

    # pillar 먼저
    pid = await client.create_draft(
        title=cluster.pillar.title,
        content=cluster.pillar.body_html,
        slug=cluster.pillar.slug,
        excerpt=cluster.pillar.meta_description,
        status="draft",
    )
    post_ids.append(("pillar", pid))
    print(f"    Pillar → post_id={pid}", flush=True)

    # chunks
    for i, ch in enumerate(cluster.chunks, 1):
        # chunk-nav HTML 추가
        content = ch.body_html
        nav_parts = ['<nav class="chunk-nav">']
        if ch.prev_slug:
            nav_parts.append(f'<a href="/{ch.prev_slug}">← 이전</a>')
        if ch.next_slug:
            nav_parts.append(f'<a href="/{ch.next_slug}">다음 →</a>')
        for r in ch.related_slugs:
            nav_parts.append(f'<a href="/{r}">{r}</a>')
        nav_parts.append('</nav>')
        content += "\n" + "\n".join(nav_parts)

        pid = await client.create_draft(
            title=ch.title,
            content=content,
            slug=ch.slug,
            excerpt=ch.meta_description,
            status="draft",
        )
        post_ids.append((f"chunk_{i}", pid))
        print(f"    Chunk {i} ({ch.title[:30]}...) → post_id={pid}", flush=True)

    print(f"  publish: {elapsed(start)}", flush=True)
    print(f"  [OK] {len(post_ids)}개 post 생성 완료", flush=True)

    return post_ids, cluster


async def demo_l2_url_ingest() -> tuple[ExtractedText, list[str]]:
    """L2: 외부 URL → ingest-url → key facts."""
    section("L2: 외부 URL → ingest-url → key facts")

    # 안정적인 URL 사용 (wikipedia, 위키백과 등)
    # 1차 출처 검증된 사이트
    test_urls = [
        "https://en.wikipedia.org/wiki/Affiliate_marketing",
    ]

    results = []
    for url in test_urls:
        print(f"  URL: {url}")
        start = time.time()
        try:
            ref = SourceRef.from_url(url, locale="en")
            extracted = ingest_url(ref, timeout=30)
            print(f"  추출: {elapsed(start)}")
            print(f"    Title: {extracted.title}")
            print(f"    Body: {len(extracted.body):,}자")
            print(f"    Language hint: {extracted.language_hint}")

            # key facts
            print(f"    Key facts ({len(extracted.key_facts)}개):")
            for i, f in enumerate(extracted.key_facts[:5], 1):
                # 80자만 표시
                display = f[:80] + "..." if len(f) > 80 else f
                print(f"      {i}. {display}")

            results.append((extracted, ref))
        except Exception as e:
            print(f"  [!] 추출 실패: {e}")

    if results:
        return results[0]
    return None, None


async def demo_l2b_korean_url() -> tuple[ExtractedText | None, SourceRef | None]:
    """L2b: 한국어 URL → ingest-url (성공/실패 모두 OK)."""
    section("L2b: 한국어 URL → ingest-url (선택)")

    # 한국어 안정 URL (위키백과)
    url = "https://ko.wikipedia.org/wiki/워드프레스"
    print(f"  URL: {url}")
    start = time.time()
    try:
        ref = SourceRef.from_url(url, locale="ko")
        extracted = ingest_url(ref, timeout=20)
        print(f"  추출: {elapsed(start)}")
        print(f"    Title: {extracted.title}")
        print(f"    Body: {len(extracted.body):,}자")
        print(f"    Key facts ({len(extracted.key_facts)}개):")
        for i, f in enumerate(extracted.key_facts[:5], 1):
            display = f[:80] + "..." if len(f) > 80 else f
            print(f"      {i}. {display}")
        return extracted, ref
    except Exception as e:
        print(f"  [!] 추출 실패 (skip 가능): {e}")
        return None, None


def save_results(md_post_ids, url_extracted) -> None:
    """시연 결과 저장."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result_path = RESULTS_DIR / "L_input_v9_result.json"

    data = {
        "demo": "L (v0.9 input features)",
        "L1_markdown_publish": {
            "input_file": str(SAMPLE_MD),
            "post_ids": md_post_ids,
        } if md_post_ids else None,
        "L2_url_ingest": None,
    }

    if url_extracted:
        data["L2_url_ingest"] = {
            "url": url_extracted.source.url,
            "title": url_extracted.title,
            "body_chars": len(url_extracted.body),
            "language_hint": url_extracted.language_hint,
            "key_facts_count": len(url_extracted.key_facts),
            "key_facts_sample": url_extracted.key_facts[:5],
        }

    result_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n[OK] 결과 저장: {result_path}")


async def main() -> None:
    print("\n>>> 시연 L: v0.9 입력 기능 (URL/PDF + markdown) end-to-end")
    print(">>> 모듈: source_ingestor + researcher + markdown_loader")
    print(">>> 1차 출처: Trafilatura F1 0.958, PyMuPDF 180 pages/sec\n", flush=True)

    # L1: markdown → publish
    md_result = await demo_l1_markdown_publish()

    # L2: URL → extract
    url_result, url_ref = await demo_l2_url_ingest()

    # L2b: 한국어 URL (선택)
    ko_url_result, ko_url_ref = await demo_l2b_korean_url()

    # 결과 저장 (sync — async chain 끝난 후)
    final_url = url_result if url_result else ko_url_result
    save_results(md_result, final_url)

    section("시연 L 완료")
    print("  ✓ L1: markdown → publish (cluster mode)", flush=True)
    print("  ✓ L2: URL → extract (Trafilatura)", flush=True)
    print("  ✓ L2b: 한국어 URL → extract (Wikipedia)", flush=True)
    print("\n다음: v0.9 commit + push", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
