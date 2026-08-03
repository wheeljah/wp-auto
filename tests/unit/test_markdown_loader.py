"""Unit tests for markdown_loader.py (직접 작성 markdown → cluster)."""

from __future__ import annotations

from pathlib import Path

import pytest

from wp_auto.ai.chunked_generator import PillarCluster
from wp_auto.ai.markdown_loader import (
    Frontmatter,
    MarkdownPost,
    load_markdown,
    md_to_cluster,
    parse_markdown,
)


# ---------------------------------------------------------------------------
# Frontmatter 파싱
# ---------------------------------------------------------------------------


class TestFrontmatter:
    def test_basic(self) -> None:
        text = """---
title: "테스트 글"
slug: "test-post"
keyword: "테스트"
intent: "informational"
language: "ko"
---

본문
"""
        post = parse_markdown(text)
        assert post.frontmatter.title == "테스트 글"
        assert post.frontmatter.slug == "test-post"
        assert post.frontmatter.keyword == "테스트"
        assert post.frontmatter.intent == "informational"
        assert post.frontmatter.language == "ko"

    def test_tags_list(self) -> None:
        text = """---
title: "Test"
tags: [워드프레스, SEO, 가이드]
---

본문
"""
        post = parse_markdown(text)
        assert post.frontmatter.tags == ["워드프레스", "SEO", "가이드"]

    def test_categories_list(self) -> None:
        text = """---
title: "Test"
categories: [블로그, 수익화]
---

본문
"""
        post = parse_markdown(text)
        assert post.frontmatter.categories == ["블로그", "수익화"]

    def test_extras(self) -> None:
        text = """---
title: "Test"
author: "Kim"
date: "2026-08-04"
---

본문
"""
        post = parse_markdown(text)
        assert post.frontmatter.extras.get("author") == "Kim"
        assert post.frontmatter.extras.get("date") == "2026-08-04"

    def test_single_quotes(self) -> None:
        text = """---
title: 'Quoted Title'
slug: 'quoted-slug'
---

본문
"""
        post = parse_markdown(text)
        assert post.frontmatter.title == "Quoted Title"
        assert post.frontmatter.slug == "quoted-slug"

    def test_no_frontmatter(self) -> None:
        text = "# H1 제목\n\n## H2 섹션\n\n본문"
        post = parse_markdown(text)
        assert post.frontmatter.title == ""
        assert post.frontmatter.intent == "informational"  # default
        assert post.frontmatter.language == "ko"  # default


# ---------------------------------------------------------------------------
# Markdown 파싱 (sections)
# ---------------------------------------------------------------------------


class TestParseMarkdown:
    def test_h1_extraction(self) -> None:
        text = """---
title: "FM Title"
---

# H1 Real Title

## H2 Section 1

본문 1

## H2 Section 2

본문 2
"""
        post = parse_markdown(text)
        assert post.h1_title == "H1 Real Title"
        # title 우선 (FM)
        assert post.title == "FM Title"

    def test_h1_when_no_fm(self) -> None:
        text = "# H1 Only\n\n## H2 1\n\nbody\n\n## H2 2\n\nbody"
        post = parse_markdown(text)
        assert post.h1_title == "H1 Only"
        assert post.title == "H1 Only"
        assert len(post.sections) == 2

    def test_intro(self) -> None:
        text = """---
title: "T"
---

intro 본문 1
intro 본문 2

## H2 Section

section body
"""
        post = parse_markdown(text)
        assert "intro 본문 1" in post.intro
        assert "intro 본문 2" in post.intro
        assert "section body" not in post.intro

    def test_h3_within_h2(self) -> None:
        text = """---
title: "T"
---

## H2 Section

본문 시작

### H3 Sub 1

h3 본문 1

### H3 Sub 2

h3 본문 2

## H2 Section 2

body 2
"""
        post = parse_markdown(text)
        assert len(post.sections) == 2
        assert post.sections[0]["h2"] == "H2 Section"
        assert post.sections[0]["h3"] == ["H3 Sub 1", "H3 Sub 2"]

    def test_no_sections(self) -> None:
        text = """---
title: "T"
---

# H1만 있는 글

본문
"""
        post = parse_markdown(text)
        assert len(post.sections) == 0

    def test_to_outline_format(self) -> None:
        text = """---
title: "T"
---

## H2 1
body

## H2 2
### H3 2-1
body
"""
        post = parse_markdown(text)
        outline_fmt = post.to_outline_format()
        assert len(outline_fmt) == 2
        assert outline_fmt[0]["h2"] == "H2 1"
        assert outline_fmt[1]["h2"] == "H2 2"
        assert outline_fmt[1]["h3"] == ["H3 2-1"]


# ---------------------------------------------------------------------------
# load_markdown (file)
# ---------------------------------------------------------------------------


class TestLoadMarkdown:
    def test_load_existing(self, tmp_path: Path) -> None:
        md = tmp_path / "test.md"
        md.write_text(
            "---\ntitle: \"Loaded\"\n---\n\n# H1\n\n## H2\n\nbody",
            encoding="utf-8",
        )
        post = load_markdown(md)
        assert post.title == "Loaded"

    def test_load_korean(self, tmp_path: Path) -> None:
        md = tmp_path / "ko.md"
        md.write_text(
            "---\ntitle: \"한글\"\n---\n\n# 제목\n\n## 섹션\n\n본문",
            encoding="utf-8",
        )
        post = load_markdown(md)
        assert post.title == "한글"
        assert post.sections[0]["h2"] == "섹션"

    def test_load_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_markdown("/nonexistent/file.md")


