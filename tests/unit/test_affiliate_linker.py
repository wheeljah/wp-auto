"""AffiliateLinker 단위 테스트 (FTC + Amazon Associates 1차 출처 기반)."""
from __future__ import annotations

import re

import pytest

from wp_auto.ai.affiliate_linker import (
    AMAZON_DISCLOSURE,
    AffiliateLinker,
    GENERIC_DISCLOSURE,
)


@pytest.fixture
def linker() -> AffiliateLinker:
    return AffiliateLinker(network="amazon", amazon_tag="myblog-20", language="ko")


# ---------------------------------------------------------------------------
# Amazon URL 빌드
# ---------------------------------------------------------------------------

def test_build_amazon_url_basic(linker: AffiliateLinker) -> None:
    url = linker.build_amazon_url(asin="B0CHWRXH8B")
    assert "amazon.com/dp/B0CHWRXH8B" in url
    assert "tag=myblog-20" in url
    assert "linkCode=ogi" in url
    assert "th=1" in url


def test_build_amazon_url_with_keyword(linker: AffiliateLinker) -> None:
    url = linker.build_amazon_url(asin="B0CHWRXH8B", keyword="wireless earbuds")
    assert "keywords=wireless+earbuds" in url


def test_build_amazon_url_no_tag(linker: AffiliateLinker) -> None:
    """tag 없으면 단순 URL."""
    no_tag = AffiliateLinker(network="amazon", amazon_tag="")
    url = no_tag.build_amazon_url(asin="B0CHWRXH8B")
    assert "tag=" not in url


# ---------------------------------------------------------------------------
# wrap_amazon_link (FTC disclosure 포함)
# ---------------------------------------------------------------------------

def test_wrap_amazon_link_has_disclosure(linker: AffiliateLinker) -> None:
    html = linker.wrap_amazon_link(asin="B0CHWRXH8B", anchor_text="에어팟")
    assert 'rel="sponsored nofollow noopener"' in html  # FTC 권장 속성
    assert "target=\"_blank\"" in html
    assert "에어팟" in html
    assert "tag=myblog-20" in html
    assert "(paid link)" in html  # FTC 권장 disclosure 문구


def test_wrap_amazon_link_custom_disclosure(linker: AffiliateLinker) -> None:
    html = linker.wrap_amazon_link(
        asin="B0CHWRXH8B",
        anchor_text="X",
        disclosure_marker="#ad",
    )
    assert "#ad" in html
    assert "(paid link)" not in html


def test_wrap_amazon_link_sponsored_attribute(linker: AffiliateLinker) -> None:
    """FTC 권장: rel='sponsored' 속성 필수."""
    html = linker.wrap_amazon_link(asin="B0CHWRXH8B", anchor_text="X")
    # rel="sponsored" + nofollow (검색 봇 차단)
    assert 'rel="sponsored nofollow' in html


# ---------------------------------------------------------------------------
# disclosure_block
# ---------------------------------------------------------------------------

def test_disclosure_block_amazon(linker: AffiliateLinker) -> None:
    html = linker.disclosure_block(position="top", amazon_associate=True)
    assert "Amazon Associate" in html
    assert "qualifying purchases" in html
    assert "📌" in html
    assert "border-left:4px solid #f59e0b" in html  # warning style


def test_disclosure_block_generic(linker: AffiliateLinker) -> None:
    html = linker.disclosure_block(position="top", amazon_associate=False)
    assert "Amazon" not in html
    assert "제휴 마케팅" in html or "affiliate" in html.lower()


def test_disclosure_block_inline_style(linker: AffiliateLinker) -> None:
    html = linker.disclosure_block(position="inline", amazon_associate=True)
    assert "<span" in html
    assert "<div" not in html  # inline은 span


# ---------------------------------------------------------------------------
# inject_into_chunk
# ---------------------------------------------------------------------------

def test_inject_chunk_no_products(linker: AffiliateLinker) -> None:
    body = "<p>본문</p>"
    out = linker.inject_into_chunk(body, products=[])
    # disclosure는 top에 추가됨
    assert "Amazon Associate" in out
    assert "<p>본문</p>" in out


def test_inject_chunk_with_product_end(linker: AffiliateLinker) -> None:
    body = "<p>본문</p>"
    out = linker.inject_into_chunk(body, products=[
        {"asin": "B0CHWRXH8B", "anchor": "에어팟", "position": "end"},
    ])
    assert "(paid link)" in out
    assert "에어팟" in out
    assert "tag=myblog-20" in out


def test_inject_chunk_with_product_after_first_h2(linker: AffiliateLinker) -> None:
    body = "<h2>제목</h2><p>본문</p>"
    out = linker.inject_into_chunk(body, products=[
        {"asin": "B0CHWRXH8B", "anchor": "X", "position": "after_first_h2"},
    ])
    # h2 뒤에 affiliate 박스
    h2_pos = out.index("</h2>")
    box_pos = out.index("affiliate-product-box")
    assert box_pos > h2_pos
    assert "🛒 추천 제품" in out


def test_inject_chunk_no_top_disclosure(linker: AffiliateLinker) -> None:
    body = "<p>본문</p>"
    out = linker.inject_into_chunk(body, products=[], add_top_disclosure=False)
    assert "Amazon Associate" not in out


def test_inject_chunk_sponsored_rel(linker: AffiliateLinker) -> None:
    """Inject된 링크에 rel='sponsored' (FTC 권장)."""
    body = "<p>본문</p>"
    out = linker.inject_into_chunk(body, products=[
        {"asin": "B0CHWRXH8B", "anchor": "X", "position": "end"},
    ])
    assert 'rel="sponsored nofollow' in out


# ---------------------------------------------------------------------------
# 표준 FTC disclosure 문구
# ---------------------------------------------------------------------------

def test_amazon_disclosure_text_contains_required() -> None:
    """Amazon Operating Agreement가 요구하는 문구 포함."""
    assert "Amazon Associate" in AMAZON_DISCLOSURE
    assert "qualifying purchases" in AMAZON_DISCLOSURE


def test_generic_disclosure_mentions_commission() -> None:
    assert "제휴" in GENERIC_DISCLOSURE or "affiliate" in GENERIC_DISCLOSURE.lower()
    assert "commission" in GENERIC_DISCLOSURE.lower() or "수수료" in GENERIC_DISCLOSURE
