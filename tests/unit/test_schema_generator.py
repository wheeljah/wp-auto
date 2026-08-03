"""SchemaGenerator 단위 테스트 (Google JSON-LD 1차 출처 기반)."""
from __future__ import annotations

import json

import pytest

from wp_auto.ai.schema_generator import CONTEXT, SchemaGenerator


@pytest.fixture
def gen() -> SchemaGenerator:
    return SchemaGenerator(language="ko")


# ---------------------------------------------------------------------------
# Article
# ---------------------------------------------------------------------------

def test_article_basic(gen: SchemaGenerator) -> None:
    a = gen.article(
        title="워드프레스 SEO 가이드",
        author="테스트",
        date_published="2026-08-04",
        description="워드프레스 SEO 핵심 가이드",
        url="https://example.com/post",
    )
    assert a["@type"] == "Article"
    assert a["headline"] == "워드프레스 SEO 가이드"
    assert a["author"]["name"] == "테스트"
    assert a["datePublished"] == "2026-08-04"
    assert a["inLanguage"] == "ko"


def test_article_headline_max_110(gen: SchemaGenerator) -> None:
    """Google 권장: headline 110자 이하."""
    long_title = "A" * 200
    a = gen.article(
        title=long_title, author="X", date_published="2026-08-04",
        description="", url="https://x.com"
    )
    assert len(a["headline"]) <= 110


def test_article_description_max_160(gen: SchemaGenerator) -> None:
    a = gen.article(
        title="X", author="X", date_published="2026-08-04",
        description="A" * 300, url="https://x.com"
    )
    assert len(a["description"]) <= 160


# ---------------------------------------------------------------------------
# Product (제휴마케팅 핵심)
# ---------------------------------------------------------------------------

def test_product_basic(gen: SchemaGenerator) -> None:
    p = gen.product(
        name="에어팟 프로 2",
        description="Apple 무선 이어폰",
        brand="Apple",
        price=329.0,
        currency="USD",
        rating_value=4.5,
        review_count=1200,
        affiliate_url="https://amazon.com/dp/B0CHWRXH8B?tag=myblog-20",
    )
    assert p["@type"] == "Product"
    assert p["name"] == "에어팟 프로 2"
    assert p["brand"]["name"] == "Apple"
    assert p["offers"]["price"] == 329.0
    assert p["offers"]["priceCurrency"] == "USD"
    assert p["aggregateRating"]["ratingValue"] == 4.5
    assert p["aggregateRating"]["reviewCount"] == 1200
    # affiliate URL이 url에 적용됨
    assert p["url"] == "https://amazon.com/dp/B0CHWRXH8B?tag=myblog-20"
    assert p["offers"]["url"] == "https://amazon.com/dp/B0CHWRXH8B?tag=myblog-20"


def test_product_with_image_and_sku(gen: SchemaGenerator) -> None:
    p = gen.product(
        name="X", description="Y", brand="Z",
        image="https://example.com/x.jpg", sku="B0CHWRXH8B"
    )
    assert p["image"] == ["https://example.com/x.jpg"]
    assert p["sku"] == "B0CHWRXH8B"


def test_product_availability_instock(gen: SchemaGenerator) -> None:
    p = gen.product(name="X", description="Y", brand="Z", price=10.0, url="https://x.com")
    assert p["offers"]["availability"] == "https://schema.org/InStock"


# ---------------------------------------------------------------------------
# Review (2024 valid types: 17개)
# ---------------------------------------------------------------------------

def test_review_product(gen: SchemaGenerator) -> None:
    r = gen.review(
        item_name="에어팟 프로 2",
        item_type="Product",
        author="테스트",
        date_published="2026-08-04",
        review_body="훌륭한 무선 이어폰",
        rating_value=4.5,
    )
    assert r["@type"] == "Review"
    assert r["itemReviewed"]["@type"] == "Product"
    assert r["reviewRating"]["ratingValue"] == 4.5


def test_review_invalid_type_raises(gen: SchemaGenerator) -> None:
    """2024부터 Organization/Article은 review 부적합."""
    with pytest.raises(ValueError, match="Invalid review item type"):
        gen.review(item_name="X", item_type="Organization")


def test_review_valid_types_list() -> None:
    """Google이 인정하는 17개 valid types 중 주요 8개."""
    from wp_auto.ai.schema_generator import SchemaGenerator
    gen = SchemaGenerator()
    for t in ("Product", "LocalBusiness", "Book", "Movie", "Recipe",
              "SoftwareApplication", "Event", "Game"):
        r = gen.review(item_name="X", item_type=t)
        assert r["itemReviewed"]["@type"] == t


def test_review_author_max_100(gen: SchemaGenerator) -> None:
    """Google 2024 변경: author.name 100자 이하."""
    r = gen.review(item_name="X", item_type="Product", author="A" * 200)
    assert len(r["author"]["name"]) <= 100