# ---------------------------------------------------------------------------
# md_to_cluster (핵심 통합)
# ---------------------------------------------------------------------------


class TestMdToCluster:
    def test_basic_conversion(self) -> None:
        text = """---
title: "테스트 글"
slug: "test-post"
keyword: "테스트"
intent: "informational"
language: "ko"
tags: [테스트]
categories: [가이드]
---

## H2 섹션 1

본문 1입니다.

## H2 섹션 2

본문 2입니다.

## H2 섹션 3

본문 3입니다.
"""
        post = parse_markdown(text)
        cluster = md_to_cluster(post, language="ko")

        assert isinstance(cluster, PillarCluster)
        assert cluster.pillar.title == "테스트 글"
        assert len(cluster.chunks) == 3
        assert cluster.language == "ko"
        assert cluster.keyword == "테스트"

    def test_chunk_navigation(self) -> None:
        text = """---
title: "T"
---

## A
body A

## B
body B

## C
body C
"""
        post = parse_markdown(text)
        cluster = md_to_cluster(post, language="ko")

        # 첫 chunk: prev=None, next=B
        assert cluster.chunks[0].prev_slug is None
        assert cluster.chunks[0].next_slug == cluster.chunks[1].slug
        # 중간 chunk: prev=A, next=C, related=[A, C]
        assert cluster.chunks[1].prev_slug == cluster.chunks[0].slug
        assert cluster.chunks[1].next_slug == cluster.chunks[2].slug
        assert len(cluster.chunks[1].related_slugs) == 2
        # 마지막 chunk: prev=B, next=None
        assert cluster.chunks[2].prev_slug == cluster.chunks[1].slug
        assert cluster.chunks[2].next_slug is None

    def test_minimum_sections_required(self) -> None:
        text = """---
title: "T"
---

# H1만 있는 글
"""
        post = parse_markdown(text)
        with pytest.raises(ValueError, match="H2 섹션이 없음"):
            md_to_cluster(post, language="ko")

    def test_wp_post_specs(self) -> None:
        text = """---
title: "T"
keyword: "k"
---

## S1
body 1

## S2
body 2
"""
        post = parse_markdown(text)
        cluster = md_to_cluster(post, language="ko")
        specs = cluster.to_wp_post_specs()

        # 1 pillar + 2 chunks
        assert len(specs) == 3
        assert specs[0]["type"] == "pillar"
        assert specs[1]["type"] == "chunk"
        assert specs[2]["type"] == "chunk"

    def test_intro_only_no_sections(self) -> None:
        text = """---
title: "Intro Only"
---

intro만 있는 글 — H2 없음
"""
        post = parse_markdown(text)
        with pytest.raises(ValueError):
            md_to_cluster(post, language="ko")

    def test_pillar_has_toc(self) -> None:
        text = """---
title: "T"
---

## A
body A

## B
body B
"""
        post = parse_markdown(text)
        cluster = md_to_cluster(post, language="ko")
        pillar_html = cluster.pillar.body_html
        # TOC 포함
        assert 'class="toc"' in pillar_html
        assert '<ul>' in pillar_html
        # cluster index 포함
        assert 'class="cluster-index"' in pillar_html
        # author footer
        assert 'class="author-bio"' in pillar_html

    def test_english(self) -> None:
        text = """---
title: "English Post"
language: "en"
keyword: "test"
---

## Section 1
body 1

## Section 2
body 2
"""
        post = parse_markdown(text)
        cluster = md_to_cluster(post, language="en")
        assert cluster.language == "en"
        assert cluster.pillar.title == "English Post"

    def test_category_from_fm(self) -> None:
        text = """---
title: "T"
categories: [MyCategory]
---

## S1
body
"""
        post = parse_markdown(text)
        cluster = md_to_cluster(post, language="ko")
        assert cluster.category == "MyCategory"

    def test_category_default(self) -> None:
        text = """---
title: "T"
---

## S1
body
"""
        post = parse_markdown(text)
        cluster = md_to_cluster(post, language="ko")
        # default: "md-ko"
        assert "md-" in cluster.category


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_body_sections(self) -> None:
        """H2만 있고 body가 빈 경우."""
        text = """---
title: "T"
---

## H2 Empty
"""
        post = parse_markdown(text)
        cluster = md_to_cluster(post, language="ko")
        assert len(cluster.chunks) == 1
        assert cluster.chunks[0].title == "H2 Empty"

    def test_slug_unicode(self) -> None:
        text = """---
title: "한글 제목"
---

## 섹션
body
"""
        post = parse_markdown(text)
        cluster = md_to_cluster(post, language="ko")
        # 한글 slug 허용
        assert cluster.chunks[0].slug  # 비어있지 않음

    def test_special_chars_in_h2(self) -> None:
        text = """---
title: "T"
---

## H2: "특수문자" & <tag>
body
"""
        post = parse_markdown(text)
        cluster = md_to_cluster(post, language="ko")
        # HTML escape 확인
        html = cluster.chunks[0].body_html
        assert "&amp;" in html or "&" not in html  # escape 적용

    def test_load_korean_file(self, tmp_path: Path) -> None:
        md = tmp_path / "한글파일.md"
        md.write_text(
            "---\ntitle: \"한글\"\nlanguage: \"ko\"\n---\n\n# 제목\n\n## 본문\n\nbody",
            encoding="utf-8",
        )
        post = load_markdown(md)
        assert post.title == "한글"
