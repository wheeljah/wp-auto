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

    def embed_hero(
        self,
        html_text: str,
        hero_image: ImageResult,
        height: int = 400,
        overlay: bool = True,
    ) -> str:
        """HTML 본문 상단에 hero <figure> + dark gradient 삽입.

        1차 출처 (MDN HTML figure):
          https://developer.mozilla.org/en-US/docs/Web/HTML/Element/figure
        - <figure>: self-contained content with optional <figcaption>
        - 권장 속성: loading="eager" (above the fold), fetchpriority="high"

        Args:
            html_text: 원본 HTML
            hero_image: 다운로드된 ImageResult (local_path 채워진 상태)
            height: hero 높이 (px)
            overlay: dark gradient overlay (가독성)

        Returns:
            hero <figure>가 첫 H1 직후 (또는 시작) 에 삽입된 HTML
        """
        if hero_image.local_path is None:
            return html_text
        rel_path = hero_image.local_path.name
        alt_escaped = html.escape(hero_image.alt or hero_image.photographer or "hero image")
        attribution_escaped = html.escape(hero_image.attribution)

        # 1) overlay (dark gradient for readability of text)
        overlay_html = (
            f'<div style="position: absolute; inset: 0; '
            f'background: linear-gradient(180deg, rgba(0,0,0,0.0) 50%, rgba(0,0,0,0.55) 100%); '
            f'pointer-events: none; border-radius: 8px;"></div>'
        ) if overlay else ""

        # 2) attribution figcaption (positioned bottom-right)
        figcaption_html = (
            f'<figcaption style="position: absolute; bottom: 10px; right: 10px; '
            f'background: rgba(0,0,0,0.6); color: #fff; padding: 4px 10px; '
            f'font-size: 12px; line-height: 1.4; border-radius: 4px; '
            f'font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif; '
            f'z-index: 2;">'
            f'{attribution_escaped}</figcaption>'
        )

        # 3) hero figure (전체 width, object-fit cover)
        hero_html = (
            f'<figure class="article-hero" style="position: relative; margin: 0 0 2rem 0; '
            f'overflow: hidden; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">'
            f'<img src="assets/images/{rel_path}" alt="{alt_escaped}" '
            f'loading="eager" fetchpriority="high" decoding="async" '
            f'style="display: block; width: 100%; height: {height}px; object-fit: cover; '
            f'background: #f0f0f0;" />'
            f'{overlay_html}'
            f'{figcaption_html}'
            f'</figure>\n'
        )

        # 첫 H1 직후에 삽입 (또는 시작)
        m = re.search(r'(</h1>)', html_text, re.IGNORECASE)
        if m:
            pos = m.end()
            return html_text[:pos] + "\n" + hero_html + html_text[pos:]
        # H1 없으면 본문 시작에 삽입
        return hero_html + html_text

    def embed_background_style(
        self,
        html_text: str,
        hero_image: ImageResult,
        selector: str = ".article-hero-bg",
        height: int = 400,
    ) -> str:
        """CSS background-image 방식 hero. <head>에 <style> 추가.

        사용법: 본문 시작에 <div class="article-hero-bg">...</div> 삽입하고,
        CSS에서 background-image: url(...)로 cover. SEO는 약하지만 visual은 강함.
        <img> 방식 (embed_hero)이 더 SEO-friendly. 이 메서드는 background-style 필요 시 사용.

        Args:
            html_text: 원본 HTML (보통 <body> 시작 부분)
            hero_image: 다운로드된 ImageResult
            selector: CSS selector (default ".article-hero-bg")
            height: hero 높이 (px)

        Returns:
            <style>이 <head>에 추가된 HTML
        """
        if hero_image.local_path is None:
            return html_text
        rel_path = hero_image.local_path.name
        style = (
            f'<style>{selector} {{ '
            f'background-image: linear-gradient(rgba(0,0,0,0.4), rgba(0,0,0,0.4)), '
            f'url("assets/images/{rel_path}"); '
            f'background-size: cover; background-position: center; '
            f'height: {height}px; display: flex; align-items: flex-end; '
            f'padding: 1.5rem; color: white; '
            f'}}</style>'
        )
        # <head>에 추가
        m = re.search(r'(</head>)', html_text, re.IGNORECASE)
        if m:
            pos = m.end()
            return html_text[:pos] + style + html_text[pos:]
        return style + html_text

    @staticmethod
    def _ext_from_url(url: str) -> str | None:
        m = re.search(r'\.([a-zA-Z0-9]+)(?:\?|$)', url)
        if m:
            ext = m.group(1).lower()
            # 일반적인 image/video ext만
            if ext in ("jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff", "svg"):
                return "jpg" if ext == "jpeg" else ext
        return None
