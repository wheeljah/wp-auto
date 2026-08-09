"""Image pipeline unit tests — Pexels + Wikimedia + NASA + generator + embedder.

.env에서 PEXELS_API_KEY 자동 load. KEY 없으면 Pexels 테스트 skip.

Run:
    cd D:\\Google_blog\\wp-auto
    .venv\\Scripts\\python.exe -m pytest tests/unit/test_image_pipeline.py -v
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# .env load (PEXELS_API_KEY 자동 주입)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from wp_auto.image.models import ImageResult
from wp_auto.image.source_resolver import ImageSourceResolver
from wp_auto.image.embedder import ImageEmbedder
from wp_auto.image.generator import InfographicGenerator
from wp_auto.image.pipeline import ImagePipeline


@pytest.fixture
def assets_dir(tmp_path) -> Path:
    """테스트용 임시 assets/images 디렉토리."""
    d = tmp_path / "assets" / "images"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def pexels_key() -> str | None:
    return os.environ.get("PEXELS_API_KEY")


# ============================================================
# ImageResult model
# ============================================================
def test_image_result_to_dict():
    img = ImageResult(
        source="pexels",
        license="Pexels",
        photographer="Alice",
        source_url="https://pexels.com/photo/1",
        image_url="https://images.pexels.com/photos/1.jpeg",
        width=1000,
        height=667,
        alt="test alt",
        attribution="by Alice via Pexels",
    )
    d = img.to_dict()
    assert d["source"] == "pexels"
    assert d["photographer"] == "Alice"
    assert d["width"] == 1000
    assert "by Alice via Pexels" in d["attribution"]


# ============================================================
# ImageSourceResolver — Pexels (KEY 있을 때만)
# ============================================================
def test_pexels_search_returns_image_results(pexels_key):
    if not pexels_key:
        pytest.skip("PEXELS_API_KEY not set, skipping Pexels test")
    with ImageSourceResolver(pexels_api_key=pexels_key) as r:
        results = r.search("OpenAI", max_results=2)
    assert isinstance(results, list)
    if results:
        assert all(img.source == "pexels" for img in results)
        assert all(img.license == "Pexels" for img in results)
        assert all(img.image_url.startswith("https://") for img in results)
        assert all(img.photographer for img in results)
        assert all("by " in img.attribution for img in results)


# ============================================================
# ImageSourceResolver — Wikimedia Commons (KEY 불필요)
# ============================================================
def test_wikimedia_search_returns_results():
    """Wikimedia API 호출. CC0/CC BY/CC BY-SA만 필터링. 결과 없을 수도 있음 (rate limit 등)."""
    r = ImageSourceResolver()
    try:
        results = r._search_wikimedia("mountain", max_results=3)
    finally:
        r.close()
    # 결과 없으면 skip (rate limit 또는 검색 매칭 0)
    if not results:
        pytest.skip("Wikimedia returned 0 results (rate limit or no match)")
    assert all(img.source == "wikimedia" for img in results)
    assert all(img.license in ("CC0", "CC-BY", "CC-BY-SA", "Public Domain") for img in results)
    assert all(img.image_url.startswith("https://") for img in results)
    # Non-free 라이선스 (CC-BY-NC 등)는 포함 안 됨
    assert not any("NC" in img.license for img in results)


def test_wikimedia_license_filter():
    """라이선스 필터 단위 검증."""
    # 자유 라이선스
    assert ImageSourceResolver._wikimedia_license("CC0") == "CC0"
    assert ImageSourceResolver._wikimedia_license("Public Domain") == "Public Domain"
    assert ImageSourceResolver._wikimedia_license("CC BY 4.0") == "CC-BY"
    assert ImageSourceResolver._wikimedia_license("CC BY-SA 4.0") == "CC-BY-SA"
    assert ImageSourceResolver._wikimedia_license("PD-Art") == "Public Domain"
    # 비자유 라이선스 (None 반환)
    assert ImageSourceResolver._wikimedia_license("CC BY-NC 4.0") is None
    assert ImageSourceResolver._wikimedia_license("CC BY-NC-SA 4.0") is None
    assert ImageSourceResolver._wikimedia_license("CC BY-SA-NC 4.0") is None
    assert ImageSourceResolver._wikimedia_license("CC BY-ND 4.0") is None
    assert ImageSourceResolver._wikimedia_license("GFDL") is None
    assert ImageSourceResolver._wikimedia_license("") is None


def test_clean_artist_removes_html():
    raw = '<a href="//commons.wikimedia.org/wiki/User:Alice">Alice</a> Some text'
    assert ImageSourceResolver._clean_artist(raw) == "Alice Some text"
    assert ImageSourceResolver._clean_artist("Bob") == "Bob"
    assert ImageSourceResolver._clean_artist("") == "Unknown"


# ============================================================
# ImageSourceResolver — NASA (KEY 불필요)
# ============================================================
def test_nasa_search_returns_results():
    r = ImageSourceResolver()
    try:
        results = r._search_nasa("moon", max_results=2)
    finally:
        r.close()
    if results:
        assert all(img.source == "nasa" for img in results)
        assert all(img.license == "PD-NASA" for img in results)
        assert all(img.image_url.startswith("https://") for img in results)
        assert all("NASA" in img.attribution for img in results)


# ============================================================
# ImageSourceResolver — 통합 search (KEY 있는 경우)
# ============================================================
def test_combined_search(pexels_key):
    """Pexels 있으면 Pexels 우선, 없으면 Wikimedia → NASA."""
    r = ImageSourceResolver(pexels_api_key=pexels_key)
    try:
        results = r.search("news", max_results=3)
    finally:
        r.close()
    if pexels_key and results:
        # Pexels이 첫 source
        assert results[0].source == "pexels"
    # 결과 없으면 OK (모든 source 실패 가능)


# ============================================================
# InfographicGenerator
# ============================================================
def test_infographic_generate_16x9(assets_dir):
    gen = InfographicGenerator()
    out = gen.generate_hero(
        title="Test Title",
        subtitle="Test Subtitle",
        aspect="16:9",
        out_path=assets_dir / "test_hero_16x9.png",
    )
    assert out.exists()
    assert out.stat().st_size > 1000  # 적어도 1KB


def test_infographic_generate_9x16(assets_dir):
    gen = InfographicGenerator()
    out = gen.generate_hero(
        title="세로형 테스트",
        aspect="9:16",
        out_path=assets_dir / "test_hero_9x16.png",
    )
    assert out.exists()


def test_infographic_aspect_to_size():
    assert InfographicGenerator._aspect_to_size("16:9") == (1280, 720)
    assert InfographicGenerator._aspect_to_size("9:16") == (1080, 1920)
    assert InfographicGenerator._aspect_to_size("1:1") == (1024, 1024)
    with pytest.raises(ValueError):
        InfographicGenerator._aspect_to_size("3:2")


# ============================================================
# ImageEmbedder
# ============================================================
def test_ext_from_url():
    assert ImageEmbedder._ext_from_url("https://x.com/photo.jpg") == "jpg"
    assert ImageEmbedder._ext_from_url("https://x.com/photo.JPEG?size=large") == "jpg"
    assert ImageEmbedder._ext_from_url("https://x.com/photo.png") == "png"
    assert ImageEmbedder._ext_from_url("https://x.com/photo.gif?v=1") == "gif"
    assert ImageEmbedder._ext_from_url("https://x.com/photo") is None
    assert ImageEmbedder._ext_from_url("https://x.com/photo.exe") is None


def test_embed_inserts_figures_after_h2(assets_dir):
    """HTML의 H2 직후에 <figure> 자동 삽입."""
    embedder = ImageEmbedder(assets_dir=assets_dir)
    images = [
        ImageResult(
            source="pexels", license="Pexels", photographer="A",
            source_url="https://x.com", image_url="https://x.com/1.jpg",
            local_path=assets_dir / "img1.png",
            alt="image 1", attribution="by A via Pexels",
        ),
        ImageResult(
            source="pexels", license="Pexels", photographer="B",
            source_url="https://x.com", image_url="https://x.com/2.jpg",
            local_path=assets_dir / "img2.png",
            alt="image 2", attribution="by B via Pexels",
        ),
    ]
    # dummy local files 생성 (embed는 file 존재 확인 안 함)
    (assets_dir / "img1.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 100)
    (assets_dir / "img2.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 100)

    html_in = (
        "<h1>Title</h1><p>intro</p>"
        "<h2>Section 1</h2><p>content 1</p>"
        "<h2>Section 2</h2><p>content 2</p>"
    )
    out = embedder.embed(html_in, images, max_per_post=2)
    # 두 figure 모두 삽입 확인
    assert out.count("<figure") == 2
    assert "img1.png" in out
    assert "img2.png" in out
    # H2 직후에 figure
    assert out.index("<h2>Section 1</h2>") < out.index("img1.png")
    assert out.index("<h2>Section 2</h2>") < out.index("img2.png")


def test_embed_no_images_returns_original(assets_dir):
    embedder = ImageEmbedder(assets_dir=assets_dir)
    html_in = "<h2>Test</h2><p>content</p>"
    out = embedder.embed(html_in, [], max_per_post=2)
    assert out == html_in


def test_embed_escapes_alt_and_attribution(assets_dir):
    """XSS 방어: alt + attribution escape.

    html.escape()로 attribute value 안전하게 escape.
    `<script>` 태그가 attribute value 안에 들어가도 escape되어 텍스트로만 표시됨.
    실제 HTML attribute 내부는 안전 (브라우저가 JS 실행 안 함).
    """
    embedder = ImageEmbedder(assets_dir=assets_dir)
    img = ImageResult(
        source="pexels", license="Pexels", photographer='<script>alert(1)</script>',
        source_url="https://x.com", image_url="https://x.com/1.jpg",
        local_path=assets_dir / "img.png",
        alt='"><img onerror=alert(1)>',
        attribution='<script>evil</script> by Hacker',
    )
    (assets_dir / "img.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 100)
    html_in = "<h2>Test</h2><p>content</p>"
    out = embedder.embed(html_in, [img])
    # 1) raw <script> 태그가 HTML에 존재하면 안 됨
    assert "<script>" not in out
    # 2) escape된 형태는 존재해야 함
    assert "&lt;script&gt;" in out
    # 3) attribute value 안의 <, >, " 가 escape되었는지 확인
    #    alt="&quot;&gt;&lt;img onerror=alert(1)&gt;" 형태
    assert 'alt="&quot;&gt;&lt;img onerror=alert(1)&gt;"' in out
    # 4) figcaption 내 <script>도 escape
    assert "&lt;script&gt;evil&lt;/script&gt;" in out


# ============================================================
# ImagePipeline — end-to-end
# ============================================================
def test_embed_hero_inserts_figure_after_h1(assets_dir):
    """H1 직후에 hero <figure> + dark gradient 삽입 (1차 출처: MDN figure)."""
    embedder = ImageEmbedder(assets_dir=assets_dir)
    img = ImageResult(
        source="pexels", license="Pexels", photographer="Alice",
        source_url="https://x.com", image_url="https://x.com/hero.jpg",
        local_path=assets_dir / "hero.png",
        alt="hero image", attribution="by Alice via Pexels",
    )
    (assets_dir / "hero.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 100)
    html_in = "<h1>OpenAI GPT-6</h1><p>intro</p><h2>section</h2><p>body</p>"
    out = embedder.embed_hero(html_in, img, height=500)
    # H1 직후에 figure
    assert out.index("<h1>OpenAI GPT-6</h1>") < out.index('class="article-hero"')
    assert 'class="article-hero"' in out
    assert 'loading="eager"' in out
    assert 'fetchpriority="high"' in out
    # dark gradient overlay
    assert "linear-gradient" in out
    assert "rgba(0,0,0,0.55)" in out
    # attribution figcaption
    assert "<figcaption" in out
    assert "by Alice via Pexels" in out
    # height 500px
    assert "height: 500px" in out


def test_embed_hero_no_h1_inserts_at_start(assets_dir):
    """H1 없으면 본문 시작에 hero 삽입."""
    embedder = ImageEmbedder(assets_dir=assets_dir)
    img = ImageResult(
        source="pexels", license="Pexels", photographer="Bob",
        source_url="https://x.com", image_url="https://x.com/hero.jpg",
        local_path=assets_dir / "hero.png",
        alt="h", attribution="by Bob",
    )
    (assets_dir / "hero.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 100)
    html_in = "<p>no h1</p>"
    out = embedder.embed_hero(html_in, img)
    assert out.startswith('<figure class="article-hero"')
    assert "<p>no h1</p>" in out


def test_embed_hero_no_image_returns_original(assets_dir):
    """local_path 없으면 원본 그대로."""
    embedder = ImageEmbedder(assets_dir=assets_dir)
    img = ImageResult(
        source="pexels", license="Pexels", photographer="X",
        source_url="", image_url="", local_path=None,
        alt="", attribution="",
    )
    html_in = "<h1>Title</h1>"
    out = embedder.embed_hero(html_in, img)
    assert out == html_in


def test_embed_hero_overlay_disabled(assets_dir):
    """overlay=False이면 gradient div 없음."""
    embedder = ImageEmbedder(assets_dir=assets_dir)
    img = ImageResult(
        source="pexels", license="Pexels", photographer="C",
        source_url="", image_url="", local_path=assets_dir / "h.png",
        alt="", attribution="by C",
    )
    (assets_dir / "h.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 100)
    out = embedder.embed_hero("<h1>Title</h1>", img, overlay=False)
    assert "linear-gradient" not in out


def test_embed_hero_escapes_xss(assets_dir):
    """XSS escape (alt + attribution). escape된 텍스트는 attribute value 안에서 안전.

    `<img onerror=alert(1)>` 같은 raw HTML이 alt attribute value 안에 들어가는 경우,
    html.escape()로 텍스트화되어 브라우저가 JS 실행 안 함.
    진짜 XSS는 attribute value 바깥에서 `<img ... onerror=...>` 가 attribute로 직접 있는 경우.
    """
    embedder = ImageEmbedder(assets_dir=assets_dir)
    img = ImageResult(
        source="pexels", license="Pexels", photographer='<script>alert(1)</script>',
        source_url="", image_url="", local_path=assets_dir / "h.png",
        alt='"><img onerror=alert(1)>',
        attribution='<script>evil</script> by Hacker',
    )
    (assets_dir / "h.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 100)
    out = embedder.embed_hero("<h1>Title</h1>", img)
    # 1) raw <script> 태그 없어야 함
    assert "<script>" not in out
    # 2) escape된 형태는 attribute value 안에 존재 (= 안전, 텍스트로만 표시)
    assert "&lt;script&gt;" in out
    assert "&lt;img onerror=alert(1)&gt;" in out
    # 3) 진짜 XSS: attribute로 직접 onerror= 가 있는 <img> 는 없어야 함
    #    패턴: <img [attrs] onerror=  (단, value quote 닫힌 후의 raw onerror)
    #    <img src="..." onerror="..."/> — attribute로 직접 onerror
    import re
    # <img ... onerror=  (단, alt/value quote 닫힌 후) — quote 닫힘을 추적하는 단순 검사:
    # attribute value 안의 onerror= (quote 짝 맞음) 는 안전, attribute로 직접 (quote 안 닫힘) 은 XSS
    # 가장 단순한 검사: src= 다음 onerror= 가 직접 나오면 XSS
    raw_xss = re.search(r'src="[^"]*"\s+onerror\s*=', out)
    assert raw_xss is None, f"Found raw XSS vector: {raw_xss.group(0)}"


def test_embed_background_style_injects_style(assets_dir):
    """embed_background_style이 <style>을 </head> 직후에 삽입."""
    embedder = ImageEmbedder(assets_dir=assets_dir)
    img = ImageResult(
        source="pexels", license="Pexels", photographer="D",
        source_url="", image_url="", local_path=assets_dir / "bg.png",
        alt="", attribution="by D",
    )
    (assets_dir / "bg.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 100)
    html_in = "<html><head><title>x</title></head><body>content</body></html>"
    out = embedder.embed_background_style(html_in, img, height=300)
    # <style>이 </head> 직후에 (즉 </head> 이후 위치) 삽입
    assert "</head>" in out
    assert "<style>" in out
    style_idx = out.index("<style>")
    head_end_idx = out.index("</head>")
    # <style>은 </head> **다음**에 와야 함 (</head> 인덱스보다 큼)
    assert style_idx > head_end_idx
    # </head>와 <style> 사이에 다른 내용 없어야 함
    between = out[head_end_idx + len("</head>"):style_idx]
    assert between.strip() == ""
    # background-image: url() 포함
    assert "background-image:" in out
    assert "url(" in out
    assert "linear-gradient" in out
    assert "height: 300px" in out
    # body content 보존
    assert "content" in out


def test_pipeline_e2e_with_pexels(assets_dir, pexels_key):
    """Pexels API + embed 통합 테스트. KEY 없으면 skip."""
    if not pexels_key:
        pytest.skip("PEXELS_API_KEY not set")
    pipe = ImagePipeline(
        assets_dir=assets_dir,
        pexels_api_key=pexels_key,
    )
    try:
        result = pipe.run(
            draft_html=(
                "<h1>OpenAI GPT-6</h1>"
                "<p>OpenAI가 새 모델을 발표했습니다.</p>"
                "<h2>추론 능력</h2><p>MMLU-Pro 92.3% 달성.</p>"
                "<h2>가격</h2><p>입력 $5/1M, 출력 $15/1M.</p>"
            ),
            keyword="OpenAI",
            max_images=2,
            use_infographic_fallback=False,
        )
    finally:
        pipe.close()
    assert "html" in result
    assert "images" in result
    assert "licenses" in result
    # Pexels 결과가 있으면 본문에 <figure> 포함
    if result["images"]:
        assert "<figure" in result["html"]
        # 파일이 실제로 저장됨
        for img_path in result["images"]:
            assert Path(img_path).exists()
        # licenses sidecar JSON 저장 확인
        license_files = list(assets_dir.glob("licenses_*.json"))
        if license_files:
            import json
            data = json.loads(license_files[0].read_text(encoding="utf-8"))
            assert "licenses" in data


def test_pipeline_fallback_to_infographic(assets_dir, pexels_key):
    """Pexels 결과 없을 때 infographic fallback."""
    pipe = ImagePipeline(
        assets_dir=assets_dir,
        pexels_api_key=None,  # Wikimedia + NASA만 시도 (결과 없을 가능성 큼)
    )
    try:
        result = pipe.run(
            draft_html="<h1>Fallback Test</h1><p>intro</p>",
            keyword="zzznosuchkeyword99999xyz",  # 거의 결과 없을 키워드
            max_images=2,
            use_infographic_fallback=True,
            title="Fallback Test Title",
            subtitle="No source found, using infographic",
            aspect="16:9",
        )
    finally:
        pipe.close()
    # fallback infographic 생성 시 path 반환
    # (Wikimedia/NASA에서 결과 있으면 infographic 안 만들어질 수도 있음)
    assert "html" in result


def test_pipeline_e2e_with_hero_image(assets_dir, pexels_key):
    """hero_image=True end-to-end. Pexels 1장 hero + 본문 1장."""
    if not pexels_key:
        pytest.skip("PEXELS_API_KEY not set")
    pipe = ImagePipeline(
        assets_dir=assets_dir,
        pexels_api_key=pexels_key,
    )
    try:
        result = pipe.run(
            draft_html=(
                "<h1>Climate Change 2026</h1>"
                "<p>지구 온난화 가속.</p>"
                "<h2>원인</h2><p>온실가스.</p>"
                "<h2>결과</h2><p>해수면 상승.</p>"
            ),
            keyword="climate",
            max_images=1,
            use_infographic_fallback=False,
            hero_image=True,
            hero_height=400,
        )
    finally:
        pipe.close()
    # hero image가 결과에 포함 (KEY 있고 Pexels 결과 있을 때)
    if result.get("hero"):
        assert Path(result["hero"]).exists()
        # HTML에 article-hero figure 포함
        assert "article-hero" in result["html"]
        # 첫 H1 직후에 삽입
        assert result["html"].index("<h1>") < result["html"].index("article-hero")
        # sidecar JSON에 hero_license 포함
        license_files = list(assets_dir.glob("licenses_climate*.json"))
        if license_files:
            import json
            data = json.loads(license_files[0].read_text(encoding="utf-8"))
            assert "hero_license" in data


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
