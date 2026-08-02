"""Image Optimizer + Lazy Loader 단위 테스트."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from wp_auto.optimize.image_optimizer import ImageOptimizer, OptimizeResult
from wp_auto.optimize.lazy_loader import inject_lazy_loading, strip_dimensions

# === 1. Image Optimizer ===

@pytest.fixture
def sample_jpg(tmp_path: Path) -> Path:
    """테스트용 큰 JPEG 이미지 (2000x1500, 빨간색)."""
    img = Image.new("RGB", (2000, 1500), color="red")
    path = tmp_path / "test.jpg"
    img.save(path, "JPEG", quality=95)
    return path


def test_optimize_converts_to_webp(sample_jpg: Path) -> None:
    """JPEG → WebP 변환."""
    opt = ImageOptimizer()
    result = opt.optimize(sample_jpg, max_width=1200)
    assert result.dst_path.suffix == ".webp"
    assert result.dst_path.exists()
    assert result.format == "webp"


def test_optimize_resizes_to_max_width(sample_jpg: Path) -> None:
    """max_width 초과 시 리사이즈."""
    opt = ImageOptimizer()
    result = opt.optimize(sample_jpg, max_width=1200)
    assert result.width == 1200
    assert result.height == 900  # 4:3 비율


def test_optimize_reduces_size(sample_jpg: Path) -> None:
    """WebP 변환으로 크기 감소."""
    opt = ImageOptimizer(quality=70)
    result = opt.optimize(sample_jpg, max_width=1200, quality=70)
    assert result.dst_size_kb < result.src_size_kb
    assert result.reduction_pct < 0  # 음수 = 감소


def test_optimize_avif_format(sample_jpg: Path) -> None:
    """AVIF 형식 변환."""
    opt = ImageOptimizer(default_format="avif")
    result = opt.optimize(sample_jpg, max_width=1200, format="avif")
    assert result.dst_path.suffix == ".avif"
    assert result.format == "avif"


def test_optimize_invalid_format_raises(sample_jpg: Path) -> None:
    """지원 안 되는 형식 → ValueError."""
    opt = ImageOptimizer()
    with pytest.raises(ValueError, match="Unsupported format"):
        opt.optimize(sample_jpg, format="gif")


def test_optimize_file_not_found(tmp_path: Path) -> None:
    """존재하지 않는 파일 → FileNotFoundError."""
    opt = ImageOptimizer()
    with pytest.raises(FileNotFoundError):
        opt.optimize(tmp_path / "nonexistent.jpg")


def test_batch_optimize_processes_multiple(sample_jpg: Path, tmp_path: Path) -> None:
    """여러 이미지 일괄 변환."""
    img2 = Image.new("RGB", (800, 600), color="blue")
    path2 = tmp_path / "test2.jpg"
    img2.save(path2, "JPEG")

    opt = ImageOptimizer()
    results = opt.batch_optimize([sample_jpg, path2], max_width=1200)
    assert len(results) == 2
    assert all(isinstance(r, OptimizeResult) for r in results)


# === 2. Lazy Loader ===

def test_inject_lazy_loading_marks_imgs_as_lazy() -> None:
    """모든 <img>에 loading='lazy' (첫 번째 제외)."""
    html = """
    <html><body>
    <img src="/a.jpg" alt="A">
    <img src="/b.jpg" alt="B">
    <img src="/c.jpg" alt="C">
    </body></html>
    """
    result = inject_lazy_loading(html, exclude_first=True)
    assert 'loading="eager"' in result  # 첫 번째
    assert 'fetchpriority="high"' in result
    assert result.count('loading="lazy"') == 2  # 나머지 2개


def test_inject_lazy_loading_adds_dimensions() -> None:
    """width/height 없는 img에 기본값 추가."""
    html = '<html><body><img src="/a.jpg" alt="A"></body></html>'
    result = inject_lazy_loading(html, exclude_first=True, default_width=1200, default_height=675)
    assert 'width="1200"' in result
    assert 'height="675"' in result


def test_inject_lazy_loading_preserves_existing_dimensions() -> None:
    """기존 width/height 보존."""
    html = '<html><body><img src="/a.jpg" alt="A" width="800" height="600"></body></html>'
    result = inject_lazy_loading(html, exclude_first=True)
    assert 'width="800"' in result
    assert 'height="600"' in result


def test_inject_lazy_loading_no_imgs_returns_unchanged() -> None:
    """이미지 없으면 그대로."""
    html = "<html><body><p>No images</p></body></html>"
    result = inject_lazy_loading(html)
    assert result == html


def test_inject_lazy_loading_exclude_first_false() -> None:
    """exclude_first=False → 모든 img lazy."""
    html = '<html><body><img src="/a.jpg" alt="A"><img src="/b.jpg" alt="B"></body></html>'
    result = inject_lazy_loading(html, exclude_first=False)
    assert result.count('loading="lazy"') == 2
    assert "fetchpriority" not in result


def test_strip_dimensions_removes_all_attrs() -> None:
    """strip_dimensions: width/height/loading/fetchpriority 제거."""
    html = '<img src="/a.jpg" width="1200" height="675" loading="lazy" fetchpriority="high" alt="A">'
    result = strip_dimensions(html)
    assert "width=" not in result
    assert "height=" not in result
    assert "loading=" not in result
    assert "fetchpriority=" not in result
