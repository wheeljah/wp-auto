"""InfographicGenerator — PIL 기반 자체 infographic (image source 없을 때 fallback).

YouTube Shorts thumbnail 패턴 확장 (user.md memory rule):
- 9:16 (1080x1920) / 16:9 (1280x720) / 1:1 (1024x1024)
- 상단 20% 제목 (노란 #FFEB3B) + 하단 20% 부제 (흰 #FFFFFF) — 노 박스
- 상단 accent bar
- 폰트: Noto Sans KR (OFL 1.1) — wp-auto/assets/fonts/에 자체 호스팅

자체 생성 = 라이선스 걱정 0. 100% 상업용 OK.
"""
from __future__ import annotations

from pathlib import Path

from loguru import logger
from PIL import Image, ImageDraw, ImageFont


# 폰트 후보 (OFL 1.1 — 상업용 무료)
FONT_CANDIDATES = [
    "BlackHanSans-Regular.ttf",
    "NotoSansKR-Bold.ttf",
    "NotoSansCJKkr-Bold.otf",
    "Pretendard-Bold.otf",
    "arial.ttf",  # Windows 기본 fallback
    "DejaVuSans-Bold.ttf",  # Linux fallback
]


class InfographicGenerator:
    """PIL 기반 키워드/제목 infographic 생성.

    사용법:
        gen = InfographicGenerator(fonts_dir=Path("assets/fonts"))
        out = gen.generate_hero(
            title="OpenAI GPT-6 발표",
            subtitle="추론 능력 10배 강화",
            aspect="16:9",
            out_path=Path("assets/images/hero_gpt6.png"),
        )
    """

    DEFAULT_PALETTE = {
        "bg": (24, 32, 64),          # dark navy
        "title": (255, 235, 59),     # yellow #FFEB3B
        "subtitle": (255, 255, 255), # white
        "accent": (224, 32, 32),     # red #E02020
    }

    def __init__(self, fonts_dir: Path | None = None) -> None:
        self.fonts_dir = Path(fonts_dir) if fonts_dir else Path("assets/fonts")
        logger.debug("InfographicGenerator: fonts_dir={}", self.fonts_dir)

    def generate_hero(
        self,
        title: str,
        subtitle: str = "",
        aspect: str = "16:9",
        out_path: Path | None = None,
        palette: dict | None = None,
    ) -> Path:
        """Hero 이미지 생성 (제목 + 부제).

        Args:
            title: 메인 제목 (큰 글씨)
            subtitle: 부제 (작은 글씨)
            aspect: "16:9" (1280x720), "9:16" (1080x1920), "1:1" (1024x1024)
            out_path: 저장 경로. None이면 자동.
            palette: 색상 dict (bg, title, subtitle, accent)

        Returns:
            저장된 Path
        """
        w, h = self._aspect_to_size(aspect)
        colors = {**self.DEFAULT_PALETTE, **(palette or {})}
        img = Image.new("RGB", (w, h), colors["bg"])
        draw = ImageDraw.Draw(img)

        # 상단 accent bar
        accent_h = max(4, h // 80)
        draw.rectangle([0, 0, w, accent_h], fill=colors["accent"])

        # 폰트 로드
        title_font = self._load_font(size=int(h * 0.13))
        subtitle_font = self._load_font(size=int(h * 0.07))

        # 제목 (상단 20% 영역, 노란색, 검정 outline)
        title_y_start = int(h * 0.20)
        self._draw_wrapped_text(
            draw, title, title_font, colors["title"],
            x_center=w // 2, y=title_y_start,
            max_width=int(w * 0.88), outline_color=(0, 0, 0), outline_width=3,
        )

        # 부제 (하단 20% 영역, 흰색, 검정 outline)
        if subtitle:
            subtitle_y = int(h * 0.70)
            self._draw_wrapped_text(
                draw, subtitle, subtitle_font, colors["subtitle"],
                x_center=w // 2, y=subtitle_y,
                max_width=int(w * 0.84), outline_color=(0, 0, 0), outline_width=2,
            )

        # 저장
        if out_path is None:
            import hashlib
            h_hash = hashlib.md5((title + subtitle).encode("utf-8")).hexdigest()[:8]
            out_path = Path(f"assets/images/hero_{aspect.replace(':', 'x')}_{h_hash}.png")
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path, "PNG", optimize=True)
        logger.info("Generated infographic: {}", out_path)
        return out_path

    @staticmethod
    def _aspect_to_size(aspect: str) -> tuple[int, int]:
        if aspect == "16:9":
            return 1280, 720
        elif aspect == "9:16":
            return 1080, 1920
        elif aspect == "1:1":
            return 1024, 1024
        else:
            raise ValueError(f"Unsupported aspect: {aspect} (16:9 | 9:16 | 1:1)")

    def _load_font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        for name in FONT_CANDIDATES:
            path = self.fonts_dir / name
            if path.exists():
                try:
                    return ImageFont.truetype(str(path), size)
                except Exception:
                    continue
        # Windows 기본 (DejaVu 등)
        try:
            return ImageFont.truetype("arial.ttf", size)
        except Exception:
            return ImageFont.load_default()

    def _draw_wrapped_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont,
        color: tuple,
        x_center: int,
        y: int,
        max_width: int,
        outline_color: tuple = (0, 0, 0),
        outline_width: int = 2,
    ) -> None:
        """가운데 정렬 + 자동 줄바꿈 + outline."""
        words = text.split()
        lines: list[str] = []
        line = ""
        for word in words:
            test = (line + " " + word).strip()
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] > max_width and line:
                lines.append(line)
                line = word
            else:
                line = test
        if line:
            lines.append(line)

        # 폰트 높이 계산 (draw.textbbox 기준)
        sample_bbox = draw.textbbox((0, 0), "Ag", font=font)
        line_height = (sample_bbox[3] - sample_bbox[1]) + 8

        for i, ln in enumerate(lines):
            bbox = draw.textbbox((0, 0), ln, font=font)
            text_w = bbox[2] - bbox[0]
            x = x_center - text_w // 2
            line_y = y + i * line_height
            # outline
            if outline_width > 0:
                for dx in range(-outline_width, outline_width + 1):
                    for dy in range(-outline_width, outline_width + 1):
                        if dx == 0 and dy == 0:
                            continue
                        draw.text((x + dx, line_y + dy), ln, fill=outline_color, font=font)
            # 본문
            draw.text((x, line_y), ln, fill=color, font=font)
