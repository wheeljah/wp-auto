"""JSON-LD Schema 생성기 (제휴마케팅 SEO 최적화).

Google Search Central 1차 출처 기반:
- Article: https://developers.google.com/search/docs/appearance/structured-data/article
- Product: https://developers.google.com/search/docs/appearance/structured-data/product
- Review: https://developers.google.com/search/docs/appearance/structured-data/review
- FAQ: https://developers.google.com/search/docs/appearance/structured-data/faqpage
- HowTo: https://developers.google.com/search/docs/appearance/structured-data/howto
- BreadcrumbList: https://schema.org/BreadcrumbList
- WebSite: https://schema.org/WebSite
- Organization: https://schema.org/Organization
- Person: https://schema.org/Person (E-E-A-T)

사용법:
    from wp_auto.ai.schema_generator import SchemaGenerator

    gen = SchemaGenerator(language="ko")
    article_json = gen.article(
        title="...", author="...", date_published="2026-08-04",
        description="...", url="...", image="..."
    )
    product_json = gen.product(
        name="...", description="...", brand="...", price=99.99,
        currency="USD", rating_value=4.5, review_count=42,
        affiliate_url="https://amazon.com/..."
    )
    html = gen.to_html([article_json, product_json])  # <script type="application/ld+json">...</script>
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any


# Schema.org @context (모든 schema의 표준 prefix)
CONTEXT = "https://schema.org"


@dataclass
class SchemaGenerator:
    """JSON-LD Schema 빌더.

    모든 메서드는 dict 반환 (schema.org 형식).
    gen.to_html([...])로 <script> 태그 생성.
    """

    language: str = "ko"

    # -------------------------------------------------------------------------
    # Article (모든 글에 적용)
    # -------------------------------------------------------------------------
    def article(
        self,
        title: str,
        author: str,
        date_published: str,
        description: str,
        url: str,
        image: str = "",
        date_modified: str = "",
        author_url: str = "",
    ) -> dict[str, Any]:
        """Article schema — 1차 출처: developers.google.com/.../article"""
        return {
            "@context": CONTEXT,
            "@type": "Article",
            "headline": title[:110],  # Google 권장 110자
            "description": description[:160],
            "image": [image] if image else [],
            "datePublished": date_published,
            "dateModified": date_modified or date_published,
            "author": {
                "@type": "Person",
                "name": author[:100],  # Google 100자 제한
                "url": author_url or url,
            },
            "publisher": {
                "@type": "Organization",
                "name": author[:100],  # 1인 self-use = publisher = author
                "url": author_url or url,
            },
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": url,
            },
            "inLanguage": self.language,
        }

    # -------------------------------------------------------------------------
    # Product (제휴마케팅 핵심)
    # -------------------------------------------------------------------------
    def product(
        self,
        name: str,
        description: str,
        brand: str,
        price: float | None = None,
        currency: str = "USD",
        availability: str = "InStock",
        url: str = "",
        image: str = "",
        sku: str = "",
        rating_value: float | None = None,
        review_count: int = 0,
        affiliate_url: str = "",
    ) -> dict[str, Any]:
        """Product schema — 1차 출처: developers.google.com/.../product

        Review snippet 자격: review OR aggregateRating OR offers 중 1개 필수
        - product snippets: editorial review (Amazon Affiliate 적합)
        """
        product: dict[str, Any] = {
            "@context": CONTEXT,
            "@type": "Product",
            "name": name,
            "description": description,
            "brand": {"@type": "Brand", "name": brand},
            "url": affiliate_url or url,  # affiliate 우선
        }
        if image:
            product["image"] = [image]
        if sku:
            product["sku"] = sku
        # offers: affiliate 링크 있으면 가격+URL
        if price is not None and (affiliate_url or url):
            product["offers"] = {
                "@type": "Offer",
                "priceCurrency": currency,
                "price": price,
                "availability": f"https://schema.org/{availability}",
                "url": affiliate_url or url,
            }
        # aggregateRating: 별점 정보
        if rating_value is not None and review_count > 0:
            product["aggregateRating"] = {
                "@type": "AggregateRating",
                "ratingValue": rating_value,
                "reviewCount": review_count,
                "bestRating": 5,
                "worstRating": 1,
            }
        return product

    # -------------------------------------------------------------------------
    # Review (제품 리뷰 글)
    # -------------------------------------------------------------------------
    def review(
        self,
        item_name: str,
        item_type: str = "Product",
        author: str = "",
        date_published: str = "",
        review_body: str = "",
        rating_value: float = 5.0,
        best_rating: float = 5.0,
    ) -> dict[str, Any]:
        """Review schema — 1차 출처: developers.google.com/.../review

        유효 type: Product, LocalBusiness, Book, Movie, Recipe,
                  SoftwareApplication, Event, Game
        (2024부터 Organization/Article 부적합)
        """
        valid_types = (
            "Product", "LocalBusiness", "Book", "Movie", "Recipe",
            "SoftwareApplication", "Event", "Game",
        )
        if item_type not in valid_types:
            raise ValueError(
                f"Invalid review item type: {item_type}. "
                f"Valid: {', '.join(valid_types)}"
            )
        review: dict[str, Any] = {
            "@context": CONTEXT,
            "@type": "Review",
            "itemReviewed": {
                "@type": item_type,
                "name": item_name,
            },
            "reviewRating": {
                "@type": "Rating",
                "ratingValue": rating_value,
                "bestRating": best_rating,
            },
        }
        if author:
            review["author"] = {
                "@type": "Person",
                "name": author[:100],  # Google 100자 제한
            }
        if date_published:
            review["datePublished"] = date_published
        if review_body:
            review["reviewBody"] = review_body[:2000]
        return review

    # -------------------------------------------------------------------------
    # FAQPage
    # -------------------------------------------------------------------------
    def faq(
        self,
        questions: list[dict[str, str]],
    ) -> dict[str, Any]:
        """FAQPage schema — 1차 출처: developers.google.com/.../faqpage

        questions: [{"q": "...", "a": "..."}, ...]
        """
        return {
            "@context": CONTEXT,
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": q["q"],
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": q["a"],
                    },
                }
                for q in questions
            ],
        }

    # -------------------------------------------------------------------------
    # HowTo (가이드형 글)
    # -------------------------------------------------------------------------
    def howto(
        self,
        name: str,
        description: str,
        steps: list[str],
        total_time: str = "",
        image: str = "",
    ) -> dict[str, Any]:
        """HowTo schema — 1차 출처: developers.google.com/.../howto

        steps: 단계별 설명 리스트
        total_time: ISO 8601 duration (e.g., "PT30M")
        """
        howto: dict[str, Any] = {
            "@context": CONTEXT,
            "@type": "HowTo",
            "name": name,
            "description": description,
            "step": [
                {
                    "@type": "HowToStep",
                    "position": i + 1,
                    "text": step,
                }
                for i, step in enumerate(steps)
            ],
        }
        if total_time:
            howto["totalTime"] = total_time
        if image:
            howto["image"] = image
        return howto

    # -------------------------------------------------------------------------
    # BreadcrumbList
    # -------------------------------------------------------------------------
    def breadcrumb(
        self,
        items: list[dict[str, str]],
    ) -> dict[str, Any]:
        """BreadcrumbList — schema.org

        items: [{"name": "...", "url": "..."}, ...]
        """
        return {
            "@context": CONTEXT,
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": i + 1,
                    "name": it["name"],
                    "item": it["url"],
                }
                for i, it in enumerate(items)
            ],
        }

    # -------------------------------------------------------------------------
    # WebSite + SearchAction (sitelinks search box)
    # -------------------------------------------------------------------------
    def website(
        self,
        name: str,
        url: str,
        search_url: str = "",
    ) -> dict[str, Any]:
        """WebSite schema (sitelinks search box) — 1차 출처: schema.org/WebSite"""
        site: dict[str, Any] = {
            "@context": CONTEXT,
            "@type": "WebSite",
            "name": name,
            "url": url,
            "inLanguage": self.language,
        }
        if search_url:
            site["potentialAction"] = {
                "@type": "SearchAction",
                "target": f"{search_url}?q={{search_term_string}}",
                "query-input": "required name=search_term_string",
            }
        return site

    # -------------------------------------------------------------------------
    # Organization (E-E-A-T 사이트 정보)
    # -------------------------------------------------------------------------
    def organization(
        self,
        name: str,
        url: str,
        logo: str = "",
        same_as: list[str] | None = None,
    ) -> dict[str, Any]:
        """Organization — schema.org/Organization"""
        org: dict[str, Any] = {
            "@context": CONTEXT,
            "@type": "Organization",
            "name": name,
            "url": url,
        }
        if logo:
            org["logo"] = logo
        if same_as:
            org["sameAs"] = same_as
        return org

    # -------------------------------------------------------------------------
    # Person (E-E-A-T 작성자 정보)
    # -------------------------------------------------------------------------
    def person(
        self,
        name: str,
        url: str = "",
        description: str = "",
        same_as: list[str] | None = None,
    ) -> dict[str, Any]:
        """Person — schema.org/Person (Google 100자 name 제한)"""
        p: dict[str, Any] = {
            "@context": CONTEXT,
            "@type": "Person",
            "name": name[:100],
        }
        if url:
            p["url"] = url
        if description:
            p["description"] = description
        if same_as:
            p["sameAs"] = same_as
        return p

    # -------------------------------------------------------------------------
    # HTML 출력
    # -------------------------------------------------------------------------
    def to_html(
        self,
        schemas: list[dict[str, Any]],
    ) -> str:
        """여러 schema를 하나의 <script> 태그로 출력.

        args:
            schemas: schema dict 리스트

        returns:
            <script type="application/ld+json">{"@graph": [...]}</script>
        """
        # Google 권장: @graph로 묶기
        graph = {
            "@context": CONTEXT,
            "@graph": schemas,
        }
        json_str = json.dumps(graph, ensure_ascii=False, separators=(",", ":"))
        return (
            f'<script type="application/ld+json">\n'
            f'{json_str}\n'
            f'</script>'
        )


__all__ = ["SchemaGenerator", "CONTEXT"]
