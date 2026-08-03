"""One-off K: v0.8 제휴마케팅 통합 데모 (Amazon Associates 시뮬레이션).

v0.8 핵심:
- JSON-LD schema 자동 주입 (Article + FAQ + Breadcrumb)
- Amazon affiliate link 자동 생성 + FTC disclosure
- chunked에 inject_schema + inject_affiliate 옵션

테스트 시나리오:
- 가짜 Amazon ASIN 1개 (실제 제휴 tag는 placeholder)
- pillar body 끝에 JSON-LD 자동 삽입
- chunk body에 Amazon affiliate 링크 + (paid link) disclosure

Usage:
    cd D:\\Google_blog\\wp-auto
    .venv\\Scripts\\python.exe -u oneoff_chunked_k_affiliate.py
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

CJK_REPLACEMENTS = {"人物": "인물", "代表": "대표"}


def clean_cjk(text: str) -> str:
    for old, new in CJK_REPLACEMENTS.items():
        text = text.replace(old, new)
    return text


def now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def log(msg: str) -> None:
    print(f"[{now()}] {msg}", flush=True)


def count_features(html: str) -> dict:
    return {
        "has_hook": "wp-auto-hook" in html,
        "has_cta": "wp-auto-cta" in html,
        "has_tldr": "wp-auto-tldr" in html,
        "has_related": "wp-auto-related" in html,
        "has_eeat": "wp-auto-eeat" in html,
        "has_image": "<img" in html,
        "has_jsonld": "application/ld+json" in html,
        "has_faq_schema": "FAQPage" in html,
        "has_article_schema": '"Article"' in html or "'Article'" in html,
        "has_breadcrumb_schema": "BreadcrumbList" in html,
        "has_affiliate_disclosure": "Amazon Associate" in html or "qualifying purchases" in html,
        "has_paid_link": "(paid link)" in html,
    }


# 데모용 Amazon affiliate product (ASIN은 placeholder, 실제 사용 시 본인 ASIN)
DEMO_AFFILIATE_PRODUCT = {
    "asin": "B0CHWRXH8B",  # 예시: Apple AirPods Pro 2 ASIN
    "anchor": "Amazon에서 제품 보기",
    "disclosure": "(paid link)",
    "position": "end",
    "price": 329.0,
    "currency": "USD",
    "rating": 4.5,
    "review_count": 1247,
}


def main() -> None:
    t_start = time.time()
    log("===== K: v0.8 제휴마케팅 통합 (Amazon Affiliates + JSON-LD) =====")
    log(f"OLLAMA_MODEL = {os.environ.get('OLLAMA_MODEL')}")

    # 1. RSS fetch
    RSS_URL = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
    log("[1/6] Fetching Google News KR RSS...")
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
    pub_date_short = pub_date[:10] if pub_date and len(pub_date) >= 10 else "2026-08-04"
    keyword = " ".join(title.split()[:3]) if len(title.split()) >= 3 else title

    log(f"  → random: {title[:70]}")
    log(f"  → source: {source_name}  ({pub_date})")

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
    log(f"  ✓ outline: '{outline.title}' ({time.time()-t:.1f}s)")

    # 3. Pillar-cluster (v0.8: schema + affiliate ON)
    chunked_gen = ChunkedContentGenerator(
        client, chunk_chars=300, target_chunks=4, style="trend",
        verify_links=True, optimize_structure=True,
        author_name="1인 운영자 (AI-assisted)",
        inject_schema=True,         # v0.8 NEW: JSON-LD 자동
        inject_affiliate=True,      # v0.8 NEW: FTC disclosure
        affiliate_network="amazon",
        affiliate_tag="myblog-20",  # 데모용 tag (실제 본인 tag로 교체)
        site_name="My WordPress Blog",
        site_url="https://myblog.example.com",
    )
    log("[3/6] Pillar-cluster (ko, v0.8 full ON)...")
    t = time.time()
    try:
        cluster = chunked_gen.generate_pillar_cluster(outline, language="ko", target_chunks=4)
        cluster.pillar.body_html = clean_cjk(cluster.pillar.body_html)
        for ch in cluster.chunks:
            ch.body_html = clean_cjk(ch.body_html)
    except Exception as e:
        log(f"  [ERROR] {e}")
        sys.exit(1)
    t_cluster = time.time() - t
    log(f"  ✓ pillar: '{cluster.pillar.title[:50]}'")
    log(f"  ✓ {len(cluster.chunks)} chunks: " + ", ".join(c.title[:20] for c in cluster.chunks))
    log(f"  ✓ cluster done in {t_cluster:.1f}s")

    # 4. Affiliate 링크 + disclosure (chunk body에 inject)
    log("[4/6] Injecting Amazon affiliate + FTC disclosure...")
    from wp_auto.ai.affiliate_linker import AffiliateLinker
    linker = AffiliateLinker(network="amazon", amazon_tag="myblog-20", language="ko")

    # chunk 1개에만 affiliate 링크 (너무 많으면 비자연스러움)
    target_chunk = cluster.chunks[0]  # 첫 chunk에
    new_body = linker.inject_into_chunk(
        target_chunk.body_html,
        products=[DEMO_AFFILIATE_PRODUCT],
        add_top_disclosure=True,
    )
    target_chunk.body_html = new_body
    log(f"  ✓ Affiliate link injected into chunk[0]: '{target_chunk.title[:30]}'")
    log(f"  ✓ FTC disclosure added (Amazon Associate)")

    # 5. Single mode
    log("[5/6] Mode A: SINGLE...")
    single_html = cluster.stitch_single()
    single_feats = count_features(single_html)
    log(f"  ✓ single features: {single_feats}")
    single_path = RESULTS_DIR / "K_single.html"
    single_path.write_text(single_html, encoding="utf-8")
    log(f"  ✓ saved: {single_path.name}")
    single_id = None
    try:
        async def _pub_single():
            wp = get_wp_client()
            return await wp.create_draft(
                title=cluster.topic,
                content=single_html,
                slug=("k-affiliate-single-" + cluster.topic.replace(" ", "-"))[:50] or "k-affiliate-single",
                excerpt=cluster.pillar.meta_description,
                status="draft",
            )
        single_id = asyncio.run(_pub_single())
        log(f"  ✓ published: WP #{single_id}")
    except Exception as e:
        log(f"  [WARN] single publish failed: {e}")

    # 6. Cluster mode
    log("[6/6] Mode B: PILLAR-CLUSTER...")
    cluster_specs = cluster.to_wp_post_specs()
    cluster_ids: list[int] = []
    try:
        async def _pub_cluster():
            wp = get_wp_client()
            ids = []
            for i, spec in enumerate(cluster_specs):
                spec = dict(spec)
                spec["slug"] = f"k-affiliate-c-{i}-" + spec["slug"][:30]
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
        (RESULTS_DIR / f"K_cluster_{i+1}.html").write_text(spec["content"], encoding="utf-8")

    log(f"  ✓ {len(cluster_specs)} posts: WP {cluster_ids}")

    # 결과 JSON
    elapsed = time.time() - t_start
    result = {
        "scenario": "K_v8_affiliate",
        "language": "ko",
        "style": "trend",
        "version": "v0.8",
        "verify_links": True,
        "optimize_structure": True,
        "inject_schema": True,
        "inject_affiliate": True,
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
        },
        "affiliate": {
            "asin": DEMO_AFFILIATE_PRODUCT["asin"],
            "tag": "myblog-20",
            "url": f"https://www.amazon.com/dp/{DEMO_AFFILIATE_PRODUCT['asin']}?tag=myblog-20&linkCode=ogi&th=1",
        },
        "single_mode": {"html_chars": len(single_html), "wp_id": single_id},
        "cluster_mode": {
            "n_posts": len(cluster_specs),
            "wp_ids": cluster_ids,
        },
        "html_files": {
            "single": str(single_path.name),
            "cluster": [f"K_cluster_{i+1}.html" for i in range(len(cluster_specs))],
        },
    }
    result_path = RESULTS_DIR / "K_affiliate_result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"  ✓ result JSON: {result_path.name}")
    log(f"⏱  Total: {elapsed:.1f}s ({elapsed/60:.1f}분)")


if __name__ == "__main__":
    main()
