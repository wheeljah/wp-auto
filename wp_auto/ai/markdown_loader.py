"""Markdown → ChunkedCluster: 직접 작성 콘텐츠 배포.

1인 self-use 워드프레스 자동화의 두 번째 입력 경로 (URL/PDF 외).

핵심 결정:
- **frontmatter YAML** — title, slug, keyword, intent, language, tags, categories
- **# H1** → pillar title (frontmatter에 title 없으면 자동 추출)
- **## H2** → chunk/subtopic 경계 (각 H2가 1개 cluster chunk)
- **### H3** → chunk 내부 sub-heading
- **기존 chunked_generator와 통합** — ChunkedCluster를 직접 만들어 publish

사용법:
    from wp_auto.ai.markdown_loader import MarkdownPost, load_markdown, md_to_cluster

    # 1) Markdown 파일 로드 + 파싱
    post = load_markdown("path/to/article.md")
    print(post.title, post.frontmatter)

    # 2) chunked cluster로 변환 (publish 직전 단계)
    cluster = md_to_cluster(post, language="ko", author_name="1인 운영자")
    # cluster.to_wp_post_specs() → WP publish용
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from loguru import logger

from wp_auto.ai.chunked_generator import (
    ChunkedPost,
    PillarCluster,
    Subtopic,
)

# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------

# 매우 단순한 frontmatter 파서 (PyYAML 의존 X)
# 형식:
#   ---
#   title: "..."
#   slug: "..."
#   keyword: "..."
#   intent: "informational"
#   language: "ko"
#   tags: [워드프레스, SEO]
#   categories: [가이드]
#   ---
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


@dataclass
class Frontmatter:
    """Markdown frontmatter (YAML-like, 단순 파서)."""

    title: str = ""
    slug: str = ""
    keyword: str = ""
    intent: str = "informational"           # informational | commercial investigation | transactional
    language: str = "ko"                    # "ko" | "en"
    tags: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    meta_description: str = ""
    extras: dict = field(default_factory=dict)  # 인식 안 되는 키

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "slug": self.slug,
            "keyword": self.keyword,
            "intent": self.intent,
            "language": self.language,
            "tags": self.tags,
            "categories": self.categories,
            "meta_description": self.meta_description,
            **self.extras,
        }


# ---------------------------------------------------------------------------
# MarkdownPost
# ---------------------------------------------------------------------------


@dataclass
class MarkdownPost:
    """파싱된 마크다운 글."""

    frontmatter: Frontmatter
    raw_body: str                           # frontmatter 제외 raw 마크다운
    h1_title: str = ""                      # # H1 (frontmatter 우선, 없으면 H1)
    sections: list[dict] = field(default_factory=list)  # [{"h2": "...", "level": 2, "body": "..."}, ...]
    intro: str = ""                         # 첫 H2 이전 본문 (있는 경우)

    @property
    def title(self) -> str:
        return self.frontmatter.title or self.h1_title

    @property
    def language(self) -> str:
        return self.frontmatter.language or "ko"

    def to_outline_format(self) -> list[dict]:
        """기존 Outline.outline 형식([{h2, h3}])으로 변환."""
        return [
            {
                "h2": sec.get("h2", ""),
                "h3": sec.get("h3", []),
            }
            for sec in self.sections
        ]


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def load_markdown(path: str | Path) -> MarkdownPost:
    """마크다운 파일을 로드 + 파싱.

    Args:
        path: .md 파일 경로

    Returns:
        MarkdownPost (frontmatter + sections)

    Raises:
        FileNotFoundError: 파일 없음
        ValueError: frontmatter 형식 오류
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Markdown 파일 없음: {path}")

    text = p.read_text(encoding="utf-8")
    return parse_markdown(text)


