"""One-off H: deep_dive v2 시연 (verify_links + optimize_structure ON, ko 4 chunks).

F (deep_dive v1)와 비교: link verification + structure optimization 추가.
- 외부 link 자동 검증
- E-E-A-T footer
- TL;DR + related articles
- nut graf

Usage:
    cd D:\\Google_blog\\wp-auto
    .venv\\Scripts\\python.exe -u oneoff_chunked_h_deep_dive_v2.py
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

from wp_auto.ai.chunked_generator import ChunkedContentGenerator  # noqa: E402
from wp_auto.ai.content_generator import ContentGenerator  # noqa: E402
from wp_auto.ai.ollama_client import OllamaClient  # noqa: E402
from wp_auto.wp.factory import get_wp_client  # noqa: E402

RESULTS_DIR = WP_AUTO / "oneoff" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def log(msg: str) -> None:
    print(f"[{now()}] {msg}", flush=True)


def count_features(html: str) -> dict:
    return {
        "internal_links": len(re.findall(r'<a\s+href="([^"]+)"', html)) - len(
            re.findall(r'<a\s+href="https?://', html)
        ),
        "external_links": len(re.findall(r'<a\s+href="https?://[^"]+"', html)),
        "has_hook": "wp-auto-hook" in html,
        "has_cta": "wp-auto-cta" in html,
        "has_tldr": "wp-auto-tldr" in html,
        "has_related": "wp-auto-related" in html,
        "has_eeat": "wp-auto-eeat" in html,
        "has_faq_details": html.count("<details") + html.count("<summary"),
    }


def main() -> None:
    t_start = time.time()
    log("===== H: deep_dive v2 (verify + optimize ON) =====")
    log(f"OLLAMA_MODEL = {os.environ.get('OLLAMA_MODEL')}")

    # 1. RSS fetch
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

    # 2. Outline
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

    # 3. Pillar-cluster (deep_dive v2)
    chunked_gen = ChunkedContentGenerator(
        client, chunk_chars=300, target_chunks=4, style="deep_dive",
        verify_links=True, optimize_structure=True, author_name="1인 운영자 (AI-assisted)",
    )
    log("[3/5] Pillar-cluster (ko, deep_dive v2, target=4)...")
    t = time.time()
    try:
        cluster = chunked_gen.generate_pillar_cluster(outline, language="ko", target_chunks=4)
    except Exception as e:
        log(f"  [ERROR] {e}")
        sys.exit(1)
    t_cluster = time.time() - t
    log(f"  ✓ pillar: '{cluster.pillar.title[:50]}'")
    log(f"  ✓ {len(cluster.chunks)} chunks: " + ", ".join(c.title[:20] for c in cluster.chunks))
    log(f"  ✓ cluster done in {t_cluster:.1f}s")

    # 4. Single mode
    log("[4/5] Mode A: SINGLE...")
    single_html = cluster.stitch_single()
    single_feats = count_features(single_html)
    single_path = RESULTS_DIR / "H_single.html"
    single_path.write_text(single_html, encoding="utf-8")
    log(f"  ✓ single HTML: {len(single_html):,}자, {single_feats}")
    log(f"  ✓ file={single_path.name}")
    single_id = None
    try:
        async def _pub_single():
            wp = get_wp_client()
            return await wp.create_draft(
                title=cluster.topic,
                content=single_html,
                slug=("h-deepv2-single-" + cluster.topic.replace(" ", "-"))[:50] or "h-deepv2-single",
                excerpt=cluster.pillar.meta_description,
                status="draft",
            )
        single_id = asyncio.run(_pub_single())
        log(f"  ✓ published: WP #{single_id}")
    except Exception as e:
        log(f"  [WARN] single publish failed: {e}")

    # 5. Cluster mode
    log("[5/5] Mode B: PILLAR-CLUSTER...")
    cluster_specs = cluster.to_wp_post_specs()
    cluster_ids: list[int] = []
    try:
        async def _pub_cluster():
            wp = get_wp_client()
            ids = []
            for i, spec in enumerate(cluster_specs):
                spec = dict(spec)
                spec["slug"] = f"h-deepv2-c-{i}-" + spec["slug"][:30]
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
        (RESULTS_DIR / f"H_cluster_{i+1}.html").write_text(spec["content"], encoding="utf-8")

    cluster_total_chars = sum(len(s["content"]) for s in cluster_specs)
    avg_internal = sum(count_features(s["content"])["internal_links"] for s in cluster_specs) / max(len(cluster_specs), 1)
    log(f"  ✓ {len(cluster_specs)} posts: WP {cluster_ids}")
    log(f"  ✓ total chars: {cluster_total_chars:,}, avg internal: {avg_internal:.1f}")

    # 결과 JSON
    elapsed = time.time() - t_start
    result = {
        "scenario": "H_deep_dive_v2_ko",
        "language": "ko",
        "style": "deep_dive",
        "version": "v2",
        "verify_links": True,
        "optimize_structure": True,
        "target_chunks": 4,
        "rss_topic": title,
        "rss_source": source_name,
        "outline_title": outline.title,
        "n_chunks": len(cluster.chunks),
        "chunk_titles": [c.title for c in cluster.chunks],
        "pillar_title": cluster.pillar.title,
        "timing_sec": {
            "total": round(elapsed, 1),
            "cluster_generation": round(t_cluster, 1),
        },
        "structure_features": {
            "single": single_feats,
            "pillar": count_features(cluster.pillar.body_html),
            "avg_chunk": {
                "has_eeat": sum(1 for c in cluster.chunks if "wp-auto-eeat" in c.body_html) / max(len(cluster.chunks), 1),
                "has_cta": sum(1 for c in cluster.chunks if "wp-auto-cta" in c.body_html) / max(len(cluster.chunks), 1),
            },
        },
        "single_mode": {
            "html_chars": len(single_html),
            "wp_id": single_id,
        },
        "cluster_mode": {
            "n_posts": len(cluster_specs),
            "total_html_chars": cluster_total_chars,
            "avg_internal_links": round(avg_internal, 1),
            "wp_ids": cluster_ids,
        },
        "html_files": {
            "single": str(single_path.name),
            "cluster": [f"H_cluster_{i+1}.html" for i in range(len(cluster_specs))],
        },
    }
    result_path = RESULTS_DIR / "H_deepv2_result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"  ✓ result JSON: {result_path.name}")
    log(f"⏱  Total: {elapsed:.1f}s ({elapsed/60:.1f}분)")


if __name__ == "__main__":
    main()