# ---------------------------------------------------------------------------
# FAQ
# ---------------------------------------------------------------------------

def test_faq(gen: SchemaGenerator) -> None:
    f = gen.faq([
        {"q": "Q1?", "a": "A1."},
        {"q": "Q2?", "a": "A2."},
    ])
    assert f["@type"] == "FAQPage"
    assert len(f["mainEntity"]) == 2
    assert f["mainEntity"][0]["@type"] == "Question"
    assert f["mainEntity"][0]["name"] == "Q1?"
    assert f["mainEntity"][0]["acceptedAnswer"]["text"] == "A1."


# ---------------------------------------------------------------------------
# HowTo
# ---------------------------------------------------------------------------

def test_howto(gen: SchemaGenerator) -> None:
    h = gen.howto(
        name="워드프레스 설치",
        description="5분 안에 워드프레스 설치하기",
        steps=["호스팅 가입", "WordPress 클릭 설치", "테마 적용"],
        total_time="PT5M",
    )
    assert h["@type"] == "HowTo"
    assert len(h["step"]) == 3
    assert h["step"][0]["position"] == 1
    assert h["totalTime"] == "PT5M"


# ---------------------------------------------------------------------------
# Breadcrumb
# ---------------------------------------------------------------------------

def test_breadcrumb(gen: SchemaGenerator) -> None:
    b = gen.breadcrumb([
        {"name": "Home", "url": "https://example.com"},
        {"name": "Blog", "url": "https://example.com/blog"},
    ])
    assert b["@type"] == "BreadcrumbList"
    assert len(b["itemListElement"]) == 2
    assert b["itemListElement"][0]["position"] == 1


# ---------------------------------------------------------------------------
# WebSite + SearchAction
# ---------------------------------------------------------------------------

def test_website_with_search(gen: SchemaGenerator) -> None:
    w = gen.website(
        name="My Blog", url="https://myblog.com",
        search_url="https://myblog.com/search",
    )
    assert w["@type"] == "WebSite"
    assert w["potentialAction"]["@type"] == "SearchAction"
    assert "{search_term_string}" in w["potentialAction"]["target"]


def test_website_without_search(gen: SchemaGenerator) -> None:
    w = gen.website(name="X", url="https://x.com")
    assert "potentialAction" not in w


# ---------------------------------------------------------------------------
# Organization
# ---------------------------------------------------------------------------

def test_organization_with_logo_and_sameas(gen: SchemaGenerator) -> None:
    o = gen.organization(
        name="My Blog",
        url="https://myblog.com",
        logo="https://myblog.com/logo.png",
        same_as=["https://twitter.com/myblog"],
    )
    assert o["@type"] == "Organization"
    assert o["logo"] == "https://myblog.com/logo.png"
    assert "https://twitter.com/myblog" in o["sameAs"]


# ---------------------------------------------------------------------------
# Person (E-E-A-T)
# ---------------------------------------------------------------------------

def test_person_author_max_100(gen: SchemaGenerator) -> None:
    p = gen.person(name="A" * 200)
    assert len(p["name"]) <= 100


def test_person_with_sameas(gen: SchemaGenerator) -> None:
    p = gen.person(
        name="Kim",
        url="https://kim.com",
        description="Tech blogger",
        same_as=["https://twitter.com/kim"],
    )
    assert p["@type"] == "Person"
    assert "https://twitter.com/kim" in p["sameAs"]


# ---------------------------------------------------------------------------
# to_html
# ---------------------------------------------------------------------------

def test_to_html_wraps_in_script(gen: SchemaGenerator) -> None:
    html = gen.to_html([
        {"@type": "Article", "headline": "Test"},
    ])
    assert '<script type="application/ld+json">' in html
    assert '</script>' in html
    # @graph 구조
    assert '"@graph"' in html
    # script 안의 JSON 파싱 가능
    json_str = html.split('<script type="application/ld+json">')[1].split('</script>')[0].strip()
    parsed = json.loads(json_str)
    assert "@graph" in parsed
    assert len(parsed["@graph"]) == 1
    assert parsed["@graph"][0]["@type"] == "Article"


def test_to_html_multiple_schemas(gen: SchemaGenerator) -> None:
    html = gen.to_html([
        gen.article(title="X", author="Y", date_published="2026-08-04", description="", url=""),
        gen.faq([{"q": "Q?", "a": "A."}]),
    ])
    parsed = json.loads(
        html.split('<script type="application/ld+json">')[1].split('</script>')[0].strip()
    )
    types = [s["@type"] for s in parsed["@graph"]]
    assert "Article" in types
    assert "FAQPage" in types


def test_to_html_uses_context(gen: SchemaGenerator) -> None:
    html = gen.to_html([{"@type": "WebSite", "name": "X", "url": "https://x.com"}])
    parsed = json.loads(
        html.split('<script type="application/ld+json">')[1].split('</script>')[0].strip()
    )
    assert parsed["@context"] == CONTEXT  # schema.org