def parse_markdown(text: str) -> MarkdownPost:
    """마크다운 텍스트를 파싱.

    Args:
        text: 마크다운 텍스트 (frontmatter 포함 가능)

    Returns:
        MarkdownPost
    """
    # 1) frontmatter 분리
    frontmatter = Frontmatter()
    body = text
    m = FRONTMATTER_RE.match(text)
    if m:
        frontmatter = _parse_frontmatter(m.group(1))
        body = m.group(2)

    # 2) H1/H2/H3 파싱
    h1_title = ""
    sections: list[dict] = []
    intro_lines: list[str] = []

    current_h2: dict | None = None
    current_h3: dict | None = None

    for line in body.splitlines():
        stripped = line.rstrip()

        if stripped.startswith("# ") and not stripped.startswith("## "):
            # H1
            h1_title = stripped[2:].strip()
            continue

        if stripped.startswith("## ") and not stripped.startswith("### "):
            # H2 → 새 section 시작
            if current_h2 is not None:
                sections.append(current_h2)
            current_h2 = {
                "h2": stripped[3:].strip(),
                "h3": [],
                "body_lines": [],
            }
            current_h3 = None
            continue

        if stripped.startswith("### "):
            # H3
            if current_h2 is None:
                # H2 없이 H3만 있는 경우 → intro에 추가
                intro_lines.append(line)
                continue
            current_h3 = {
                "h3": stripped[4:].strip(),
                "body_lines": [],
            }
            current_h2["h3"].append(current_h3)
            continue

        # 본문 라인
        if current_h3 is not None:
            current_h3["body_lines"].append(line)
        elif current_h2 is not None:
            current_h2["body_lines"].append(line)
        else:
            intro_lines.append(line)

    # 마지막 section
    if current_h2 is not None:
        sections.append(current_h2)

    # 3) body_lines → body 문자열 (H3 구조 보존)
    intro = _strip_blank_lines(intro_lines)
    final_sections: list[dict] = []
    for sec in sections:
        h2 = sec["h2"]
        h3_list = []
        # H3 + 본문 구조
        body_parts: list[str] = []
        for h3 in sec["h3"]:
            h3_title = h3["h3"]
            h3_body = _strip_blank_lines(h3["body_lines"])
            if h3_body:
                body_parts.append(f"### {h3_title}\n\n{h3_body}")
            else:
                body_parts.append(f"### {h3_title}")
            h3_list.append(h3_title)

        # H2 본문 (H3 외)
        # H3는 이미 h3.body_lines를 사용했으므로 sec.body_lines는 H2 직속만
        h2_direct = _strip_blank_lines(sec["body_lines"])
        if h2_direct and body_parts:
            body_parts.insert(0, h2_direct)
        elif h2_direct and not body_parts:
            body_parts = [h2_direct]

        final_sections.append({
            "h2": h2,
            "h3": h3_list,
            "body": "\n\n".join(body_parts).strip(),
        })

    return MarkdownPost(
        frontmatter=frontmatter,
        raw_body=body,
        h1_title=h1_title,
        sections=final_sections,
        intro=intro,
    )


def _strip_blank_lines(lines: list[str]) -> str:
    """앞뒤 빈 줄 제거 + 연속 빈 줄 1개로 압축."""
    if not lines:
        return ""
    # 앞뒤 trim
    text = "\n".join(lines)
    text = text.strip()
    # 연속 빈 줄 1개로
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _parse_frontmatter(text: str) -> Frontmatter:
    """매우 단순한 frontmatter 파서 (PyYAML 의존 X).

    지원 형식:
        key: value
        key: "quoted value"
        key: [a, b, c]
    """
    fm = Frontmatter()
    known_keys = {
        "title", "slug", "keyword", "intent", "language",
        "tags", "categories", "meta_description",
    }

    for line in text.splitlines():
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()

        if not value:
            continue

        # 따옴표 제거
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]

        if key == "title":
            fm.title = value
        elif key == "slug":
            fm.slug = value
        elif key == "keyword":
            fm.keyword = value
        elif key == "intent":
            fm.intent = value
        elif key == "language":
            fm.language = value
        elif key == "meta_description":
            fm.meta_description = value
        elif key in ("tags", "categories"):
            # list 파싱: [a, b, c] or [a,b,c]
            if value.startswith("[") and value.endswith("]"):
                inner = value[1:-1]
                items = [x.strip().strip('"').strip("'") for x in inner.split(",")]
                items = [x for x in items if x]
                if key == "tags":
                    fm.tags = items
                else:
                    fm.categories = items
            else:
                if key == "tags":
                    fm.tags = [value]
                else:
                    fm.categories = [value]
        else:
            fm.extras[key] = value

    return fm


# ---------------------------------------------------------------------------
# Markdown → ChunkedCluster 변환
# ---------------------------------------------------------------------------


