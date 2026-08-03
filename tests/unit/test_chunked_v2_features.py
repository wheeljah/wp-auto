"""ChunkedContentGenerator v0.5+ 새 동작 테스트 (verify_links, optimize_structure).

기존 chunked 테스트는 새 모듈이 opt-in이라 disabled. 여기서는 명시적으로 ON.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from wp_auto.ai.chunked_generator import ChunkedContentGenerator
from wp_auto.ai.content_generator import Outline
from wp_auto.ai.ollama_client import MockOllamaClient


def make_mock_client() -> MockOllamaClient:
    return MockOllamaClient({
        "subtopics": (
            '{"subtopics": ['
            '{"id": "background", "title": "배경", "summary": "기본 맥락", "focus_keyword": "워드프레스"},'
            '{"id": "method", "title": "방법", "summary": "핵심 방법", "focus_keyword": "SEO"},'
            '{"id": "example", "title": "예시", "summary": "실제 사례", "focus_keyword": "예시"},'
            '{"id": "summary", "title": "정리", "summary": "마무리", "focus_keyword": "정리"}'
            ']}'
        ),
        "단락 chunk": "<p>Mock chunk body with <a href=\"https://example.com/bad\">bad link</a>.</p>",
        "Table of Contents": (
            "<p>Mock pillar intro with <a href=\"https://example.com\">example</a>.</p>"
            "<h2>목차 (Table of Contents)</h2>"
            "<p>결론 + CTA.</p>"
        ),
        "__HOOKS_MARKER__": (
            '{"hooks": ['
            '{"type": "question", "text": "왜 X?", "rationale": "r"},'
            '{"type": "stat", "text": "50%가 Y.", "rationale": "r"},'
            '{"type": "story", "text": "story", "rationale": "r"},'
            '{"type": "reversal", "text": "truth", "rationale": "r"}'
            ']}'
        ),
        "__CTA_MARKER__": (
            '{"ctas": ['
            '{"type": "informational", "text": "더 보기", "placement_hint": "end"},'
            '{"type": "action", "text": "시작", "placement_hint": "btn"},'
            '{"type": "social_proof", "text": "참여", "placement_hint": "foot"}'
            ']}'
        ),
    })


@pytest.fixture
def mock_client() -> MockOllamaClient:
    return make_mock_client()


@pytest.fixture
def sample_outline() -> Outline:
    return Outline(
        title="테스트 글",
        meta_description="테스트 메타 설명",
        slug="test-post",
        outline=[
            {"h2": "배경", "h3": []},
            {"h2": "방법", "h3": []},
        ],
        faq=[{"q": "Q1?", "a": "A1."}],
        key_takeaways=["핵심1"],
    )


# ---------------------------------------------------------------------------
# verify_links ON
# ---------------------------------------------------------------------------

def test_verify_links_default_off(mock_client: MockOllamaClient, sample_outline: Outline) -> None:
    """기본 OFF — broken link가 그대로 남음."""
    gen = ChunkedContentGenerator(mock_client)
    cluster = gen.generate_pillar_cluster(sample_outline, language="ko", target_chunks=2)
    # broken link 그대로 (verify_links=False)
    body = cluster.pillar.body_html + cluster.chunks[0].body_html
    assert "https://example.com" in body


def test_verify_links_on_removes_placeholder(
    mock_client: MockOllamaClient, sample_outline: Outline
) -> None:
    """verify_links=True → placeholder 도메인 자동 제거."""
    with patch("wp_auto.ai.chunked_generator.LinkVerifier") as MockLV:
        # mock이 placeholder 무조건 invalid로
        mock_v = MagicMock()
        from wp_auto.ai.link_verifier import LinkCheckResult
        mock_v.verify_and_clean_html.return_value = (
            "<p>Mock chunk body with bad link.</p>",
            [LinkCheckResult(url="https://example.com/bad", anchor_text="bad link", is_valid=False, error="placeholder")],
        )
        MockLV.return_value = mock_v
        gen = ChunkedContentGenerator(
            mock_client, verify_links=True, optimize_structure=False
        )
        cluster = gen.generate_pillar_cluster(sample_outline, language="ko", target_chunks=2)
        body = cluster.pillar.body_html + cluster.chunks[0].body_html
        assert "https://example.com" not in body


# ---------------------------------------------------------------------------
# optimize_structure ON
# ---------------------------------------------------------------------------

def test_optimize_structure_default_off(
    mock_client: MockOllamaClient, sample_outline: Outline
) -> None:
    """기본 OFF — E-E-A-T footer 없음."""
    gen = ChunkedContentGenerator(mock_client)
    cluster = gen.generate_pillar_cluster(sample_outline, language="ko", target_chunks=2)
    body = cluster.pillar.body_html + cluster.chunks[0].body_html
    assert "wp-auto-eeat" not in body


def test_optimize_structure_on_adds_eeat_to_chunks(
    mock_client: MockOllamaClient, sample_outline: Outline
) -> None:
    """optimize_structure=True → chunk에 E-E-A-T footer 추가."""
    gen = ChunkedContentGenerator(
        mock_client, verify_links=False, optimize_structure=True
    )
    cluster = gen.generate_pillar_cluster(sample_outline, language="ko", target_chunks=2)
    for ch in cluster.chunks:
        assert "wp-auto-eeat" in ch.body_html
        assert "AI로 초안" in ch.body_html


def test_optimize_structure_on_adds_tldr_related_eeat_to_pillar(
    mock_client: MockOllamaClient, sample_outline: Outline
) -> None:
    """optimize_structure=True → pillar에 TL;DR + related + E-E-A-T."""
    gen = ChunkedContentGenerator(
        mock_client, verify_links=False, optimize_structure=True
    )
    cluster = gen.generate_pillar_cluster(sample_outline, language="ko", target_chunks=2)
    body = cluster.pillar.body_html
    assert "wp-auto-tldr" in body
    assert "TL;DR" in body
    assert "wp-auto-related" in body
    assert "wp-auto-eeat" in body


def test_optimize_structure_on_related_uses_chunk_titles(
    mock_client: MockOllamaClient, sample_outline: Outline
) -> None:
    """related_items에 chunk 제목이 들어감."""
    gen = ChunkedContentGenerator(
        mock_client, verify_links=False, optimize_structure=True
    )
    cluster = gen.generate_pillar_cluster(sample_outline, language="ko", target_chunks=2)
    body = cluster.pillar.body_html
    # cluster.chunks의 제목이 related에 들어감
    for ch in cluster.chunks:
        assert ch.title in body


# ---------------------------------------------------------------------------
# 통합: verify_links + optimize_structure + style=trend
# ---------------------------------------------------------------------------

def test_full_integration_trend_style(
    mock_client: MockOllamaClient, sample_outline: Outline
) -> None:
    """모든 기능 ON: verify + optimize + trend style → E-E-A-T footer + structure."""
    gen = ChunkedContentGenerator(
        mock_client, verify_links=False, optimize_structure=True, style="trend"
    )
    cluster = gen.generate_pillar_cluster(sample_outline, language="ko", target_chunks=2)
    # pillar: hook + E-E-A-T
    assert "wp-auto-hook" in cluster.pillar.body_html
    assert "wp-auto-eeat" in cluster.pillar.body_html
    assert "wp-auto-tldr" in cluster.pillar.body_html
    # chunks: E-E-A-T (CTA는 mock이 default response라 fallback 1개만)
    for ch in cluster.chunks:
        assert "wp-auto-eeat" in ch.body_html
