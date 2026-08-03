"""One-off D: 큰 chunk (8 chunks) 시나리오.

시나리오:
1. Google News KR RSS → random pick
2. Outline (ko) → qwen2.5:3b
3. Pillar-cluster (ko) — plan을 8 subtopic으로 truncate (확장)
4. Mode A: single HTML → 1 WP post
5. Mode B: pillar-cluster → 9 WP posts (pillar + 8 chunks)
6. 결과 JSON + HTML 파일 저장

Usage:
    cd D:\\Google_blog\\wp-auto
    .venv\\Scripts\\python.exe -u oneoff_chunked_d_long.py
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"

WP_AUTO = Path(r"D:\Google_blog\wp-auto")
sys.path.insert(0, str(WP_AUTO))

env_path = WP_AUTO / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").split("\n"):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

import httpx  # noqa: E402

from wp_auto.ai.chunked_generator import ChunkedContentGenerator, PillarCluster  # noqa: E402
from wp_auto.ai.content_generator import ContentGenerator  # noqa: E402
from wp_auto.ai.ollama_client import OllamaClient  # noqa: E402
from wp_auto.wp.factory import get_wp_client  # noqa: E402

RESULTS_DIR = WP_AUTO / "oneoff" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

MAX_CHUNKS = 8  # 큰 chunk 시나리오


def now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def log(msg: str) -> None:
    print(f"[{now()}] {msg}", flush=True)


def count_internal_links(html: str) -> int:
    links = re.findall(r'<a\s+href="([^"]+)"', html)
    return sum(1 for l in links if not l.startswith("http"))


def main() -> None:
    t_start = time.time()
    log(f"===== D: Long chunk (max {MAX_CHUNKS} chunks, ko) =====")
    log(f"OLLAMA_MODEL = {os.environ.get('OLLAMA_MODEL')}")

    # 1. RSS fetch (Korean)
    RSS_URL = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
    log("[1/5] Fetching Google News KR RSS...")
    try:
        resp = httpx.get(RSS_URL, timeout=15.0, follow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        log(f"  [ERROR] {e}")
        sys.exit(1)
    root = ET.fromstring(resp.text)
    items = root.findall(".//item")
    log(f"  ✓ {len(items)} news items")

    selected = random.choice(items)
    import html as html_lib
    title = html_lib.unescape((selected.find("title").text or "").strip())
    if " - " in title:
        title = title.rsplit(" - ", 1)[0]
    source_el = selected.find("source")
    source_name = html_lib.unescape(source_el.text) if source_el is not None else "?"
    pub_date = selected.find("pubDate")
    pub_date = pub_date.text if pub_date is not None else "?"
    keyword = " ".join(title.split()[:3]) if len(title.split()) >= 3 else title

    log(f"  → random: {title[:70]}")
    log(f"  → source: {source_name}  ({pub_date})")
    log(f"  → keyword: {keyword}")

    # 2. Outline (ko)
    client = OllamaClient(
        model=os.environ.get("OLLAMA_MODEL", "qwen2.5:3b"),
        timeout=600.0,
    )
    outline_gen = ContentGenerator(client)
    log("[2/5] Outline (ko)...")
    t = time.time()
    try:
        outline = outline_gen.generate_outline(
            topic=title, keyword=keyword, intent="informational", length=600, language="ko"
        )
    except Exception as e:
        log(f"  [ERROR] {e}")
        sys.exit(1)
    log(f"  ✓ outline: '{outline.title}' ({time.time()-t:.1f}s, {len(outline.outline)} H2)")

    # 3. Pillar-cluster (ko) - plan → truncate to MAX_CHUNKS
    chunked_gen = ChunkedContentGenerator(client, chunk_chars=300)
    log(f"[3/5] Pillar-cluster (ko, max {MAX_CHUNKS} chunks)...")
    t = time.time()
    try:
        all_subtopics = chunked_gen.plan_subtopics(outline, language="ko")
        log(f"  ✓ plan returned {len(all_subtopics)} subtopics, truncating to {MAX_CHUNKS}")
        subtopics = all_subtopics[:MAX_CHUNKS]
        chunks = chunked_gen.generate_chunks(outline, subtopics, language="ko")
        pillar = chunked_gen.generate_pillar(outline, subtopics, chunks, language="ko")
        cluster = PillarCluster(
            pillar=pillar,
            chunks=chunks,
            topic=outline.title,
            keyword=outline.title,
            language="ko",
            category="chunked-ko-long",
        )
    except Exception as e:
        log(f"  [ERROR] {e}")
        sys.exit(1)
    t_cluster = time.time() - t
    log(f"  ✓ pillar: '{cluster.pillar.title[:50]}'")
    log(f"  ✓ {len(cluster.chunks)} chunks: " + ", ".join(c.title[:20] for c in cluster.chunks))
    log(f"  ✓ cluster done in {t_cluster:.1f}s")

    # 4. Mode A: single (stitch)
    log("[4/5] Mode A: SINGLE (1 WP post, all chunks stitched)...")
    single_html = cluster.stitch_single()
    single_internal_links = count_internal_links(single_html)
    single_path = RESULTS_DIR / "D_single.html"
    single_path.write_text(single_html, encoding="utf-8")
    log(f"  ✓ single HTML: {len(single_html):,}자, internal links: {single_internal_links}, file={single_path.name}")
    single_id = None
    try:
        async def _pub_single():
            wp = get_wp_client()
            return await wp.create_draft(
                title=cluster.topic,
                content=single_html,
                slug=("d-long-single-" + cluster.topic.replace(" ", "-"))[:50] or "d-long-single",
                excerpt=cluster.pillar.meta_description,
                status="draft",
            )
        single_id = asyncio.run(_pub_single())
        log(f"  ✓ published: WP #{single_id}")
    except Exception as e:
        log(f"  [WARN] single publish failed: {e}")

    # 5. Mode B: pillar-cluster (N+1 posts)
    log("[5/5] Mode B: PILLAR-CLUSTER (1 pillar + N chunks = N+1 WP posts)...")
    cluster_specs = cluster.to_wp_post_specs()
    cluster_ids: list[int] = []
    try:
        async def _pub_cluster():
            wp = get_wp_client()
            ids = []
            for i, spec in enumerate(cluster_specs):
                spec = dict(spec)
                spec["slug"] = f"d-long-c-{i}-" + spec["slug"][:30]
                pid = await wp.create_draft(
                    title=spec["title"],
                    content=spec["content"],
                    slug=spec["slug"],
                    excerpt=spec["excerpt"],
                    status="draft",
                )
                ids.append(pid)
            return ids
        cluster_ids = asyncio.run(_pub_cluster())
    except Exception as e:
        log(f"  [WARN] cluster publish failed: {e}")

    for i, spec in enumerate(cluster_specs):
        (RESULTS_DIR / f"D_cluster_{i+1}.html").write_text(spec["content"], encoding="utf-8")

    total_cluster_html = sum(len(s["content"]) for s in cluster_specs)
    avg_internal_links = sum(count_internal_links(s["content"]) for s in cluster_specs) / max(len(cluster_specs), 1)
    log(f"  ✓ {len(cluster_specs)} posts published: WP {cluster_ids}")
    log(f"  ✓ total HTML: {total_cluster_html:,}자, avg internal links/post: {avg_internal_links:.1f}")

    # 결과 JSON 저장
    elapsed = time.time() - t_start
    result = {
        "scenario": "D_long_chunk_ko",
        "language": "ko",
        "max_chunks": MAX_CHUNKS,
        "rss_topic": title,
        "rss_source": source_name,
        "outline_title": outline.title,
        "n_chunks": len(cluster.chunks),
        "chunk_titles": [c.title for c in cluster.chunks],
        "pillar_title": cluster.pillar.title,
        "timing_sec": {
            "outline": round(time.time() - t_start, 1),
            "cluster_generation": round(t_cluster, 1),
            "total": round(elapsed, 1),
        },
        "single_mode": {
            "html_chars": len(single_html),
            "internal_links": single_internal_links,
            "wp_id": single_id,
        },
        "cluster_mode": {
            "n_posts": len(cluster_specs),
            "total_html_chars": total_cluster_html,
            "avg_internal_links": round(avg_internal_links, 1),
            "wp_ids": cluster_ids,
        },
        "html_files": {
            "single": str(single_path.name),
            "cluster": [f"D_cluster_{i+1}.html" for i in range(len(cluster_specs))],
        },
    }
    result_path = RESULTS_DIR / "D_long_result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"  ✓ result JSON: {result_path.name}")
    log(f"⏱  Total: {elapsed:.1f}s ({elapsed/60:.1f}분)")


if __name__ == "__main__":
    main()