def md_to_cluster(
    post: MarkdownPost,
    language: str = "ko",
    author_name: str = "1인 운영자 (AI-assisted)",
    pillar_chars: int = 400,
) -> PillarCluster:
    """MarkdownPost를 PillarCluster로 변환.

    - post.sections (각 H2) → 1 chunk
    - post.intro + 마지막 결론 → pillar (intro/outro)

    Args:
        post: MarkdownPost
        language: "ko" | "en"
        author_name: 작성자 (E-E-A-T)
        pillar_chars: pillar 본문 분량 (무시, intro/outro로 대체)

    Returns:
        PillarCluster (기존 chunked_generator와 동일 형식)
    """
    if not post.sections:
        raise ValueError("Markdown에 ## H2 섹션이 없음 — 최소 1개 필요")

    # 1) Pillar (intro + TOC + outro)
    pillar_title = post.title
    pillar_slug = post.frontmatter.slug or _slugify(pillar_title)
    pillar_keyword = post.frontmatter.keyword

    pillar_body = _build_pillar_body(post)

    pillar = ChunkedPost(
        subtopic_id="pillar",
        title=pillar_title,
        body_html=pillar_body,
        meta_description=post.frontmatter.meta_description or _extract_intro_meta(post),
        keyword=pillar_keyword,
        slug=pillar_slug,
        h2_anchor="",
        language=language,
    )

    # 2) Chunks (각 H2 section)
    chunks: list[ChunkedPost] = []
    for i, sec in enumerate(post.sections):
        h2 = sec["h2"]
        h3 = sec.get("h3", [])
        body = sec.get("body", "")

        chunk_slug = _slugify(h2) or f"chunk-{i+1}"
        chunk_html = _md_section_to_html(h2, body, h3)

        chunks.append(ChunkedPost(
            subtopic_id=chunk_slug,
            title=h2,
            body_html=chunk_html,
            meta_description=_truncate(body, 160),
            keyword=pillar_keyword,
            slug=chunk_slug,
            h2_anchor=chunk_slug,
            language=language,
        ))

    # 3) prev/next/related 슬러그 채우기
    for i, ch in enumerate(chunks):
        if i > 0:
            ch.prev_slug = chunks[i - 1].slug
        if i < len(chunks) - 1:
            ch.next_slug = chunks[i + 1].slug
        # related: 인접 chunk
        related = []
        for j in (i - 1, i + 1):
            if 0 <= j < len(chunks):
                related.append(chunks[j].slug)
        ch.related_slugs = related

    # 4) category 자동 생성 (frontmatter 또는 날짜 기반)
    category = (
        post.frontmatter.categories[0]
        if post.frontmatter.categories
        else f"md-{post.frontmatter.language or 'ko'}"
    )

    cluster = PillarCluster(
        pillar=pillar,
        chunks=chunks,
        topic=post.title,
        keyword=pillar_keyword,
        language=language,
        category=category,
    )

    logger.info(
        "md_to_cluster: title={!r}, chunks={}, language={}",
        pillar_title, len(chunks), language,
    )
    return cluster


def _build_pillar_body(post: MarkdownPost) -> str:
    """Pillar 본문 = intro + TOC + (outro=마지막 section의 일부)."""
    parts: list[str] = []

    # 1) intro (frontmatter.description 또는 H1 직전 본문)
    intro_text = post.intro.strip()
    if intro_text:
        parts.append(_md_to_html_simple(intro_text))
    elif post.frontmatter.meta_description:
        parts.append(f"<p>{post.frontmatter.meta_description}</p>")

    # 2) TOC
    if len(post.sections) >= 2:
        toc_items = "\n".join(
            f'<li><a href="#{_slugify(sec["h2"])}">{sec["h2"]}</a></li>'
            for sec in post.sections
        )
        parts.append(f'<nav class="toc" aria-label="목차">\n<ul>\n{toc_items}\n</ul>\n</nav>')

    # 3) H2 section anchor list (pillar은 cluster를 직접 안 담고 anchor만)
    if post.sections:
        anchor_items = "\n".join(
            f'<li><a href="#{_slugify(sec["h2"])}">{sec["h2"]}</a>'
            f'<p>{_truncate(sec.get("body", ""), 100)}</p></li>'
            for sec in post.sections
        )
        parts.append(f'<section class="cluster-index">\n<ul>\n{anchor_items}\n</ul>\n</section>')

    # 4) author/footer (E-E-A-T)
    parts.append('<footer class="author-bio">')
    parts.append("<p>직접 작성 콘텐츠 — wp-auto를 통해 발행</p>")
    parts.append("</footer>")

    return "\n".join(parts)


