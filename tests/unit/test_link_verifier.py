"""LinkVerifier 단위 테스트.

HTTP 호출 없는 부분 (placeholder 체크, HTML 파싱/치환)만 단위 테스트.
실제 HTTP HEAD/GET 호출은 mock으로 처리.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from wp_auto.ai.link_verifier import (
    KNOWN_PLACEHOLDER_DOMAINS,
    LinkCheckResult,
    LinkVerifier,
)


# ---------------------------------------------------------------------------
# Placeholder 도메인 체크
# ---------------------------------------------------------------------------

def test_is_placeholder_known_domains() -> None:
    v = LinkVerifier()
    for d in KNOWN_PLACEHOLDER_DOMAINS:
        assert v._is_placeholder(f"https://{d}/some/path")
        assert v._is_placeholder(f"http://{d}")


def test_is_placeholder_subdomain() -> None:
    v = LinkVerifier()
    assert v._is_placeholder("https://www.example.com/foo")
    assert v._is_placeholder("https://blog.example.com/post/1")


def test_is_placeholder_real_domain() -> None:
    v = LinkVerifier()
    assert not v._is_placeholder("https://www.hani.co.kr/arti/society/...")
    assert not v._is_placeholder("https://github.com/python/cpython")
    assert not v._is_placeholder("https://www.nytimes.com/2024/01/01/...")


# ---------------------------------------------------------------------------
# HTML 파싱/치환 (verify_and_clean_html의 regex 부분)
# ---------------------------------------------------------------------------

def test_anchor_pattern_extracts_external_links() -> None:
    from wp_auto.ai.link_verifier import ANCHOR_PATTERN
    html = '<p>text <a href="https://example.com">ex</a> and <a href="/internal">int</a>.</p>'
    matches = list(ANCHOR_PATTERN.finditer(html))
    assert len(matches) == 2
    assert matches[0].group(3) == "https://example.com"
    assert matches[1].group(3) == "/internal"


def test_verify_and_clean_html_removes_placeholder() -> None:
    """placeholder 도메인은 무조건 broken 처리 → 텍스트로 변환."""
    v = LinkVerifier()
    html = '<p>See <a href="https://example.com/foo">this example</a> for more.</p>'
    # check_urls를 mock해서 placeholder URL이 invalid로 표시되도록
    with patch.object(v, "check_urls") as mock_check:
        mock_check.return_value = {
            "https://example.com/foo": LinkCheckResult(
                url="https://example.com/foo", anchor_text="this example", is_valid=False, error="placeholder"
            )
        }
        cleaned, removed = v.verify_and_clean_html(html)
    assert "this example" in cleaned  # anchor text는 남음
    assert "https://example.com" not in cleaned
    assert len(removed) == 1


def test_verify_and_clean_html_keeps_valid_links() -> None:
    """유효한 URL은 그대로 유지."""
    v = LinkVerifier()
    html = '<p>Read <a href="https://www.hani.co.kr/article">here</a>.</p>'
    with patch.object(v, "check_urls") as mock_check:
        mock_check.return_value = {
            "https://www.hani.co.kr/article": LinkCheckResult(
                url="https://www.hani.co.kr/article", anchor_text="here", is_valid=True, status_code=200
            )
        }
        cleaned, removed = v.verify_and_clean_html(html)
    assert '<a href="https://www.hani.co.kr/article">here</a>' in cleaned
    assert len(removed) == 0


def test_verify_and_clean_html_handles_internal_links() -> None:
    """내부 링크(/, #chunk- 등)는 검증 스킵하고 그대로 유지."""
    v = LinkVerifier()
    html = (
        '<p>See <a href="/wp/some-post">internal</a> '
        'or <a href="#chunk-background">#anchor</a>.</p>'
    )
    with patch.object(v, "check_urls") as mock_check:
        cleaned, removed = v.verify_and_clean_html(html)
        mock_check.assert_not_called()  # 외부 URL 없어서 호출 안 됨
    assert '<a href="/wp/some-post">internal</a>' in cleaned
    assert '<a href="#chunk-background">#anchor</a>' in cleaned
    assert len(removed) == 0


def test_verify_and_clean_html_handles_mixed() -> None:
    """혼합 케이스: 유효 2, broken 1, 내부 1."""
    v = LinkVerifier()
    html = (
        '<p>Mix:</p>'
        '<ul>'
        '<li><a href="https://valid1.com/a">v1</a></li>'
        '<li><a href="https://example.com/b">broken</a></li>'
        '<li><a href="https://valid2.com/c">v2</a></li>'
        '<li><a href="/internal">int</a></li>'
        '</ul>'
    )
    with patch.object(v, "check_urls") as mock_check:
        mock_check.return_value = {
            "https://valid1.com/a": LinkCheckResult(url="https://valid1.com/a", anchor_text="v1", is_valid=True, status_code=200),
            "https://example.com/b": LinkCheckResult(url="https://example.com/b", anchor_text="broken", is_valid=False, error="placeholder"),
            "https://valid2.com/c": LinkCheckResult(url="https://valid2.com/c", anchor_text="v2", is_valid=True, status_code=200),
        }
        cleaned, removed = v.verify_and_clean_html(html)
    assert '<a href="https://valid1.com/a">v1</a>' in cleaned
    assert '<a href="https://valid2.com/c">v2</a>' in cleaned
    assert "broken" in cleaned
    assert "https://example.com" not in cleaned
    assert len(removed) == 1


def test_verify_and_clean_html_empty() -> None:
    """링크가 없는 HTML은 그대로 반환."""
    v = LinkVerifier()
    html = "<p>just text</p>"
    cleaned, removed = v.verify_and_clean_html(html)
    assert cleaned == html
    assert removed == []


# ---------------------------------------------------------------------------
# check_urls — async 일괄 검증 (mock으로)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_url_placeholder_skips_http() -> None:
    """placeholder URL은 HTTP 호출 없이 invalid 반환."""
    v = LinkVerifier()
    import httpx
    async with httpx.AsyncClient() as client:
        result = await v._check_url(client, "https://example.com")
    assert result.is_valid is False
    assert result.error == "placeholder domain"


@pytest.mark.asyncio
async def test_check_url_200_success() -> None:
    """HEAD 200 → valid."""
    v = LinkVerifier()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.head = AsyncMock(return_value=mock_response)

    result = await v._check_url(mock_client, "https://real.com/page")
    assert result.is_valid is True
    assert result.status_code == 200


@pytest.mark.asyncio
async def test_check_url_404_get_fallback() -> None:
    """HEAD 404 → GET fallback → 404 → invalid."""
    v = LinkVerifier()
    head_resp = MagicMock()
    head_resp.status_code = 404

    get_resp = MagicMock()
    get_resp.status_code = 404

    # async context manager for stream
    class _MockStream:
        async def __aenter__(self):
            return get_resp
        async def __aexit__(self, *args):
            return False

    mock_client = MagicMock()
    mock_client.head = AsyncMock(return_value=head_resp)
    mock_client.stream = MagicMock(return_value=_MockStream())

    result = await v._check_url(mock_client, "https://broken.com/404")
    assert result.is_valid is False


@pytest.mark.asyncio
async def test_check_url_timeout() -> None:
    """HEAD timeout → invalid."""
    v = LinkVerifier()
    import httpx
    mock_client = MagicMock()
    mock_client.head = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
    mock_client.stream = MagicMock(side_effect=httpx.TimeoutException("timeout"))

    result = await v._check_url(mock_client, "https://slow.com/")
    assert result.is_valid is False
    assert "timeout" in result.error.lower() or "timeout" in str(result.error).lower()
