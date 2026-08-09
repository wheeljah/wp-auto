"""ImagePipeline — search → download → embed orchestrator.

사용법:
    from wp_auto.image.pipeline import ImagePipeline
    import os
    pipe = ImagePipeline(
        assets_dir=Path("assets/images"),
        pexels_api_key=os.environ.get("PEXELS_API_KEY"),
    )
    result = pipe.run(
        draft_html="<h2>...</h2><p>...</p>...",
        keyword="OpenAI GPT-6",
        max_images=2,
    )
    final_html = result["html"]
    licenses = result["licenses"]
"""
from __future__ import annotations

import json
from pathlib import Path

from loguru import logger

from .embedder import ImageEmbedder
from .generator import InfographicGenerator
from .models import ImageResult
from .source_resolver import ImageSourceResolver


class ImagePipeline:
    """통합 orchestrator.

    1. ImageSourceResolver.search() — Pexels → Wikimedia → NASA
    2. ImageEmbedder.download() — 각 image 다운로드 + WebP 변환
    3. ImageEmbedder.embed() — HTML에 <figure> 삽입
    4. (선택) 자체 infographic hero — image 없을 때 fallback
    5. 라이선스 메타데이터 sidecar JSON 저장
    """

    def __init__(
        self,
        assets_dir: Path,
        pexels_api_key: str | None = None,
        unsplash_api_key: str | None = None,
        pixabay_api_key: str | None = None,
        fonts_dir: Path | None = None,
    ) -> None:
        self.assets_dir = Path(assets_dir)
        self.resolver = ImageSourceResolver(
            pexels_api_key=pexels_api_key,
            unsplash_api_key=unsplash_api_key,
            pixabay_api_key=pixabay_api_key,
        )
        self.embedder = ImageEmbedder(assets_dir=self.assets_dir)
        self.infographic = InfographicGenerator(fonts_dir=fonts_dir)

    def close(self) -> None:
        self.resolver.close()
        self.embedder.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def run(
        self,
        draft_html: str,
        keyword: str,
        max_images: int = 2,
        use_infographic_fallback: bool = True,
        title: str = "",
        subtitle: str = "",
        aspect: str = "16:9",
        save_license_json: bool = True,
        hero_image: bool = False,
        hero_height: int = 400,
    ) -> dict:
        """전체 파이프라인 실행.

        Args:
            draft_html: 원본 HTML
            keyword: 검색 키워드
            max_images: 본문당 최대 image 수
            use_infographic_fallback: image 못 찾을 때 자체 infographic hero 생성
            title/subtitle/aspect: infographic용 (fallback일 때만)
            save_license_json: out/ 디렉토리에 licenses sidecar JSON 저장
            hero_image: True면 본문 상단에 hero image 1장 자동 검색 + embed
            hero_height: hero image 높이 (px, default 400)

        Returns:
            dict with keys:
                - html: image가 삽입된 HTML
                - images: local_path 리스트
                - licenses: ImageResult.to_dict() 리스트
                - hero: hero image path (없으면 None)
                - infographic: fallback infographic path (없으면 None)
        """
        # 0) Hero image (별도 1장 검색, 큰 해상도)
        hero_path: Path | None = None
        hero_meta: dict | None = None
        if hero_image:
            logger.info("ImagePipeline: searching hero image for keyword='{}'", keyword)
            hero_candidates = self.resolver.search(keyword, max_results=1)
            if hero_candidates:
                hero_d = self.embedder.download(hero_candidates[0], max_width=1920)
                if hero_d.local_path:
                    draft_html = self.embedder.embed_hero(
                        draft_html, hero_d, height=hero_height
                    )
                    hero_path = hero_d.local_path
                    hero_meta = hero_d.to_dict()
                    logger.info("Hero embedded: {}", hero_path)

        # 1) 본문 image 검색
        logger.info("ImagePipeline: searching for keyword='{}'", keyword)
        images = self.resolver.search(keyword, max_results=max_images)
        logger.info("Found {} candidate images", len(images))

        # 2) 다운로드 + WebP
        downloaded: list[ImageResult] = []
        for img in images:
            d = self.embedder.download(img)
            if d.local_path is not None:
                downloaded.append(d)

        # 3) Embed (image가 없으면 infographic fallback)
        infographic_path: Path | None = None
        if not downloaded and use_infographic_fallback and title:
            infographic_path = self.infographic.generate_hero(
                title=title,
                subtitle=subtitle,
                aspect=aspect,
                out_path=self.assets_dir / f"infographic_{keyword.replace(' ', '_')[:30]}.png",
            )
            # infographic은 HTML 첫 H1 직후에 삽입
            draft_html = self._inject_infographic(draft_html, infographic_path)

        final_html = self.embedder.embed(draft_html, downloaded, max_per_post=max_images)

        # 4) 라이선스 sidecar JSON
        licenses = [img.to_dict() for img in downloaded]
        if save_license_json and (licenses or hero_meta):
            sidecar_data = {"keyword": keyword, "licenses": licenses}
            if hero_meta:
                sidecar_data["hero_license"] = hero_meta
            sidecar_path = self.assets_dir / f"licenses_{keyword.replace(' ', '_')[:30]}.json"
            sidecar_path.parent.mkdir(parents=True, exist_ok=True)
            sidecar_path.write_text(
                json.dumps(sidecar_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info("License sidecar saved: {}", sidecar_path)

        return {
            "html": final_html,
            "images": [str(img.local_path) for img in downloaded if img.local_path],
            "licenses": licenses,
            "hero": str(hero_path) if hero_path else None,
            "infographic": str(infographic_path) if infographic_path else None,
        }

    def _inject_infographic(self, html_text: str, infographic_path: Path) -> str:
        """자체 infographic을 HTML 첫 H1 직후에 삽입."""
        if not infographic_path:
            return html_text
        rel_path = infographic_path.name
        figure = (
            f'<figure class="wp-block-image">'
            f'<img src="assets/images/{rel_path}" alt="infographic" />'
            f'<figcaption>Infographic by dopaminews.com</figcaption>'
            f'</figure>'
        )
        # 첫 H1 직후 삽입
        m = re.search(r'(</h1>)', html_text, re.IGNORECASE)
        if m:
            insert_pos = m.end()
            return html_text[:insert_pos] + "\n" + figure + "\n" + html_text[insert_pos:]
        return figure + "\n" + html_text


import re  # noqa: E402  (위에서 사용)