def _md_section_to_html(h2: str, body: str, h3: list[str]) -> str:
    """H2 section → HTML (chunk body)."""
    parts: list[str] = []
    # body에 이미 ### H3 포함 가능
    if body.strip():
        parts.append(_md_to_html_simple(body))
    else:
        # body가 비었으면 H3만
        for h in h3:
            parts.append(f"<h3>{_esc(h)}</h3>")
    return "\n".join(parts)


def _md_to_html_simple(text: str) -> str:
    """매우 단순한 markdown → HTML (bold, italic, link, list, h3, h4).

    의도: 1인 self-use, 빠른 변환. 풀 CommonMark 구현 X.
    """
    if not text:
        return ""
    lines = text.splitlines()
    out: list[str] = []
    in_ul = False
    in_ol = False
    in_p = False

    def close_ul():
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    def close_ol():
        nonlocal in_ol
        if in_ol:
            out.append("</ol>")
            in_ol = False

    def close_p():
        nonlocal in_p
        if in_p:
            out.append("</p>")
            in_p = False

    for line in lines:
        stripped = line.strip()

        # 빈 줄 → 블록 닫기
        if not stripped:
            close_ul()
            close_ol()
            close_p()
            continue

        # H3
        if stripped.startswith("### ") and not stripped.startswith("#### "):
            close_ul()
            close_ol()
            close_p()
            out.append(f"<h3>{_esc(stripped[4:])}</h3>")
            continue

        # H4
        if stripped.startswith("#### "):
            close_ul()
            close_ol()
            close_p()
            out.append(f"<h4>{_esc(stripped[5:])}</h4>")
            continue

        # UL
        if stripped.startswith("- ") or stripped.startswith("* "):
            close_ol()
            close_p()
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            content = _inline_md(stripped[2:])
            out.append(f"  <li>{content}</li>")
            continue

        # OL
        if re.match(r"^\d+\.\s", stripped):
            close_ul()
            close_p()
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            content = re.sub(r"^\d+\.\s+", "", stripped)
            out.append(f"  <li>{_inline_md(content)}</li>")
            continue

        # Paragraph
        close_ul()
        close_ol()
        if not in_p:
            out.append("<p>")
            in_p = True
        else:
            out.append("<br>")
        out.append(_inline_md(stripped))

    close_ul()
    close_ol()
    close_p()
    return "\n".join(out)


def _inline_md(text: str) -> str:
    """inline markdown 변환 (**bold**, *italic*, [text](url))."""
    # escape 먼저
    text = _esc(text)
    # link
    text = re.sub(
        r"\[([^\]]+)\]\(([^\)]+)\)",
        r'<a href="\2">\1</a>',
        text,
    )
    # bold (**)
    text = re.sub(r"\*\*([^\*]+)\*\*", r"<strong>\1</strong>", text)
    # italic (*)
    text = re.sub(r"(?<!\*)\*([^\*]+)\*(?!\*)", r"<em>\1</em>", text)
    return text


def _esc(text: str) -> str:
    """HTML escape (5자)."""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
    )


def _slugify(text: str) -> str:
    """영문/숫자/하이픈 slug 생성 (한글은 그대로)."""
    s = text.lower().strip()
    # 영문/숫자/공백/하이픈만 남김
    s = re.sub(r"[^a-z0-9가-힣\s\-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rsplit(" ", 1)[0] + "..."


def _extract_intro_meta(post: MarkdownPost) -> str:
    """intro에서 meta_description 자동 추출 (160자 이내)."""
    intro = post.intro.strip()
    # 첫 paragraph만
    first_para = re.split(r"\n\n", intro, maxsplit=1)[0]
    # 마크다운 제거
    first_para = re.sub(r"[#*\[\]()`>]+\s*", "", first_para)
    return _truncate(first_para, 160)


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "MarkdownPost",
    "Frontmatter",
    "load_markdown",
    "parse_markdown",
    "md_to_cluster",
]
