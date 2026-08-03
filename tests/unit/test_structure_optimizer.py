"""StructureOptimizer 단위 테스트."""
from __future__ import annotations

import pytest

from wp_auto.ai.structure_optimizer import StructureOptimizer


@pytest.fixture
def optimizer_ko() -> StructureOptimizer:
    return StructureOptimizer(author_name="테스트", language="ko")


@pytest.fixture
def optimizer_en() -> StructureOptimizer:
    return StructureOptimizer(author_name="Test Author", language="en")


# ---------------------------------------------------------------------------
# wrap_tldr
# ---------------------------------------------------------------------------

def test_wrap_tldr_ko(optimizer_ko: StructureOptimizer) -> None:
    body = "<p>본문</p>"
    out = optimizer_ko.wrap_tldr(body, "한 줄 요약입니다")
    assert "한 줄 요약입니다" in out
    assert "TL;DR" in out
    assert "본문" in out


def test_wrap_tldr_en(optimizer_en: StructureOptimizer) -> None:
    body = "<p>body</p>"
    out = optimizer_en.wrap_tldr(body, "Summary here")
    assert "Summary here" in out
    assert "TL;DR" in out


def test_wrap_tldr_empty_skipped(optimizer_ko: StructureOptimizer) -> None:
    body = "<p>본문</p>"
    out = optimizer_ko.wrap_tldr(body, "")
    assert out == body


# ---------------------------------------------------------------------------
# wrap_faq
# ---------------------------------------------------------------------------

def test_wrap_faq_ko(optimizer_ko: StructureOptimizer) -> None:
    body = "<p>본문</p>"
    faqs = [
        {"q": "Q1?", "a": "A1"},
        {"q": "Q2?", "a": "A2"},
    ]
    out = optimizer_ko.wrap_faq(body, faqs)
    assert "Q1?" in out
    assert "A1" in out
    assert "Q2?" in out
    assert "FAQ" in out
    # HTML structure
    assert "<details" in out
    assert "<summary" in out


def test_wrap_faq_en(optimizer_en: StructureOptimizer) -> None:
    body = "<p>body</p>"
    faqs = [{"q": "Q?", "a": "A"}]
    out = optimizer_en.wrap_faq(body, faqs)
    assert "Q?" in out
    assert "Frequently Asked" in out


def test_wrap_faq_empty_skipped(optimizer_ko: StructureOptimizer) -> None:
    body = "<p>본문</p>"
    out = optimizer_ko.wrap_faq(body, [])
    assert out == body


# ---------------------------------------------------------------------------
# wrap_related
# ---------------------------------------------------------------------------

def test_wrap_related_ko(optimizer_ko: StructureOptimizer) -> None:
    body = "<p>본문</p>"
    items = [
        {"title": "관련 글 1", "url": "/p1", "description": "설명 1"},
        {"title": "관련 글 2", "url": "/p2"},
    ]
    out = optimizer_ko.wrap_related(body, items)
    assert "관련 글 1" in out
    assert "관련 글 2" in out
    assert "/p1" in out
    assert "설명 1" in out
    # description 없는 경우 description div 없음
    assert "설명 2" not in out


def test_wrap_related_en(optimizer_en: StructureOptimizer) -> None:
    body = "<p>body</p>"
    items = [{"title": "Related 1", "url": "/r1"}]
    out = optimizer_en.wrap_related(body, items)
    assert "Related 1" in out
    assert "Related Articles" in out


def test_wrap_related_empty_skipped(optimizer_ko: StructureOptimizer) -> None:
    body = "<p>본문</p>"
    out = optimizer_ko.wrap_related(body, [])
    assert out == body


# ---------------------------------------------------------------------------
# append_eeat
# ---------------------------------------------------------------------------

def test_append_eeat_ko(optimizer_ko: StructureOptimizer) -> None:
    body = "<p>본문</p>"
    out = optimizer_ko.append_eeat(body)
    assert "테스트" in out  # author
    assert "AI로 초안" in out  # KO 안내
    assert "<hr" in out  # separator


def test_append_eeat_en(optimizer_en: StructureOptimizer) -> None:
    body = "<p>body</p>"
    out = optimizer_en.append_eeat(body)
    assert "Test Author" in out
    assert "AI assistance" in out


# ---------------------------------------------------------------------------
# optimize_pillar (통합)
# ---------------------------------------------------------------------------

def test_optimize_pillar_full_ko(optimizer_ko: StructureOptimizer) -> None:
    body = "<p>본문</p>"
    out = optimizer_ko.optimize_pillar(
        body,
        tldr="한 줄 요약",
        faqs=[{"q": "Q?", "a": "A"}],
        related_items=[{"title": "관련", "url": "/x"}],
    )
    assert "한 줄 요약" in out
    assert "Q?" in out
    assert "관련" in out
    assert "테스트" in out
    # 순서: TL;DR → body → FAQ → Related → E-E-A-T
    tldr_pos = out.index("한 줄 요약")
    body_pos = out.index("본문")
    faq_pos = out.index("Q?")
    related_pos = out.index("관련")
    eeat_pos = out.index("테스트")
    assert tldr_pos < body_pos < faq_pos < related_pos < eeat_pos


def test_optimize_pillar_no_tldr(optimizer_ko: StructureOptimizer) -> None:
    body = "<p>본문</p>"
    out = optimizer_ko.optimize_pillar(body, tldr="", faqs=None, related_items=None)
    # TL;DR 없으면 body만 + E-E-A-T
    assert "본문" in out
    assert "테스트" in out
    assert "TL;DR" not in out


# ---------------------------------------------------------------------------
# optimize_chunk (관련 + E-E-A-T만, TL;DR/FAQ 없음)
# ---------------------------------------------------------------------------

def test_optimize_chunk_ko(optimizer_ko: StructureOptimizer) -> None:
    body = "<p>본문</p>"
    out = optimizer_ko.optimize_chunk(
        body, related_items=[{"title": "관련", "url": "/x"}]
    )
    assert "관련" in out
    assert "테스트" in out
    # TL;DR / FAQ는 없어야 함
    assert "TL;DR" not in out
    assert "FAQ" not in out


def test_optimize_chunk_no_related(optimizer_ko: StructureOptimizer) -> None:
    body = "<p>본문</p>"
    out = optimizer_ko.optimize_chunk(body, related_items=None)
    assert "본문" in out
    assert "테스트" in out
    assert "관련" not in out  # related 섹션 없음
