"""이미지 자동 최적화: WebP/AVIF 변환 + 리사이즈.

Pillow 기반. 외부 서비스 의존 없음.

사용법:
    from wp_auto.optimize.image_optimizer import ImageOptimizer
    opt = ImageOptimizer()
    out_path = opt.optimize(Path("hero.jpg"), max_width=1200)
    # → hero.webp (1200px 이하, WebP 형식)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loguru import logger
from PIL import Image, ImageOps


@dataclass
class OptimizeResult:
    """이미지 최적화 결과."""

    src_path: Path
    dst_path: Path
    src_size_kb: float
    dst_size_kb: float
    reduction_pct: float  # 음수면 크기 감소
    width: int
    height: int
    format: str  # "webp" or "avif"


class ImageOptimizer:
    """이미지 WebP/AVIF 변환 + 리사이즈."""

    def __init__(self, quality: int = 80, default_format: str = "webp") -> None:
        self.quality = quality
        self.default_format = default_format
        logger.info("ImageOptimizer: quality={}, format={}", quality, default_format)

    def optimize(
        self,
        src_path: Path,
        max_width: int = 1200,
        quality: int | None = None,
        format: str | None = None,
    ) -> OptimizeResult:
        """이미지 변환 + 리사이즈.

        Args:
            src_path: 원본 이미지 경로
            max_width: 최대 가로 크기 (그 이상은 축소)
            quality: 1-100, default 80
            format: "webp" or "avif", default "webp"

        Returns:
            OptimizeResult (원본/결과 경로, 크기, 압축률)
        """
        src_path = Path(src_path)
        if not src_path.exists():
            raise FileNotFoundError(f"Image not found: {src_path}")

        q = quality if quality is not None else self.quality
        fmt = (format or self.default_format).lower()
        if fmt not in ("webp", "avif"):
            raise ValueError(f"Unsupported format: {fmt} (webp or avif only)")

        # 결과 파일 경로 (.webp/.avif)
        dst_path = src_path.with_suffix(f".{fmt}")

        # EXIF 회전 보정 + 열기
        with Image.open(src_path) as img:
            img = ImageOps.exif_transpose(img)

            # RGBA → RGB (WebP는 RGB 또는 RGBA 모두 가능, JPEG는 RGB)
            if fmt == "webp" and img.mode == "RGBA":
                # WebP는 alpha 지원
                pass
            elif img.mode in ("RGBA", "LA", "P") and fmt == "webp":
                img = img.convert("RGB")

            # 리사이즈 (가로 기준)
            original_size = src_path.stat().st_size
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.LANCZOS)
                logger.debug(
                    "resized {} → {}x{}", src_path.name, max_width, new_height
                )

            # 저장
            save_kwargs: dict = {"quality": q, "method": 6}
            if fmt == "webp":
                save_kwargs["lossless"] = False
            img.save(dst_path, fmt.upper(), **save_kwargs)

        # 결과
        new_size = dst_path.stat().st_size
        reduction = (new_size - original_size) / original_size * 100
        with Image.open(dst_path) as img:
            final_w, final_h = img.size

        result = OptimizeResult(
            src_path=src_path,
            dst_path=dst_path,
            src_size_kb=original_size / 1024,
            dst_size_kb=new_size / 1024,
            reduction_pct=reduction,
            width=final_w,
            height=final_h,
            format=fmt,
        )
        logger.info(
            "optimized: {} → {} (-{:.1f}%, {}x{} {})",
            src_path.name,
            dst_path.name,
            abs(reduction),
            final_w,
            final_h,
            fmt,
        )
        return result

    def batch_optimize(
        self, paths: list[Path], max_width: int = 1200
    ) -> list[OptimizeResult]:
        """여러 이미지 일괄 변환."""
        results = []
        for path in paths:
            try:
                results.append(self.optimize(path, max_width=max_width))
            except Exception as e:
                logger.error("batch_optimize failed for {}: {}", path, e)
        return results


__all__ = ["ImageOptimizer", "OptimizeResult"]
