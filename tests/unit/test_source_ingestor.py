"""Unit tests for source_ingestor (URL/PDF ingestion)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from wp_auto.ai.source_ingestor import (
    DEFAULT_SUMMARY_CHARS,
    ExtractedText,
    SourceRef,
    extract_key_facts,
    ingest_pdf,
    ingest_sources,
    ingest_url,
)


# ---------------------------------------------------------------------------
# SourceRef
# ---------------------------------------------------------------------------


class TestSourceRef:
    def test_from_url(self) -> None:
        ref = SourceRef.from_url("https://example.com/article/123")
        assert ref.url == "https://example.com/article/123"
        assert ref.path == ""
        assert ref.source_type == "url"
        assert ref.label  # auto-generated

    def test_from_url_invalid_scheme(self) -> None:
        with pytest.raises(ValueError, match="Invalid URL scheme"):
            SourceRef.from_url("ftp://example.com")

    def test_from_url_empty(self) -> None:
        with pytest.raises(ValueError, match="requires url"):
            SourceRef(url="", source_type="url")

    def test_from_path_pdf(self, tmp_path: Path) -> None:
        pdf = tmp_path / "test.pdf"
        pdf.write_text("dummy")
        ref = SourceRef.from_path(str(pdf))
        assert ref.path == str(pdf)
        assert ref.source_type == "pdf"
        assert ref.label == "test.pdf"

    def test_from_path_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            SourceRef.from_path("/nonexistent/file.pdf")

    def test_from_path_empty(self) -> None:
        with pytest.raises(ValueError, match="requires path"):
            SourceRef(path="", source_type="pdf")

    def test_display_name_url(self) -> None:
        ref = SourceRef.from_url("https://example.com")
        assert "example.com" in ref.display_name

    def test_display_name_path(self, tmp_path: Path) -> None:
        pdf = tmp_path / "doc.pdf"
        pdf.write_text("dummy")
        ref = SourceRef.from_path(str(pdf))
        assert ref.display_name == "doc.pdf"

    def test_post_init_invalid_combination(self) -> None:
        # url=empty, type=url
        with pytest.raises(ValueError):
            SourceRef(url="", path="", source_type="url")
        # path=empty, type=pdf
        with pytest.raises(ValueError):
            SourceRef(url="", path="", source_type="pdf")


# ---------------------------------------------------------------------------
# extract_key_facts (deterministic, no LLM)
# ---------------------------------------------------------------------------


class TestExtractKeyFacts:
    def test_empty_body(self) -> None:
        assert extract_key_facts("") == []
        assert extract_key_facts("   ") == []

    def test_no_facts(self) -> None:
        # 숫자/고유명사 없는 본문
        text = "이것은 그냥 본문입니다. 사실이 없습니다."
        result = extract_key_facts(text)
        # 짧은 문장은 제외됨
        assert result == []

    def test_with_numbers(self) -> None:
        # 50자 이상의 한국어 fact-like 문장
        text = (
            "오늘 증시는 2,500선을 돌파했습니다. 한국 거래소에서 가장 큰 상승폭을 보였습니다. "
            "거래량은 1조원을 넘어섰습니다."
        )
        result = extract_key_facts(text)
        assert len(result) >= 1
        # 숫자 포함 문장이 우선
        for fact in result:
            assert any(c.isdigit() for c in fact)

    def test_with_currency(self) -> None:
        text = (
            "애플 시가총액은 $3 trillion을 돌파했다. 이는 사상 최고치다. "
            "테슬라도 $1 trillion을 기록했다."
        )
        result = extract_key_facts(text)
        assert len(result) >= 1
        # 통화 포함
        assert any("$" in f or "₩" in f or "€" in f for f in result)

    def test_with_percentage(self) -> None:
        # 한국어 fact-like 문장 (각 25자 이상)
        text = (
            "미국 실업률은 3.5%로 하락했다. 노동 시장이 빠르게 회복되고 있는 신호다. "
            "한국 경제 성장률은 2.8% 증가했다. 이는 5년 만에 가장 높은 수치다."
        )
        result = extract_key_facts(text)
        assert len(result) >= 1
        assert any("%" in f or "퍼센트" in f for f in result)

    def test_max_facts_limit(self) -> None:
        text = " ".join(
            f"오늘 {i}번째 사실은 {i*10}개의 데이터를 보여줍니다." for i in range(20)
        )
        result = extract_key_facts(text, max_facts=5)
        assert len(result) <= 5

    def test_dedup_by_prefix(self) -> None:
        text = (
            "오늘 증시는 2,500선을 돌파했습니다. 한국 거래소에서 가장 큰 상승폭을 보였습니다. "
            "오늘 증시는 2,500선을 돌파했습니다. 한국 거래소에서 가장 큰 상승폭을 보였습니다."
        )
        result = extract_key_facts(text)
        # 앞 50자 기준 dedup
        assert len(result) == 1

    def test_length_filter(self) -> None:
        # 너무 짧은 문장 (20자 미만)
        text = "짧음."
        result = extract_key_facts(text)
        assert result == []
        # 너무 긴 문장 (350자 초과)
        text = "이것은 매우 긴 문장입니다. " * 30
        result = extract_key_facts(text)
        assert result == []

    def test_english_proper_nouns(self) -> None:
        text = "Joe Biden met with Xi Jinping in San Francisco. The two leaders discussed trade."
        result = extract_key_facts(text)
        assert len(result) >= 1
        # 고유명사 or 숫자 포함
        assert any(c.isupper() for c in " ".join(result))


# ---------------------------------------------------------------------------
# ingest_url (with mocked trafilatura)
# ---------------------------------------------------------------------------


class TestIngestUrl:
    def test_ingest_url_success(self) -> None:
        mock_extracted_json = """{
            "title": "Test Article",
            "text": "This is the body text. It has some content. Apple stock rose 5% today.",
            "description": "Test description",
            "sitename": "Test News",
            "url": "https://example.com/article/123",
            "hostname": "example.com",
            "date": "2026-08-04",
            "author": "Test Author",
            "language": "en"
        }"""
        with patch("trafilatura.fetch_url", return_value="<html>mock</html>"):
            with patch("trafilatura.extract", return_value=mock_extracted_json):
                ref = SourceRef.from_url("https://example.com/article/123")
                result = ingest_url(ref)

        assert isinstance(result, ExtractedText)
        assert result.title == "Test Article"
        assert "Apple stock" in result.body
        assert result.metadata["sitename"] == "Test News"
        assert result.metadata["date"] == "2026-08-04"
        assert result.char_count == len(result.body)
        assert result.summary  # auto-generated

    def test_ingest_url_wrong_type(self) -> None:
        ref = SourceRef(path="/tmp/test.pdf", source_type="pdf")
        with pytest.raises(ValueError, match="source_type='url'"):
            ingest_url(ref)

    def test_ingest_url_fetch_failure(self) -> None:
        with patch("trafilatura.fetch_url", return_value=None):
            ref = SourceRef.from_url("https://example.com/404")
            with pytest.raises(RuntimeError, match="fetch 실패"):
                ingest_url(ref)

    def test_ingest_url_no_extraction(self) -> None:
        with patch("trafilatura.fetch_url", return_value="<html>mock</html>"):
            with patch("trafilatura.extract", return_value=""):
                ref = SourceRef.from_url("https://example.com/empty")
                with pytest.raises(RuntimeError, match="본문 추출 실패"):
                    ingest_url(ref)

    def test_ingest_url_json_parse_error(self) -> None:
        with patch("trafilatura.fetch_url", return_value="<html>mock</html>"):
            with patch("trafilatura.extract", return_value="not valid json {{{"):
                ref = SourceRef.from_url("https://example.com/bad")
                with pytest.raises(RuntimeError, match="JSON 파싱"):
                    ingest_url(ref)

    def test_ingest_url_empty_body(self) -> None:
        mock_extracted_json = '{"title": "Empty", "text": ""}'
        with patch("trafilatura.fetch_url", return_value="<html>mock</html>"):
            with patch("trafilatura.extract", return_value=mock_extracted_json):
                ref = SourceRef.from_url("https://example.com/empty")
                with pytest.raises(RuntimeError, match="본문 비어있음"):
                    ingest_url(ref)


# ---------------------------------------------------------------------------
# ingest_pdf (with mocked fitz)
# ---------------------------------------------------------------------------


class TestIngestPdf:
    def test_ingest_pdf_success(self, tmp_path: Path) -> None:
        # Mock fitz (PyMuPDF)
        mock_doc = MagicMock()
        mock_doc.metadata = {
            "title": "Test PDF Document",
            "author": "Test Author",
            "creationDate": "2026-08-04",
        }
        mock_doc.page_count = 3
        mock_doc.__enter__ = MagicMock(return_value=mock_doc)
        mock_doc.__exit__ = MagicMock(return_value=False)

        mock_page1 = MagicMock()
        mock_page1.get_text.return_value = "This is page 1. With 100 words of content."
        mock_page2 = MagicMock()
        mock_page2.get_text.return_value = "Page 2 has different content. $50 billion in revenue."
        mock_page3 = MagicMock()
        mock_page3.get_text.return_value = "Page 3 concludes. 25% growth expected."

        mock_doc.load_page.side_effect = [mock_page1, mock_page2, mock_page3]
        mock_doc.close = MagicMock()

        with patch.dict("sys.modules", {"fitz": MagicMock(open=MagicMock(return_value=mock_doc))}):
            # Ensure fitz is importable
            import sys as _sys
            _sys.modules["fitz"] = MagicMock(open=MagicMock(return_value=mock_doc), __version__="1.28.0")
            try:
                import fitz  # noqa: F401
            except ImportError:
                pytest.skip("PyMuPDF not installed")

            pdf = tmp_path / "test.pdf"
            pdf.write_text("dummy")
            ref = SourceRef.from_path(str(pdf))
            result = ingest_pdf(ref)

        assert result.title == "Test PDF Document"
        assert "page 1" in result.body
        assert "$50 billion" in result.body
        assert "[p.1]" in result.body
        assert result.metadata["page_count"] == 3
        assert result.metadata["author"] == "Test Author"

    def test_ingest_pdf_wrong_type(self) -> None:
        ref = SourceRef.from_url("https://example.com")
        with pytest.raises(ValueError, match="source_type='pdf'"):
            ingest_pdf(ref)

    def test_ingest_pdf_not_found(self) -> None:
        ref = SourceRef(path="/nonexistent/file.pdf", source_type="pdf")
        with pytest.raises(FileNotFoundError):
            ingest_pdf(ref)

    def test_ingest_pdf_no_text(self, tmp_path: Path) -> None:
        mock_doc = MagicMock()
        mock_doc.metadata = {"title": "Empty PDF"}
        mock_doc.page_count = 1
        mock_page = MagicMock()
        mock_page.get_text.return_value = ""
        mock_doc.load_page.return_value = mock_page
        mock_doc.close = MagicMock()

        import sys as _sys
        _sys.modules["fitz"] = MagicMock(open=MagicMock(return_value=mock_doc), __version__="1.28.0")

        pdf = tmp_path / "empty.pdf"
        pdf.write_text("dummy")
        ref = SourceRef.from_path(str(pdf))
        with pytest.raises(RuntimeError, match="PDF 본문 추출 실패"):
            ingest_pdf(ref)

    def test_ingest_pdf_max_pages_truncation(self, tmp_path: Path) -> None:
        """max_pages 초과 시 일부만 추출 + metadata.truncated."""
        mock_doc = MagicMock()
        mock_doc.metadata = {"title": "Big PDF"}
        mock_doc.page_count = 50
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Page content. " * 100  # long content
        mock_doc.load_page.return_value = mock_page
        mock_doc.close = MagicMock()

        import sys as _sys
        _sys.modules["fitz"] = MagicMock(open=MagicMock(return_value=mock_doc), __version__="1.28.0")

        pdf = tmp_path / "big.pdf"
        pdf.write_text("dummy")
        ref = SourceRef.from_path(str(pdf))
        result = ingest_pdf(ref, max_pages=5)

        assert result.metadata.get("truncated") is True
        assert result.metadata["original_page_count"] == 50


# ---------------------------------------------------------------------------
# ingest_sources (multi)
# ---------------------------------------------------------------------------


class TestIngestSources:
    def test_ingest_sources_mixed(self, tmp_path: Path) -> None:
        # Mock ingest_url + ingest_pdf
        mock_url_text = ExtractedText(
            title="URL Article",
            body="URL body content. Apple rose 5% today.",
            source=SourceRef.from_url("https://example.com/1"),
        )
        pdf = tmp_path / "doc.pdf"
        pdf.write_text("dummy")
        pdf_ref = SourceRef.from_path(str(pdf))
        mock_pdf_text = ExtractedText(
            title="PDF Doc",
            body="PDF body content. Tesla grew 10% this quarter.",
            source=pdf_ref,
        )

        with patch("wp_auto.ai.source_ingestor.ingest_url", return_value=mock_url_text):
            with patch("wp_auto.ai.source_ingestor.ingest_pdf", return_value=mock_pdf_text):
                refs = [
                    SourceRef.from_url("https://example.com/1"),
                    pdf_ref,
                ]
                results = ingest_sources(refs)

        assert len(results) == 2
        assert results[0].title == "URL Article"
        assert results[1].title == "PDF Doc"

    def test_ingest_sources_partial_failure(self, tmp_path: Path) -> None:
        # 1개만 성공
        mock_url_text = ExtractedText(
            title="URL Article",
            body="URL body content.",
            source=SourceRef.from_url("https://example.com/1"),
        )

        with patch("wp_auto.ai.source_ingestor.ingest_url", return_value=mock_url_text):
            with patch(
                "wp_auto.ai.source_ingestor.ingest_pdf",
                side_effect=RuntimeError("PDF 오류"),
            ):
                pdf = tmp_path / "bad.pdf"
                pdf.write_text("dummy")
                refs = [
                    SourceRef.from_url("https://example.com/1"),
                    SourceRef.from_path(str(pdf)),
                ]
                results = ingest_sources(refs)

        # 1개만 성공
        assert len(results) == 1
        assert results[0].title == "URL Article"


# ---------------------------------------------------------------------------
# ExtractedText dataclass
# ---------------------------------------------------------------------------


class TestExtractedText:
    def test_post_init_summary_auto(self) -> None:
        body = "A" * 3000
        ref = SourceRef.from_url("https://example.com")
        ext = ExtractedText(
            title="Test",
            body=body,
            source=ref,
        )
        # summary 자동 생성
        assert ext.summary
        assert len(ext.summary) <= DEFAULT_SUMMARY_CHARS + 10

    def test_post_init_key_facts_auto(self) -> None:
        body = (
            "Apple stock rose 5% today according to the latest market report. "
            "Tesla grew 10% this quarter, beating analyst expectations significantly."
        )
        ref = SourceRef.from_url("https://example.com")
        ext = ExtractedText(
            title="Test",
            body=body,
            source=ref,
        )
        assert len(ext.key_facts) >= 1

    def test_char_count_auto(self) -> None:
        ref = SourceRef.from_url("https://example.com")
        ext = ExtractedText(
            title="Test",
            body="12345",
            source=ref,
        )
        assert ext.char_count == 5

    def test_explicit_summary_not_overridden(self) -> None:
        ref = SourceRef.from_url("https://example.com")
        ext = ExtractedText(
            title="Test",
            body="long body " * 100,
            source=ref,
            summary="my custom summary",
        )
        assert ext.summary == "my custom summary"
