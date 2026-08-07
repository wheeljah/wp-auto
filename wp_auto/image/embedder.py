"""ImageEmbedder — HTML 초안에 <figure> 자동 삽입 + 라이선스 메타데이터.

핵심:
- H2/H3 기준으로 본문 분할
- 첫 번째 H2 직후에 첫 image, 두 번째 H2 직후에 두 번째 image
- <figure class="wp-block-image"><img src="assets/images/..." alt="..." /><figcaption>by Photographer via Source (License)</figcaption></figure>
- 다운로드 + WebP 변환 (image_optimizer.py 활용)
- alt + attribution 자동 생성
"""
from __future__ import annotations

import html
import re
from pathlib import Path

import httpx
from loguru import logger

from .models import ImageResult
from wp_auto.optimize.image_optimizer import ImageOptimizer


class ImageEmbedder:
    """HTML 초안에 image 자동 download + embed."""

    def __init__(
        self,
        assets_dir: Path,
        image_optimizer: ImageOptimizer | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.assets_dir = Path(assets_dir)
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.image_optimizer = image_optimizer or ImageOptimizer()
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout, follow_redirects=True)
        logger.info("ImageEmbedder: assets_dir={}", self.assets_dir)

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def download(self, image: ImageResult, max_width: int = 1280) -> ImageResult:
        """이미지 다운로드 + WebP 변환.

        Args:
            image: ImageResult (image_url, source, photographer 등)
            max_width: WebP 변환 시 최대 가로 크기

        Returns:
            업데이트된 ImageResult (local_path = WebP path)
        """
        if not image.image_url:
            logger.warning("Empty image_url for {}", image.source)
            return image
        try:
            r = self._client.get(image.image_url)
            r.raise_for_status()
            ext = self._ext_from_url(image.image_url) or "jpg"
            safe_source = re.sub(r"[^a-z0-9]", "", image.source)[:10]
            safe_photographer = re.sub(r"[^A-Za-z0-9_-]", "", image.photographer)[:30] or "unknown"
            import hashlib
            url_hash = hashlib.md5(image.image_url.encode("utf-8")).hexdigest()[:8]
            filename = f"{safe_source}_{safe_photographer}_{url_hash}.{ext}"
            local_path = self.assets_dir / filename
            local_path.write_bytes(r.content)
            logger.info("Downloaded: {} ({} bytes)", local_path, len(r.content))

            # WebP 변환 (image_optimizer 활용)
            try:
                webp_path = self.image_optimizer.optimize(local_path, max_width=max_width, format="webp")
                image.local_path = webp_path
                logger.info("Optimized to WebP: {} ({} KB)", webp_path.name, webp_path.stat().st_size // 1024)
            except Exception as e:
                logger.warning("WebP optimization failed, keeping original: {}", e)
                image.local_path = local_path
            return image
        except Exception as e:
            logger.error("Download failed for {}: {}", image.image_url, e)
            return image

    def embed(
        self,
        html_text: str,
        images: list[ImageResult],
        max_per_post: int = 2,
    ) -> str:
        """HTML 본문에 <figure> 자동 삽입.

        Args:
            html_text: 원본 HTML
            images: 다운로드된 ImageResult 리스트 (local_path 채워진 상태)
            max_per_post: 본문당 최대 image 수 (default 2)

        Returns:
            image가 삽입된 HTML
        """
        available = [img for img in images if img.local_path is not None]
        if not available:
            return html_text

        # H2/H3 기준으로 분할 — re.split으로 delimiter도 포함
        pattern = re.compile(r'(<h[23][^>]*>.*?</h[23]>)', re.DOTALL)
        parts = pattern.split(html_text)

        # parts는 [text, h2, text, h2, text, ...] 형태
        # h2/h3 위치에 figure 삽입
        inserted = 0
        new_parts: list[str] = []
        for part in parts:
            new_parts.append(part)
            if inserted >= max_per_post or inserted >= len(available):
                continue
            if pattern.match(part):
                img = available[inserted]
                new_parts.append("\n" + self._build_figure(img) + "\n")
                inserted += 1
        return "".join(new_parts)

    def _build_figure(self, img: ImageResult) -> str:
        rel_path = img.local_path.name if img.local_path else ""
        # alt + figcaption escape
        alt_escaped = html.escape(img.alt or img.photographer or "image")
        attribution_escaped = html.escape(img.attribution)
        return (
            f'<figure class="wp-block-image">'
            f'<img src="assets/images/{rel_path}" alt="{alt_escaped}" loading="lazy" />'
            f'<figcaption>{attribution_escaped}</figcaption>'
            f'</figure>'
        )

    @staticmethod
    def _ext_from_url(url: str) -> str | None:
        m = re.search(r'\.([a-zA-Z0-9]+)(?:\?|$)', url)
        if m:
            ext = m.group(1).lower()
            # 일반적인 image/video ext만
            if ext in ("jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff", "svg"):
                return "jpg" if ext == "jpeg" else ext
        return None
