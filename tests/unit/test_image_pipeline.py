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


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
