"""Affiliate Linker — Amazon Associates / Awin / CJ Affiliate 링크 자동화 + FTC disclosure.

1차 출처 (FTC + Amazon Operating Agreement):
- https://www.ftc.gov/business-guidance/resources/ftcs-endorsement-guides-what-people-are-asking
- https://affiliate-program.amazon.com/help/node/topic/GHQNZAU6669EZS98

핵심 규칙:
- Affiliate 링크마다 disclosure ("(paid link)", "#ad", "#CommissionsEarned")
- 사이트 전역에 "As an Amazon Associate..." 명시
- 모든 schema는 visible content와 일치 (Google 가이드)

사용법:
    from wp_auto.ai.affiliate_linker import AffiliateLinker

    linker = AffiliateLinker(
        amazon_tag="yourtag-20",
        network="amazon",
    )
    html_chunk = linker.inject(chunk_body, products=[{...}])
    disclosure = linker.disclosure_block(position="top")
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

# 1차 출처: Amazon Associates Operating Agreement + FTC Endorsement Guides
NETWORKS = ("amazon", "awin", "cj", "impact", "rakuten")

# 표준 FTC disclosure 문구 (1차 출처: Amazon + FTC)
AMAZON_DISCLOSURE = (
    "이 글에는 Amazon Associates 프로그램이 제공하는 제휴 마케팅 링크가 포함되어 있습니다. "
    "As an Amazon Associate, I earn from qualifying purchases."
)

GENERIC_DISCLOSURE = (
    "이 글에는 제휴 마케팅 링크가 포함되어 있습니다. "
    "링크를 통해 구매하시면 소정의 수수료를 받을 수 있습니다. "
    "This post contains affiliate links. We may earn a commission for purchases made through these links."
)


@dataclass
class AffiliateLinker:
    """Amazon/Awin/CJ affiliate 링크 자동 생성 + FTC disclosure."""

    network: Literal["amazon", "awin", "cj", "impact", "rakuten"] = "amazon"
    amazon_tag: str = ""  # Amazon Associates tag (e.g., "yourblog-20")
    awin_id: int | None = None
    cj_id: str = ""
    language: str = "ko"

    def build_amazon_url(
        self,
        asin: str,
        keyword: str = "",
    ) -> str:
        """Amazon Affiliate 링크 생성.

        args:
            asin: Amazon Standard Identification Number
            keyword: 검색 키워드 (선택, URL 인코딩)

        returns:
            https://www.amazon.com/dp/ASIN?tag=yourtag-20&linkCode=ogi&th=1
        """
        url = f"https://www.amazon.com/dp/{asin}"
        if self.amazon_tag:
            url += f"?tag={self.amazon_tag}&linkCode=ogi&th=1"
        if keyword:
            url += f"&keywords={keyword.replace(' ', '+')}"
        return url

    def wrap_amazon_link(
        self,
        asin: str,
        anchor_text: str,
        disclosure_marker: str = "(paid link)",
    ) -> str:
        """Amazon affiliate 링크 HTML (FTC disclosure 포함).

        args:
            asin: Amazon ASIN
            anchor_text: 표시될 텍스트
            disclosure_marker: "(paid link)" | "#ad" | "#CommissionsEarned"
        """
        url = self.build_amazon_url(asin)
        return (
            f'<a href="{url}" rel="sponsored nofollow noopener" '
            f'target="_blank">{anchor_text}</a> '
            f'<span class="affiliate-disclosure" '
            f'style="font-size:11px;color:#6b7280;">{disclosure_marker}</span>'
        )

    def disclosure_block(
        self,
        position: Literal["top", "bottom", "inline"] = "top",
        amazon_associate: bool = True,
    ) -> str:
        """FTC disclosure 블록 (Amazon/일반).

        args:
            position: "top" (글 상단) | "bottom" (글 하단) | "inline" (inline)
            amazon_associate: True면 Amazon-specific 문구, False면 일반
        """
        if amazon_associate:
            text = AMAZON_DISCLOSURE
        else:
            text = GENERIC_DISCLOSURE
        style = (
            'background:#fffbeb;border-left:4px solid #f59e0b;'
            'padding:12px 16px;margin:20px 0;border-radius:4px;'
            'font-size:13px;line-height:1.6;color:#92400e;'
        )
        if position == "inline":
            return (
                f'<span class="ftc-disclosure" style="{style}">{text}</span>'
            )
        return (
            f'<div class="ftc-disclosure" style="{style}">'
            f'<strong>📌 제휴 마케팅 고지 (Affiliate Disclosure):</strong> {text}'
            f'</div>'
        )

    def inject_into_chunk(
        self,
        chunk_body: str,
        products: list[dict] | None = None,
        add_top_disclosure: bool = True,
    ) -> str:
        """Chunk body에 Amazon affiliate 링크 + disclosure 자동 주입.

        args:
            chunk_body: 원본 HTML
            products: [{"asin": "...", "anchor": "...", "position": "end"}, ...]
            add_top_disclosure: chunk 시작에 disclosure 추가 여부

        사용 예:
            linker.inject_into_chunk(
                chunk_body,
                products=[{
                    "asin": "B08N5WRWNW",
                    "anchor": "이 제품 Amazon에서 보기",
                    "position": "end",  # or "after_first_h2"
                    "disclosure": "(paid link)",
                }],
            )
        """
        out = chunk_body
        if add_top_disclosure:
            out = self.disclosure_block(position="top") + "\n" + out
        for prod in (products or []):
            asin = prod.get("asin", "")
            if not asin:
                continue
            link_html = self.wrap_amazon_link(
                asin=asin,
                anchor_text=prod.get("anchor", "Amazon에서 보기"),
                disclosure_marker=prod.get("disclosure", "(paid link)"),
            )
            position = prod.get("position", "end")
            if position == "end":
                out = out.rstrip() + "\n\n<p>" + link_html + "</p>"
            elif position == "after_first_h2":
                # 첫 h2 뒤에 product 박스 삽입
                box = (
                    f'<div class="affiliate-product-box" style="'
                    f'border:1px solid #e5e7eb;border-radius:8px;'
                    f'padding:16px;margin:20px 0;background:#f9fafb;">'
                    f'<div style="font-weight:600;margin-bottom:8px;">'
                    f'🛒 추천 제품</div>'
                    f'{link_html}</div>'
                )
                m = re.search(r'(<h2[^>]*>.*?</h2>)', out, flags=re.DOTALL)
                if m:
                    out = out[: m.end()] + "\n" + box + out[m.end():]
                else:
                    out = box + out
        return out


__all__ = ["AffiliateLinker", "NETWORKS", "AMAZON_DISCLOSURE", "GENERIC_DISCLOSURE"]
