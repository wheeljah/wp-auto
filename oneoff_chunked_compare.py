"""One-off: chunked news → blog (single vs pillar-cluster 비교).

End-to-end demo of the new ChunkedContentGenerator:
1. Google News Korea RSS → random pick
2. Outline 생성 (qwen2.5:3b)
3. Chunked cluster 생성 (plan + 4 chunks + pillar)
4. 모드 A: single — 모든 chunk를 1 HTML에 stitch → 1 WP post
5. 모드 B: pillar-cluster — pillar 1 + N chunks = N+1 WP posts
6. 비교 결과 출력 (시간, post 수, HTML 크기, 링크 수, score)

Usage:
    cd D:\\Google_blog\\wp-auto
    .venv\\Scripts\\python.exe -u oneoff_chunked_compare.py
"""

from __future__ import annotations

import asyncio
import os
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

# UTF-8 강제
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"

WP_AUTO = Path(r"D:\Google_blog\wp-auto")
sys.path.insert(0, str(WP_AUTO))

# .env 로드
env_path = WP_AUTO / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").split("\n"):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

import httpx  # noqa: E402

from wp_auto.ai.chunked_generator import ChunkedContentGenerator  # noqa: E402
from wp_auto.ai.content_generator import ContentGenerator  # noqa: E402
from wp_auto.ai.ollama_client import OllamaClient  # noqa: E402
from wp_auto.wp.factory import get_wp_client  # noqa: E402


def now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def log(msg: str) -> None:
    print(f"[{now()}] {msg}", flush=True)


def count_internal_links(html: str) -> int:
    """HTML 내 내부 링크 (<a href>) 개수 (외부 https://example.com 제외)."""
    links = re.findall(r'<a\s+href="([^"]+)"', html)
    return sum(1 for l in links if not l.startswith("http"))


def main() -> None:
    t_start = time.time()
    log("===== Chunked news: single vs pillar-cluster =====")
    log(f"OLLAMA_MODEL = {os.environ.get('OLLAMA_MODEL')}")
    log(f"WP_MOCK = {os.environ.get('WP_MOCK', 'true')}")

    # 1. RSS fetch
    RSS_URL = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
    log("[1/6] Fetching Google News Korea RSS...")
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

    # 2. Outline
    client = OllamaClient(
        model=os.environ.get("OLLAMA_MODEL", "qwen2.5:3b"),
        timeout=600.0,
    )
    outline_gen = ContentGenerator(client)
    log("[2/6] Outline (ko)...")
    t = time.time()
    try:
        outline = outline_gen.generate_outline(
            topic=title, keyword=keyword, intent="informational", length=600, language="ko"
        )
    except Exception as e:
        log(f"  [ERROR] {e}")
        sys.exit(1)
    log(f"  ✓ outline: '{outline.title}' ({time.time()-t:.1f}s, {len(outline.outline)} H2)")

    # 3. Chunked cluster
    chunked_gen = ChunkedContentGenerator(client, chunk_chars=300)
    log("[3/6] Pillar-cluster (plan + chunks + pillar)...")
    t = time.time()
    try:
        cluster = chunked_gen.generate_pillar_cluster(outline, language="ko")
    except Exception as e:
        log(f"  [ERROR] {e}")
        sys.exit(1)
    t_cluster = time.time() - t
    log(f"  ✓ pillar: '{cluster.pillar.title[:50]}'")
    log(f"  ✓ {len(cluster.chunks)} chunks: " + ", ".join(c.title[:20] for c in cluster.chunks))
    log(f"  ✓ cluster done in {t_cluster:.1f}s")

    # 4. 모드 A: single (stitch)
    log("[4/6] Mode A: SINGLE (1 WP post, all chunks stitched)...")
    single_html = cluster.stitch_single()
    single_internal_links = count_internal_links(single_html)
    single_id = None
    try:
        async def _pub_single():
            wp = get_wp_client()
            pid = await wp.create_draft(
                title=cluster.topic,
                content=single_html,
                slug=cluster.topic.replace(" ", "-")[:40] or "chunked",
                excerpt=cluster.pillar.meta_description,
                status="draft",
            )
            return pid
        single_id = asyncio.run(_pub_single())
    except Exception as e:
        log(f"  [WARN] single publish failed: {e}")
    log(f"  ✓ single HTML: {len(single_html):,}자, internal links: {single_internal_links}, WP #{single_id}")

    # 5. 모드 B: pillar-cluster (N+1 posts)
    log("[5/6] Mode B: PILLAR-CLUSTER (1 pillar + N chunks = N+1 WP posts)...")
    cluster_specs = cluster.to_wp_post_specs()
    cluster_ids: list[int] = []
    try:
        async def _pub_cluster():
            wp = get_wp_client()
            ids = []
            for spec in cluster_specs:
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
    total_cluster_html = sum(len(s["content"]) for s in cluster_specs)
    avg_internal_links = sum(count_internal_links(s["content"]) for s in cluster_specs) / max(len(cluster_specs), 1)
    log(f"  ✓ {len(cluster_specs)} posts published: WP {cluster_ids}")
    log(f"  ✓ total HTML: {total_cluster_html:,}자, avg internal links/post: {avg_internal_links:.1f}")

    # 6. 비교 결과
    log("[6/6] ===== COMPARISON =====")
    elapsed = time.time() - t_start
    print()
    print("┌─────────────────────┬──────────────────────┬─────────────────────────┐")
    print("│ Metric               │ A: SINGLE            │ B: PILLAR-CLUSTER       │")
    print("├─────────────────────┼──────────────────────┼─────────────────────────┤")
    print(f"│ WP posts created     │ {1:<20} │ {len(cluster_specs):<23} │")
    print(f"│ Total HTML (chars)   │ {len(single_html):<20,} │ {total_cluster_html:<23,} │")
    print(f"│ Internal links       │ {single_internal_links:<20} │ {avg_internal_links:<23.1f} │")
    print(f"│ Avg post size (chars)│ {len(single_html):<20,} │ {total_cluster_html // max(len(cluster_specs), 1):<23,} │")
    print(f"│ WP post IDs          │ {str(single_id):<20} │ {str(cluster_ids):<23} │")
    print("└─────────────────────┴──────────────────────┴─────────────────────────┘")
    print()
    print(f"📊 Generation: outline {t_cluster:.1f}s + 4 chunks + 1 pillar")
    print(f"⏱  Total: {elapsed:.1f}s ({elapsed/60:.1f}분)")
    print()
    print("📝 권장 (Google SEO pillar-cluster model):")
    print("   - 단일 post: 빠르게 발행, 내부 link 1개당 효과 적음")
    print("   - pillar-cluster: N+1개 post, 각 chunk별 link juice 공유, 부분 업데이트 용이")


if __name__ == "__main__":
    main()
