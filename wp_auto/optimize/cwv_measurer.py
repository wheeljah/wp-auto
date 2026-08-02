"""Core Web Vitals 자동 측정 (Playwright + web-vitals).

LCP/INP/CLS를 모바일 뷰포트(375x812)에서 측정. 3회 반복 후 중앙값.

사용법:
    from wp_auto.optimize.cwv_measurer import CWVMeasurer
    measurer = CWVMeasurer()
    result = await measurer.measure("https://example.com", runs=3)

    # 또는 로컬 HTML
    result = await measurer.measure_html("<html>...</html>")
"""

from __future__ import annotations

import asyncio
import statistics
from dataclasses import asdict, dataclass
from datetime import UTC
from pathlib import Path

from loguru import logger

# Playwright는 lazy import (install 안 됐을 때도 import 가능하도록)


# web-vitals JS (v4) — CDN에서 inject
WEB_VITALS_JS = """
// web-vitals v4 (simplified inline)
const observer = (cb) => {
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      cb(entry);
    }
  }).observe({ type: cb.type, buffered: true });
};

// LCP
let lcpValue = 0;
observer({
  type: 'largest-contentful-paint',
  get type() { return 'largest-contentful-paint'; },
});
new PerformanceObserver((list) => {
  const entries = list.getEntries();
  const last = entries[entries.length - 1];
  lcpValue = last ? last.startTime : 0;
}).observe({ type: 'largest-contentful-paint', buffered: true });

// CLS
let clsValue = 0;
new PerformanceObserver((list) => {
  for (const entry of list.getEntries()) {
    if (!entry.hadRecentInput) {
      clsValue += entry.value;
    }
  }
}).observe({ type: 'layout-shift', buffered: true });

// INP (간소화: 마지막 event duration)
let inpValue = 0;
new PerformanceObserver((list) => {
  const entries = list.getEntries();
  if (entries.length > 0) {
    const last = entries[entries.length - 1];
    inpValue = last.duration || 0;
  }
}).observe({ type: 'event', buffered: true, durationThreshold: 16 });

// 측정 결과를 window.__cwv__에 저장
window.__cwv__ = () => ({
  lcp: lcpValue,
  cls: clsValue,
  inp: inpValue,
});
"""


@dataclass
class CWVResult:
    """Core Web Vitals 측정 결과."""

    url: str
    lcp_ms: float  # milliseconds
    inp_ms: float
    cls: float
    rating: str  # 'good' | 'needs-improvement' | 'poor'
    runs: int
    measured_at: str

    def to_dict(self) -> dict:
        return asdict(self)

    def recommendations(self) -> list[str]:
        """측정 결과 기반 개선 권고."""
        recs = []
        if self.lcp_ms > 2500:
            recs.append("LCP > 2.5s: 히어로 이미지에 fetchpriority='high' + preload 추가")
        if self.inp_ms > 200:
            recs.append("INP > 200ms: 써드파티 스크립트 defer, 무거운 JS 지연")
        if self.cls > 0.1:
            recs.append("CLS > 0.1: 모든 img에 width/height 명시")
        return recs


class CWVMeasurer:
    """Playwright 기반 CWV 측정기.

    사용법:
        measurer = CWVMeasurer()
        result = asyncio.run(measurer.measure("https://example.com"))
    """

    # CWV 기준 (2026 Google)
    LCP_GOOD = 2500
    LCP_POOR = 4000
    INP_GOOD = 200
    INP_POOR = 500
    CLS_GOOD = 0.1
    CLS_POOR = 0.25

    def __init__(self, mobile: bool = True) -> None:
        self.mobile = mobile
        # 모바일 뷰포트
        self.viewport = {"width": 375, "height": 812} if mobile else {"width": 1280, "height": 720}
        logger.info(
            "CWVMeasurer: mobile={}, viewport={}", mobile, self.viewport
        )

    @staticmethod
    def _rate_lcp(ms: float) -> str:
        if ms <= 2500:
            return "good"
        if ms <= 4000:
            return "needs-improvement"
        return "poor"

    @staticmethod
    def _rate_inp(ms: float) -> str:
        if ms <= 200:
            return "good"
        if ms <= 500:
            return "needs-improvement"
        return "poor"

    @staticmethod
    def _rate_cls(value: float) -> str:
        if value <= 0.1:
            return "good"
        if value <= 0.25:
            return "needs-improvement"
        return "poor"

    @staticmethod
    def _worst_rating(*ratings: str) -> str:
        """여러 rating 중 가장 나쁜 것."""
        order = {"good": 0, "needs-improvement": 1, "poor": 2}
        return max(ratings, key=lambda r: order.get(r, 0))

    async def measure(
        self, url: str, runs: int = 3
    ) -> CWVResult:
        """URL 측정 (3회 반복 후 중앙값).

        Note: Playwright 필요. install: `playwright install chromium`
        """
        from playwright.async_api import async_playwright  # noqa

        lcp_values: list[float] = []
        inp_values: list[float] = []
        cls_values: list[float] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                for i in range(runs):
                    logger.info("CWV measure run {}/{} for {}", i + 1, runs, url)
                    context = await browser.new_context(
                        viewport=self.viewport,
                        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)",
                    )
                    page = await context.new_page()
                    try:
                        await page.goto(url, wait_until="networkidle", timeout=30000)
                        await page.add_script_tag(content=WEB_VITALS_JS)
                        # 측정 대기 (LCP가 발생할 시간)
                        await asyncio.sleep(3)
                        cwv = await page.evaluate("window.__cwv__ && window.__cwv__()")
                        if cwv:
                            lcp_values.append(cwv.get("lcp", 0))
                            inp_values.append(cwv.get("inp", 0))
                            cls_values.append(cwv.get("cls", 0))
                    finally:
                        await page.close()
                        await context.close()
            finally:
                await browser.close()

        if not lcp_values:
            logger.warning("CWV measure: no values collected for {}", url)
            return CWVResult(
                url=url,
                lcp_ms=0,
                inp_ms=0,
                cls=0,
                rating="poor",
                runs=0,
                measured_at=asyncio.get_event_loop().time().__str__(),
            )

        lcp = statistics.median(lcp_values)
        inp = statistics.median(inp_values)
        cls = statistics.median(cls_values)
        rating = self._worst_rating(
            self._rate_lcp(lcp),
            self._rate_inp(inp),
            self._rate_cls(cls),
        )

        from datetime import datetime

        return CWVResult(
            url=url,
            lcp_ms=round(lcp, 1),
            inp_ms=round(inp, 1),
            cls=round(cls, 3),
            rating=rating,
            runs=runs,
            measured_at=datetime.now(UTC).isoformat(),
        )

    async def measure_html(self, html: str, runs: int = 3) -> CWVResult:
        """로컬 HTML 측정 (file:// URL)."""
        # 임시 파일로 저장
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".html", delete=False, encoding="utf-8"
        ) as f:
            f.write(html)
            tmp_path = f.name
        try:
            file_url = Path(tmp_path).as_uri()
            return await self.measure(file_url, runs=runs)
        finally:
            Path(tmp_path).unlink(missing_ok=True)


__all__ = ["CWVMeasurer", "CWVResult", "WEB_VITALS_JS"]
