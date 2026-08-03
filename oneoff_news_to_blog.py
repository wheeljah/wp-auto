"""One-off: Google News Korea → random → qwen2.5:7b → MockWP publish.

End-to-end demo of the wp-auto content pipeline.
한국 뉴스 RSS에서 랜덤 1개 선택 → 한국어 블로그 글 생성 → 점수 평가 → MockWP draft 게시.

Usage:
    cd D:\\Google_blog\\wp-auto
    .venv\\Scripts\\python.exe oneoff_news_to_blog.py
"""

from __future__ import annotations

import asyncio
import os
import random
import sys
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

# UTF-8 강제
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"

# wp-auto 경로 추가
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

import httpx

from wp_auto.ai.ollama_client import OllamaClient
from wp_auto.ai.content_generator import ContentGenerator
from wp_auto.wp.factory import get_wp_client


def now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def main() -> None:
    t_start = datetime.now()
    print(f"[{now()}] ===== One-off news → blog workflow =====")
    print(f"[{now()}] OLLAMA_MODEL = {os.environ.get('OLLAMA_MODEL', '(default)')}")
    print(f"[{now()}] OLLAMA_HOST = {os.environ.get('OLLAMA_HOST', '(default)')}")
    print(f"[{now()}] WP_MOCK = {os.environ.get('WP_MOCK', 'true')}")

    # 1. RSS fetch
    RSS_URL = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
    print(f"\n[{now()}] [1/5] Fetching Google News Korea RSS...")
    try:
        resp = httpx.get(RSS_URL, timeout=15.0, follow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERROR] RSS fetch failed: {e}")
        sys.exit(1)

    root = ET.fromstring(resp.text)
    items = root.findall(".//item")
    print(f"[{now()}]   Found {len(items)} news items")
    if not items:
        print("[ERROR] No items in feed")
        sys.exit(1)

    # 2. Random pick
    selected = random.choice(items)
    title = (selected.find("title").text or "").strip()
    link = (selected.find("link").text or "").strip()
    source_el = selected.find("source")
    source_name = source_el.text if source_el is not None else "Unknown"
    pub_date_el = selected.find("pubDate")
    pub_date = pub_date_el.text if pub_date_el is not None else "?"

    # Strip " - 출처명" suffix from Google News titles
    if " - " in title:
        clean_title, src = title.rsplit(" - ", 1)
        title = clean_title
    # Strip HTML entities
    import html
    title = html.unescape(title)
    source_name = html.unescape(source_name)

    keyword = " ".join(title.split()[:3]) if len(title.split()) >= 3 else title
    length = 600   # 3B는 빠름, 600자 = ~900 tokens → 1-3분

    print(f"\n[{now()}] [2/5] Random pick:")
    print(f"  Title : {title[:80]}")
    print(f"  Source: {source_name} ({pub_date})")
    print(f"  Keyword: {keyword}")
    print(f"  Length: {length}자")

    # 3. Generate
    client = OllamaClient(
        model=os.environ.get("OLLAMA_MODEL", "qwen2.5:3b"),
        timeout=600.0,  # 3B는 빠르지만 안전 마진 (원래 300)
    )
    gen = ContentGenerator(client, min_score=75.0, max_iterations=2)

    # 3a. Outline
    print(f"\n[{now()}] [3/5] Generating outline (ko)...")
    t = datetime.now()
    try:
        outline = gen.generate_outline(
            topic=title, keyword=keyword, intent="informational", length=length, language="ko"
        )
    except Exception as e:
        print(f"[ERROR] outline failed: {e}")
        sys.exit(1)
    print(f"[{now()}]   ✓ outline: '{outline.title}' ({(datetime.now()-t).total_seconds():.1f}s)")

    # 3b. Draft
    print(f"\n[{now()}] [4/5] Generating draft HTML (ko, {length}자 target)...")
    t = datetime.now()
    try:
        html = gen.generate_draft(
            outline, keyword=keyword, tone="친근한 전문가", length=length, language="ko"
        )
    except Exception as e:
        print(f"[ERROR] draft failed: {e}")
        sys.exit(1)
    print(
        f"[{now()}]   ✓ draft {len(html)}자 생성 ({(datetime.now()-t).total_seconds():.1f}s)"
    )
    # Show preview
    preview = html[:200].replace("\n", " ")
    print(f"   preview: {preview}…")

    # 3c. Score
    print(f"\n[{now()}] [5/5] Scoring + Publishing to MockWP...")
    score_info = None
    try:
        from wp_auto.core.content_score import SpecializedContentOptimizer

        optimizer = SpecializedContentOptimizer()
        result = optimizer.verify_html(html, focus_keyword=keyword)
        score_info = {
            "total_score": result.total_score,
            "level": result.level.value,
            "feedback": result.feedback,
            "recommendations": result.recommendations,
        }
        print(
            f"[{now()}]   ✓ score: {result.total_score:.1f}/100 ({result.level.value})"
        )
        if result.recommendations:
            print(f"     top recs: {result.recommendations[:2]}")
    except Exception as e:
        print(f"[WARN] score failed (skipping): {e}")

    # 4. Publish to MockWP
    async def _publish():
        wp = get_wp_client()
        post_id = await wp.create_draft(
            title=outline.title,
            content=html,
            slug=outline.slug or "wp-auto-news",
            excerpt=outline.meta_description,
            status="draft",
        )
        return await wp.get_post(post_id)

    t = datetime.now()
    try:
        post = asyncio.run(_publish())
    except Exception as e:
        print(f"[ERROR] WP publish failed: {e}")
        sys.exit(1)
    print(
        f"[{now()}]   ✓ WP draft #{post.id} ({(datetime.now()-t).total_seconds():.1f}s)"
    )

    # 5. Summary
    elapsed = (datetime.now() - t_start).total_seconds()
    print(f"\n{'='*60}")
    print(f"  News     : {title[:80]}")
    print(f"  Source   : {source_name} ({pub_date})")
    print(f"  Link     : {link[:80]}")
    print(f"  Post     : {outline.title}")
    print(f"  Keyword  : {keyword}")
    print(f"  Score    : {score_info['total_score']:.1f}/100 ({score_info['level']})" if score_info else "  Score    : (skipped)")
    print(f"  WP ID    : #{post.id}")
    print(f"  WP URL   : {post.url}")
    print(f"  HTML len : {len(html)}자")
    print(f"  Total    : {elapsed:.1f}s ({elapsed/60:.1f}분)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
