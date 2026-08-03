"""Unit tests for researcher.py (fair-use source → outline)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from wp_auto.ai.content_generator import Outline
from wp_auto.ai.ollama_client import LLMClient
from wp_auto.ai.researcher import (
    MAX_BODY_CHARS_PER_SOURCE,
    MAX_FACTS_PER_SOURCE,
    ResearchContext,
    Researcher,
)
from wp_auto.ai.source_ingestor import ExtractedText, SourceRef


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _make_source(title: str, body: str, source_type: str = "url") -> ExtractedText:
    """테스트용 ExtractedText 생성."""
    if source_type == "url":
        ref = SourceRef.from_url("https://example.com/test")
    else:
        # PDF는 path 필요 — 임시 처리
        ref = SourceRef(path="dummy.pdf", source_type="pdf")
    return ExtractedText(
        title=title,
        body=body,
        source=ref,
    )


# ---------------------------------------------------------------------------
# ResearchContext
# ---------------------------------------------------------------------------


class TestResearchContext:
    def test_to_dict(self) -> None:
        src = _make_source("Test Article", "Some body content. Apple rose 5% today.")
        ctx = ResearchContext(
            topic="테스트 주제",
            keyword="테스트",
            intent="informational",
            sources=[src],
            language="ko",
            target_length=2000,
            category="tech",
            notes="한국 독자",
        )
        d = ctx.to_dict()
        assert d["topic"] == "테스트 주제"
        assert d["keyword"] == "테스트"
        assert d["intent"] == "informational"
        assert d["language"] == "ko"
        assert d["target_length"] == 2000
        assert d["source_count"] == 1
        assert d["notes"] == "한국 독자"


# ---------------------------------------------------------------------------
# Researcher._build_source_excerpts (fair use)
# ---------------------------------------------------------------------------


class TestBuildSourceExcerpts:
    def test_extracts_key_facts_only(self) -> None:
        """Fair use: 핵심 fact만 발췌, 본문 전체 X."""
        body = "Apple stock rose 5% today. " * 100  # 본문이 매우 길어도
        src = _make_source("Test", body)
        researcher = Researcher(client=MagicMock(spec=LLMClient), max_facts_per_source=5)

        excerpts = researcher._build_source_excerpts([src])

        # 발췌에 key facts가 포함되어야 함
        assert "Key facts" in excerpts
        # 원문 전체는 포함 ❌
        assert body not in excerpts
        # body excerpt (max 1500자)만 포함
        assert "Body excerpt" in excerpts

    def test_respects_max_facts_limit(self) -> None:
        body = " ".join(
            f"Fact {i}: Apple stock rose {i}% today."
            for i in range(20)
        )
        src = _make_source("Test", body)
        researcher = Researcher(client=MagicMock(spec=LLMClient), max_facts_per_source=3)
        excerpts = researcher._build_source_excerpts([src])

        # "Key facts" 섹션에 3개만 있어야 함
        # 1) "Key facts" 이후 "Body excerpt" 전까지의 라인 수
        import re as _re
        facts_section = excerpts.split("**Key facts")[1].split("**Body excerpt")[0]
        facts = _re.findall(r"^\s+\d+\.\s", facts_section, _re.MULTILINE)
        assert len(facts) == 3

    def test_truncates_body(self) -> None:
        body = "A" * 10000
        src = _make_source("Test", body)
        researcher = Researcher(
            client=MagicMock(spec=LLMClient),
            max_body_chars_per_source=500,
        )
        excerpts = researcher._build_source_excerpts([src])

        # body excerpt가 500자 제한
        assert "Body excerpt (앞 500자" in excerpts
        # 원문 10000자는 발췌에 없음
        assert "A" * 1000 not in excerpts

    def test_includes_metadata(self) -> None:
        src = _make_source("Test Article", "Body content. Apple rose 5%.")
        src.metadata = {
            "sitename": "Test News",
            "date": "2026-08-04",
            "author": "Test Author",
        }
        researcher = Researcher(client=MagicMock(spec=LLMClient))
        excerpts = researcher._build_source_excerpts([src])

        assert "Test News" in excerpts
        assert "2026-08-04" in excerpts
        assert "Test Author" in excerpts

    def test_multiple_sources(self) -> None:
        src1 = _make_source("Article 1", "Body 1. Apple rose 5%.")
        src2 = _make_source("Article 2", "Body 2. Tesla grew 10%.")
        researcher = Researcher(client=MagicMock(spec=LLMClient))
        excerpts = researcher._build_source_excerpts([src1, src2])

        # 2개 source 모두 포함
        assert "Source 1" in excerpts
        assert "Source 2" in excerpts
        assert "Article 1" in excerpts
        assert "Article 2" in excerpts


# ---------------------------------------------------------------------------
# Researcher.research (LLM 호출)
# ---------------------------------------------------------------------------


class TestResearch:
    def test_research_success(self) -> None:
        # Mock LLM client
        mock_client = MagicMock(spec=LLMClient)
        mock_client.generate.return_value = json.dumps({
            "title": "테스트 글 제목",
            "meta_description": "메타 디스크립션 140자 이상 160자 이하 정도의 길이로 작성된 요약문입니다.",
            "slug": "test-slug",
            "outline": [
                {"h2": "섹션 1", "h3": ["소제목 1-1", "소제목 1-2"]},
                {"h2": "섹션 2", "h3": ["소제목 2-1"]},
            ],
            "faq": [
                {"q": "질문 1?", "a": "답변 1"},
                {"q": "질문 2?", "a": "답변 2"},
            ],
            "key_takeaways": ["결론 1", "결론 2", "결론 3"],
        }, ensure_ascii=False)

        researcher = Researcher(client=mock_client)
        src = _make_source("Test Article", "Body. Apple rose 5% today.")

        ctx = ResearchContext(
            topic="테스트 주제",
            keyword="테스트",
            intent="informational",
            sources=[src],
            language="ko",
        )
        outline = researcher.research(ctx)

        assert isinstance(outline, Outline)
        assert outline.title == "테스트 글 제목"
        assert len(outline.outline) == 2
        assert len(outline.faq) == 2
        assert len(outline.key_takeaways) == 3

        # LLM 호출 확인
        mock_client.generate.assert_called_once()
        call_args = mock_client.generate.call_args
        assert "테스트 주제" in call_args.kwargs["prompt"]
        assert call_args.kwargs["system"].startswith("당신은 한국어")

    def test_research_empty_sources(self) -> None:
        researcher = Researcher(client=MagicMock(spec=LLMClient))
        ctx = ResearchContext(
            topic="Test",
            keyword="test",
            intent="informational",
            sources=[],
        )
        with pytest.raises(ValueError, match="ctx.sources 비어있음"):
            researcher.research(ctx)

    def test_research_unsupported_language(self) -> None:
        researcher = Researcher(client=MagicMock(spec=LLMClient))
        src = _make_source("Test", "Body.")
        ctx = ResearchContext(
            topic="Test",
            keyword="test",
            intent="informational",
            sources=[src],
            language="ja",  # 미지원
        )
        with pytest.raises(ValueError, match="지원 안 되는 language"):
            researcher.research(ctx)

    def test_research_handles_markdown_json(self) -> None:
        """LLM이 ```json ... ```으로 감싸서 응답하는 경우."""
        mock_client = MagicMock(spec=LLMClient)
        mock_client.generate.return_value = (
            "```json\n"
            + json.dumps({
                "title": "Test",
                "meta_description": "x" * 150,
                "slug": "test",
                "outline": [{"h2": "S1", "h3": []}],
                "faq": [{"q": "Q?", "a": "A"}],
                "key_takeaways": ["T1"],
            }, ensure_ascii=False)
            + "\n```"
        )
        researcher = Researcher(client=mock_client)
        src = _make_source("Test", "Body.")
        ctx = ResearchContext(
            topic="T",
            keyword="k",
            intent="informational",
            sources=[src],
            language="ko",
        )
        outline = researcher.research(ctx)
        assert outline.title == "Test"

    def test_research_english_system_prompt(self) -> None:
        mock_client = MagicMock(spec=LLMClient)
        mock_client.generate.return_value = json.dumps({
            "title": "Test",
            "meta_description": "x" * 150,
            "slug": "test",
            "outline": [],
            "faq": [],
            "key_takeaways": [],
        })
        researcher = Researcher(client=mock_client)
        src = _make_source("Test", "Body.")
        ctx = ResearchContext(
            topic="T",
            keyword="k",
            intent="informational",
            sources=[src],
            language="en",
        )
        researcher.research(ctx)
        call_args = mock_client.generate.call_args
        assert call_args.kwargs["system"].startswith("You are a professional English")


# ---------------------------------------------------------------------------
# _extract_response_text
# ---------------------------------------------------------------------------


class TestExtractResponseText:
    def test_string(self) -> None:
        researcher = Researcher(client=MagicMock(spec=LLMClient))
        assert researcher._extract_response_text("hello") == "hello"

    def test_dict_with_response(self) -> None:
        researcher = Researcher(client=MagicMock(spec=LLMClient))
        assert researcher._extract_response_text({"response": "x"}) == "x"
        assert researcher._extract_response_text({"text": "y"}) == "y"
        assert researcher._extract_response_text({"content": "z"}) == "z"
        assert researcher._extract_response_text({"message": "m"}) == "m"

    def test_object(self) -> None:
        class FakeResp:
            response = "fake"

        researcher = Researcher(client=MagicMock(spec=LLMClient))
        assert researcher._extract_response_text(FakeResp()) == "fake"


# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------


def test_constants() -> None:
    assert MAX_FACTS_PER_SOURCE == 8
    assert MAX_BODY_CHARS_PER_SOURCE == 1500
