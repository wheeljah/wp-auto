"""ImageResult dataclass — 4개 source (Pexels, Wikimedia, NASA, infographic) 통합.

라이선스/attribution/source URL 자동 메타데이터.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

SourceName = Literal["pexels", "unsplash", "pixabay", "wikimedia", "nasa", "infographic"]
LicenseKind = Literal[
    "CC0", "CC-BY", "CC-BY-SA", "CC-BY-NC", "Pexels", "Unsplash",
    "Pixabay", "Public Domain", "PD-NASA", "Custom",
]


@dataclass
class ImageResult:
    """1개 이미지 결과 + 라이선스 메타데이터."""

    source: SourceName
    license: LicenseKind
    photographer: str
    source_url: str       # 원본 페이지 URL (attribution link)
    image_url: str        # 다운로드 URL (CDN)
    width: int = 0
    height: int = 0
    alt: str = ""
    attribution: str = ""  # "by Photographer via Source (License)"
    local_path: Path | None = None  # 다운로드 후 path (WebP 가능)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "license": self.license,
            "photographer": self.photographer,
            "source_url": self.source_url,
            "image_url": self.image_url,
            "width": self.width,
            "height": self.height,
            "alt": self.alt,
            "attribution": self.attribution,
            "local_path": str(self.local_path) if self.local_path else None,
        }
