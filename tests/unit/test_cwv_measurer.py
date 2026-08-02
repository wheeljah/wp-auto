"""CWV Measurer 단위 테스트 (rating/recommendations만)."""

from __future__ import annotations

from wp_auto.optimize.cwv_measurer import CWVMeasurer, CWVResult

# === 1. Rating helpers ===

def test_rate_lcp_good() -> None:
    assert CWVMeasurer._rate_lcp(2000) == "good"
    assert CWVMeasurer._rate_lcp(2500) == "good"


def test_rate_lcp_needs_improvement() -> None:
    assert CWVMeasurer._rate_lcp(2501) == "needs-improvement"
    assert CWVMeasurer._rate_lcp(4000) == "needs-improvement"


def test_rate_lcp_poor() -> None:
    assert CWVMeasurer._rate_lcp(4001) == "poor"
    assert CWVMeasurer._rate_lcp(10000) == "poor"


def test_rate_inp_good() -> None:
    assert CWVMeasurer._rate_inp(100) == "good"
    assert CWVMeasurer._rate_inp(200) == "good"


def test_rate_inp_needs_improvement() -> None:
    assert CWVMeasurer._rate_inp(201) == "needs-improvement"
    assert CWVMeasurer._rate_inp(500) == "needs-improvement"


def test_rate_inp_poor() -> None:
    assert CWVMeasurer._rate_inp(501) == "poor"


def test_rate_cls_good() -> None:
    assert CWVMeasurer._rate_cls(0.05) == "good"
    assert CWVMeasurer._rate_cls(0.1) == "good"


def test_rate_cls_needs_improvement() -> None:
    assert CWVMeasurer._rate_cls(0.11) == "needs-improvement"
    assert CWVMeasurer._rate_cls(0.25) == "needs-improvement"


def test_rate_cls_poor() -> None:
    assert CWVMeasurer._rate_cls(0.26) == "poor"


def test_worst_rating() -> None:
    """여러 rating 중 가장 나쁜 것."""
    assert CWVMeasurer._worst_rating("good", "good", "good") == "good"
    assert CWVMeasurer._worst_rating("good", "poor", "needs-improvement") == "poor"
    assert CWVMeasurer._worst_rating("good", "needs-improvement") == "needs-improvement"


# === 2. CWVResult ===

def test_cwvresult_recommendations_lcp() -> None:
    """LCP > 2.5 → 권고."""
    result = CWVResult(
        url="https://example.com",
        lcp_ms=3000,
        inp_ms=100,
        cls=0.05,
        rating="needs-improvement",
        runs=3,
        measured_at="2026-08-02T00:00:00Z",
    )
    recs = result.recommendations()
    assert any("LCP" in r for r in recs)


def test_cwvresult_recommendations_inp() -> None:
    """INP > 200 → 권고."""
    result = CWVResult(
        url="https://example.com",
        lcp_ms=1500,
        inp_ms=300,
        cls=0.05,
        rating="needs-improvement",
        runs=3,
        measured_at="2026-08-02T00:00:00Z",
    )
    recs = result.recommendations()
    assert any("INP" in r for r in recs)


def test_cwvresult_recommendations_cls() -> None:
    """CLS > 0.1 → 권고."""
    result = CWVResult(
        url="https://example.com",
        lcp_ms=1500,
        inp_ms=100,
        cls=0.2,
        rating="needs-improvement",
        runs=3,
        measured_at="2026-08-02T00:00:00Z",
    )
    recs = result.recommendations()
    assert any("CLS" in r for r in recs)


def test_cwvresult_no_recommendations_when_good() -> None:
    """모든 지표 Good → 권고 없음."""
    result = CWVResult(
        url="https://example.com",
        lcp_ms=1500,
        inp_ms=100,
        cls=0.05,
        rating="good",
        runs=3,
        measured_at="2026-08-02T00:00:00Z",
    )
    assert result.recommendations() == []


def test_cwvresult_to_dict() -> None:
    """to_dict 직렬화."""
    result = CWVResult(
        url="https://example.com",
        lcp_ms=1500.0,
        inp_ms=100.0,
        cls=0.05,
        rating="good",
        runs=3,
        measured_at="2026-08-02",
    )
    d = result.to_dict()
    assert d["lcp_ms"] == 1500.0
    assert d["url"] == "https://example.com"
