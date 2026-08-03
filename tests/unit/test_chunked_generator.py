"""ChunkedContentGenerator + PillarCluster 테스트."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from wp_auto.ai.chunked_generator import (
    ChunkedContentGenerator,
    ChunkedPost,
    PillarCluster,
    Subtopic,
)
from wp_auto.ai.content_generator import Outline
from wp_auto.ai.ollama_client import MockOllamaClient

PROMPTS_DIR = None  # 기본값 사용


# ---------------------------------------------------------------------------
# MockOllamaClient helper — 한국어/영문 prompt에 unique한 keyword로 매칭
# ---------------------------------------------------------------------------

def make_mock_client(*, lang: str = "ko") -> MockOllamaClient:
    """plan / body / pillar prompt 각각의 unique 키워드로 매칭되는 mock."""
    if lang == "ko":
        return MockOllamaClient({
            # chunk_plan prompt에는 "subtopics"라는 단어가 JSON 예시에 있음
            "subtopics": (
                '{"subtopics": ['
                '{"id": "background", "title": "배경", "summary": "기본 맥락", "focus_keyword": "워드프레스"},'
                '{"id": "method", "title": "방법", "summary": "핵심 방법", "focus_keyword": "SEO"},'
                '{"id": "example", "title": "예시", "summary": "실제 사례", "focus_keyword": "예시"},'
                '{"id": "summary", "title": "정리", "summary": "마무리", "focus_keyword": "정리"}'
                ']}'
            ),
            # chunk_body prompt에는 "Hook intro"라는 고유 단어
            "Hook intro": "<p>Mock chunk body in Korean. hook + 핵심 + 실전 적용.</p>",
            # pillar prompt에는 "Table of Contents"라는 고유 단어
            "Table of Contents": (
                "<p>Mock pillar intro.</p>"
                "<h2>목차 (Table of Contents)</h2>"
                "<ol><li><a href='#background'>1. 배경</a></li></ol>"
                "<p>결론 + CTA.</p>"
            ),
        })
    else:
        return MockOllamaClient({
            "subtopics": (
                '{"subtopics": ['
                '{"id": "background", "title": "Background", "summary": "ctx", "focus_keyword": "x"},'
                '{"id": "method", "title": "Method", "summary": "how", "focus_keyword": "y"}'
                ']}'
            ),
            "Hook intro": "<p>Mock English chunk body.</p>",
            "Table of Contents": "<p>Mock pillar.</p><h2>Table of Contents</h2><p>...</p>",
        })


@pytest.fixture
def mock_client() -> MockOllamaClient:
    return make_mock_client(lang="ko")


@pytest.fixture
def sample_outline() -> Outline:
    return Outline(
        title="워드프레스 SEO 가이드",
        meta_description="워드프레스 SEO 핵심 가이드",
        slug="wordpress-seo",
        outline=[
            {"h2": "워드프레스 SEO란", "h3": ["정의", "중요성"]},
            {"h2": "핵심 전략", "h3": ["키워드", "콘텐츠"]},
            {"h2": "실전 적용", "h3": ["예시"]},
        ],
        faq=[{"q": "Q1", "a": "A1"}],
        key_takeaways=["핵심1", "핵심2"],
    )


# ---------------------------------------------------------------------------
# 데이터 모델
# ---------------------------------------------------------------------------

def test_subtopic_dataclass() -> None:
    s = Subtopic(id="background", title="배경", summary="...")
    assert s.id == "background"
    assert s.focus_keyword == ""


def test_chunked_post_dataclass() -> None:
    c = ChunkedPost(
        subtopic_id="background", title="t", body_html="<p>x</p>", meta_description="m"
    )
    assert c.prev_slug is None
    assert c.next_slug is None
    assert c.related_slugs == []


# ---------------------------------------------------------------------------
# ChunkedContentGenerator
# ---------------------------------------------------------------------------

def test_plan_subtopics_korean(mock_client: MockOllamaClient, sample_outline: Outline) -> None:
    gen = ChunkedContentGenerator(mock_client)
    subs = gen.plan_subtopics(sample_outline, language="ko")
    assert len(subs) == 4
    assert subs[0].id == "background"
    assert subs[0].title == "배경"
    assert subs[1].focus_keyword == "SEO"


def test_plan_subtopics_fallback_on_invalid_json(
    mock_client: MockOllamaClient, sample_outline: Outline
) -> None:
    """JSON parse 실패 시 outline H2 → Subtopic fallback."""
    client = MockOllamaClient({"subtopics": "not valid json"})
    gen = ChunkedContentGenerator(client)
    subs = gen.plan_subtopics(sample_outline, language="ko")
    assert len(subs) == len(sample_outline.outline)  # fallback: H2 1개 = 1 subtopic
    assert subs[0].id == "h2-0"


def test_generate_chunks_count_and_navigation(
    mock_client: MockOllamaClient, sample_outline: Outline
) -> None:
    gen = ChunkedContentGenerator(mock_client)
    subs = gen.plan_subtopics(sample_outline, language="ko")
    chunks = gen.generate_chunks(sample_outline, subs, language="ko")
    assert len(chunks) == len(subs)
    # prev/next chain
    assert chunks[0].prev_slug is None
    assert chunks[0].next_slug == chunks[1].slug
    assert chunks[-1].next_slug is None
    assert chunks[-1].prev_slug == chunks[-2].slug
    # related = 1개 (이웃 1개)
    assert all(len(c.related_slugs) >= 1 for c in chunks[1:-1])


def test_generate_pillar_with_chunks(
    mock_client: MockOllamaClient, sample_outline: Outline
) -> None:
    gen = ChunkedContentGenerator(mock_client)
    subs = gen.plan_subtopics(sample_outline, language="ko")
    chunks = gen.generate_chunks(sample_outline, subs, language="ko")
    pillar = gen.generate_pillar(sample_outline, subs, chunks, language="ko")
    assert pillar.subtopic_id == "pillar"
    assert "Mock pillar" in pillar.body_html or "목차" in pillar.body_html
    assert pillar.next_slug == chunks[0].slug


def test_generate_pillar_cluster_all_in_one(
    mock_client: MockOllamaClient, sample_outline: Outline
) -> None:
    gen = ChunkedContentGenerator(mock_client)
    cluster = gen.generate_pillar_cluster(sample_outline, language="ko")
    assert isinstance(cluster, PillarCluster)
    assert len(cluster.chunks) >= 2
    assert cluster.pillar.subtopic_id == "pillar"
    assert cluster.topic == sample_outline.title
    assert cluster.category.startswith("chunked-")


# ---------------------------------------------------------------------------
# target_chunks (chunk_plan 개선: 정확히 N개 생성)
# ---------------------------------------------------------------------------

def test_plan_subtopics_target_chunks_truncates_excess(
    mock_client: MockOllamaClient, sample_outline: Outline
) -> None:
    """LLM이 N+1 반환하면 target_chunks로 truncate."""
    gen = ChunkedContentGenerator(mock_client)
    # mock client는 4개 반환. target_chunks=2로 truncate.
    subs = gen.plan_subtopics(sample_outline, language="ko", target_chunks=2)
    assert len(subs) == 2
    # 가장 앞 2개만 살아남음
    assert subs[0].id == "background"
    assert subs[1].id == "method"


def test_plan_subtopics_target_chunks_warns_when_fewer(
    mock_client: MockOllamaClient, sample_outline: Outline
) -> None:
    """LLM이 적게 반환하면 warning + 그대로."""
    gen = ChunkedContentGenerator(mock_client)
    # mock client는 4개 반환. target_chunks=8 요청 → 4개 그대로.
    subs = gen.plan_subtopics(sample_outline, language="ko", target_chunks=8)
    assert len(subs) == 4  # 부족해도 그대로


def test_plan_subtopics_includes_target_chunks_in_prompt(
    mock_client: MockOllamaClient, sample_outline: Outline
) -> None:
    """plan prompt에 {target_chunks} 변수가 정확히 주입되는지."""
    # generate 호출을 MagicMock으로 wrap해서 인자 캡처
    mock_client.generate = MagicMock(wraps=mock_client.generate)  # type: ignore[method-assign]

    gen = ChunkedContentGenerator(mock_client, target_chunks=7)
    gen.plan_subtopics(sample_outline, language="ko")

    # generate 호출의 첫 번째 위치 인자 = prompt
    assert mock_client.generate.call_count == 1
    prompt = mock_client.generate.call_args.args[0]
    assert "7" in prompt  # target_chunks=7이 prompt에 들어감
    assert "정확히 7" in prompt or "7개" in prompt or "목표 chunk 수" in prompt


def test_plan_subtopics_overrides_constructor_target(
    mock_client: MockOllamaClient, sample_outline: Outline
) -> None:
    """plan_subtopics(target_chunks=...)가 생성자 값을 override."""
    gen = ChunkedContentGenerator(mock_client, target_chunks=5)
    subs = gen.plan_subtopics(sample_outline, language="ko", target_chunks=2)
    assert len(subs) == 2  # override된 2로 truncate


def test_generate_pillar_cluster_with_target_chunks(
    mock_client: MockOllamaClient, sample_outline: Outline
) -> None:
    """generate_pillar_cluster에 target_chunks 전달."""
    gen = ChunkedContentGenerator(mock_client)
    cluster = gen.generate_pillar_cluster(
        sample_outline, language="ko", target_chunks=3
    )
    assert len(cluster.chunks) == 3


def test_target_chunks_default_is_5(mock_client: MockOllamaClient) -> None:
    """DEFAULT_TARGET_CHUNKS = 5."""
    gen = ChunkedContentGenerator(mock_client)
    assert gen.target_chunks == 5


def test_stitch_single_contains_all_chunks(
    mock_client: MockOllamaClient, sample_outline: Outline
) -> None:
    gen = ChunkedContentGenerator(mock_client)
    cluster = gen.generate_pillar_cluster(sample_outline, language="ko")
    html = cluster.stitch_single()
    # pillar + all chunk titles
    assert "Mock pillar" in html or "Mock chunk" in html
    for ch in cluster.chunks:
        assert ch.title in html
        assert ch.slug in html
    # chunk-nav가 각 chunk 다음에 있어야 함
    assert html.count("chunk-nav") == len(cluster.chunks)


def test_to_wp_post_specs_pillar_plus_n_chunks(
    mock_client: MockOllamaClient, sample_outline: Outline
) -> None:
    gen = ChunkedContentGenerator(mock_client)
    cluster = gen.generate_pillar_cluster(sample_outline, language="ko")
    specs = cluster.to_wp_post_specs()
    # pillar 1 + chunks N
    assert len(specs) == 1 + len(cluster.chunks)
    assert specs[0]["type"] == "pillar"
    assert all(s["type"] == "chunk" for s in specs[1:])
    # 모든 spec이 publishable 형식
    for s in specs:
        assert "title" in s
        assert "content" in s
        assert "slug" in s
        assert "excerpt" in s
