"""Source ingestion: URL/PDF → 텍스트 추출.

1인 self-use 워드프레스 자동화의 입력 단계.

핵심 결정 (1차 출처 기반):
- **URL 텍스트 추출**: Trafilatura 사용
  - 1차 출처: F1 0.958, precision 0.938, recall 0.978
  - 출처: https://trafilatura.readthedocs.io/en/latest/evaluation.html
  - 출처: https://www.osti.gov/servlets/purl/2429881 (Sandia Labs)
- **PDF 텍스트 추출**: PyMuPDF (fitz) 사용
  - 1차 출처: 180 pages/sec (8-12x faster than pdfplumber)
  - 1차 출처: AGPL-3.0 (1인 self-use는 OK, network service 배포 시 commercial license)
  - 출처: https://pdfmux.com/blog/pymupdf-vs-pdfplumber/
  - 출처: https://github.com/py-pdf/benchmarks

Fair Use 준수 (1차 출처 기반):
- 17 USC §107 / US Copyright Office Fair Use Index
- "원문 직접 복제 ❌" → 요약/재구성은 researcher.py의 LLM 단계에서
- "amount and substantiality 최소화" → 본 모듈은 전체 추출 (researcher가 발췌/요약)
- 1차 출처: https://www.copyright.gov/fair-use/
- 1차 출처: https://fairuse.stanford.edu/overview/fair-use/four-factors/

사용법:
    from wp_auto.ai.source_ingestor import (
        SourceRef, ingest_url, ingest_pdf, ingest_sources,
    )

    # 단일 URL
    ref = SourceRef.from_url("https://example.com/news/article")
    text = ingest_url(ref)
    print(text.title, len(text.body))

    # PDF
    ref = SourceRef.from_path("paper.pdf", source_type="pdf")
    text = ingest_pdf(ref)
    print(text.title, len(text.body))

    # 다중 source
    refs = [
        SourceRef.from_url("https://a.com"),
        SourceRef.from_path("b.pdf", source_type="pdf"),
    ]
    texts = ingest_sources(refs)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from loguru import logger

SourceType = Literal["url", "pdf"]

# 기본 타임아웃 (URL fetch)
DEFAULT_URL_TIMEOUT = 30

# 요약 길이 (LLM 호출 없이 단순 trim)
DEFAULT_SUMMARY_CHARS = 2000

# 핵심 fact 추출 시 최대 개수
DEFAULT_MAX_FACTS = 10

# PDF 텍스트 추출 시 페이지당 최대 글자 (메모리 보호)
DEFAULT_PDF_MAX_CHARS_PER_PAGE = 50_000

# PDF 최대 페이지 수 (1인 self-use는 보통 small/medium)
DEFAULT_PDF_MAX_PAGES = 100


@dataclass
class SourceRef:
    """입력 source 참조 (URL 또는 PDF)."""

    url: str = ""                          # http(s) URL
    path: str = ""                         # local file path
    source_type: SourceType = "url"        # "url" | "pdf"
    label: str = ""                        # 사용자 식별자 (선택)
    locale: str = "auto"                   # "ko" | "en" | "auto"

    def __post_init__(self) -> None:
        if self.source_type == "url" and not self.url:
            raise ValueError("source_type='url' requires url")
        if self.source_type == "pdf" and not self.path:
            raise ValueError("source_type='pdf' requires path")
        if not self.label:
            if self.source_type == "url":
                self.label = self.url[:80]
            else:
                self.label = Path(self.path).name

    @classmethod
    def from_url(cls, url: str, label: str = "", locale: str = "auto") -> "SourceRef":
        """URL 기반 SourceRef 생성."""
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Invalid URL scheme: {parsed.scheme} (http/https only)")
        return cls(url=url, path="", source_type="url", label=label, locale=locale)

    @classmethod
    def from_path(cls, path: str, label: str = "", locale: str = "auto") -> "SourceRef":
        """로컬 파일 기반 SourceRef 생성 (.pdf)."""
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {path}")
        return cls(url="", path=str(p), source_type="pdf", label=label or p.name, locale=locale)

    @property
    def display_name(self) -> str:
        return self.label or (self.url or self.path)


@dataclass
class ExtractedText:
    """추출된 텍스트 (URL 또는 PDF)."""

    title: str
    body: str                              # 본문 (HTML 또는 plain text)
    source: SourceRef
    metadata: dict = field(default_factory=dict)
    summary: str = ""                      # DEFAULT_SUMMARY_CHARS 글자 이내
    key_facts: list[str] = field(default_factory=list)
    char_count: int = 0
    language_hint: str = "auto"            # "ko" | "en" | "auto"

    def __post_init__(self) -> None:
        self.char_count = len(self.body)
        if not self.summary and self.body:
            self.summary = _simple_summary(self.body, DEFAULT_SUMMARY_CHARS)
        if not self.key_facts:
            self.key_facts = extract_key_facts(self.body, max_facts=DEFAULT_MAX_FACTS)


# ---------------------------------------------------------------------------
# URL ingestion (Trafilatura)
# ---------------------------------------------------------------------------


def ingest_url(ref: SourceRef, timeout: int = DEFAULT_URL_TIMEOUT) -> ExtractedText:
    """URL에서 본문 텍스트 추출 (Trafilatura).

    Args:
        ref: URL 기반 SourceRef
        timeout: HTTP fetch timeout (seconds)

    Returns:
        ExtractedText (title, body, metadata, summary, key_facts)

    Raises:
        ImportError: trafilatura 미설치 시
        RuntimeError: fetch 실패 / 본문 추출 실패 시
    """
    if ref.source_type != "url":
        raise ValueError("ingest_url requires source_type='url'")

    try:
        import trafilatura  # noqa: PLC0415
    except ImportError as e:
        raise ImportError(
            "trafilatura 미설치. `pip install trafilatura` 후 재시도."
        ) from e

    logger.info("URL fetch 시작: {}", ref.url)
    try:
        # 1) HTML fetch
        downloaded = trafilatura.fetch_url(ref.url, no_ssl=True)
    except Exception as e:
        raise RuntimeError(f"URL fetch 실패 ({ref.url}): {e}") from e

    if not downloaded:
        raise RuntimeError(f"URL 응답 비어있음 (fetch 실패): {ref.url}")

    # 2) 본문 추출
    try:
        # include_comments=False: 댓글 제외
        # include_tables=True: 표 보존
        # favor_precision=True: 정밀도 우선 (precision 0.938 vs recall 0.978, 1차 출처)
        extracted = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=True,
            favor_precision=True,
            with_metadata=True,
            output_format="json",
        )
    except Exception as e:
        raise RuntimeError(f"Trafilatura 추출 실패 ({ref.url}): {e}") from e

    if not extracted:
        raise RuntimeError(f"본문 추출 실패 (Trafilatura가 본문 못 찾음): {ref.url}")

    import json  # noqa: PLC0415
    try:
        data = json.loads(extracted)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Trafilatura JSON 파싱 실패: {e}") from e

    title = (data.get("title") or "").strip() or ref.label
    body = (data.get("text") or data.get("raw_text") or "").strip()
    metadata = {
        "description": data.get("description", ""),
        "sitename": data.get("sitename", ""),
        "url": data.get("url") or ref.url,
        "hostname": data.get("hostname", ""),
        "date": data.get("date", ""),
        "author": data.get("author", ""),
        "categories": data.get("categories", ""),
        "tags": data.get("tags", ""),
        "language": data.get("language", "auto"),
    }

    if not body:
        raise RuntimeError(f"본문 비어있음 (Trafilatura 결과 없음): {ref.url}")

    logger.info("URL 추출 완료: title={!r}, body={}자", title, len(body))

    return ExtractedText(
        title=title,
        body=body,
        source=ref,
        metadata=metadata,
        language_hint=metadata.get("language", "auto") or "auto",
    )


# ---------------------------------------------------------------------------
# PDF ingestion (PyMuPDF / fitz)
# ---------------------------------------------------------------------------


def ingest_pdf(ref: SourceRef, max_pages: int = DEFAULT_PDF_MAX_PAGES) -> ExtractedText:
    """PDF에서 텍스트 추출 (PyMuPDF).

    Args:
        ref: PDF 경로 기반 SourceRef
        max_pages: 최대 페이지 수 (메모리 보호)

    Returns:
        ExtractedText (title, body, metadata, summary, key_facts)

    Raises:
        ImportError: pymupdf 미설치 시
        RuntimeError: PDF 열기 실패 / 텍스트 추출 실패 시
    """
    if ref.source_type != "pdf":
        raise ValueError("ingest_pdf requires source_type='pdf'")

    try:
        import fitz  # type: ignore[import-not-found]  # PyMuPDF  # noqa: PLC0415
    except ImportError as e:
        raise ImportError(
            "PyMuPDF 미설치. `pip install pymupdf` 후 재시도."
        ) from e

    path = Path(ref.path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF 파일 없음: {path}")

    logger.info("PDF 추출 시작: {}", path)

    try:
        doc = fitz.open(str(path))
    except Exception as e:
        raise RuntimeError(f"PDF 열기 실패 ({path}): {e}") from e

    try:
        # 메타데이터 (제목/저자)
        meta = doc.metadata or {}
        title = (meta.get("title") or "").strip() or path.stem
        metadata = {
            "title": title,
            "author": meta.get("author", ""),
            "subject": meta.get("subject", ""),
            "keywords": meta.get("keywords", ""),
            "creator": meta.get("creator", ""),
            "producer": meta.get("producer", ""),
            "creation_date": str(meta.get("creationDate", "")),
            "mod_date": str(meta.get("modDate", "")),
            "page_count": doc.page_count,
        }

        # 페이지별 텍스트 추출
        page_texts: list[str] = []
        n_pages = min(doc.page_count, max_pages)
        for i in range(n_pages):
            try:
                page = doc.load_page(i)
                txt = page.get_text("text") or ""
                if len(txt) > DEFAULT_PDF_MAX_CHARS_PER_PAGE:
                    # 비정상적으로 큰 페이지는 자름 (메모리 보호)
                    txt = txt[:DEFAULT_PDF_MAX_CHARS_PER_PAGE]
                if txt.strip():
                    page_texts.append(f"[p.{i+1}]\n{txt.strip()}")
            except Exception as e:
                logger.warning("PDF page {} 추출 실패: {}", i + 1, e)
                continue

        body = "\n\n".join(page_texts).strip()

        if doc.page_count > max_pages:
            logger.warning(
                "PDF 페이지 수 {} > max_pages {} — 일부만 추출됨. max_pages 늘려 재시도 권장.",
                doc.page_count, max_pages,
            )
            metadata["truncated"] = True
            metadata["original_page_count"] = doc.page_count

    finally:
        doc.close()

    if not body:
        raise RuntimeError(f"PDF 본문 추출 실패 (텍스트 없음): {path}")

    logger.info("PDF 추출 완료: title={!r}, pages={}, body={}자", title, n_pages, len(body))

    return ExtractedText(
        title=title,
        body=body,
        source=ref,
        metadata=metadata,
        language_hint="auto",
    )


# ---------------------------------------------------------------------------
# Multi-source / Convenience
# ---------------------------------------------------------------------------


def ingest_sources(refs: list[SourceRef], **kwargs) -> list[ExtractedText]:
    """여러 source 일괄 ingestion.

    Args:
        refs: SourceRef 리스트
        **kwargs: ingest_url/ingest_pdf에 전달

    Returns:
        성공한 ExtractedText 리스트 (실패는 log만, skip)
    """
    results: list[ExtractedText] = []
    for i, ref in enumerate(refs, 1):
        try:
            if ref.source_type == "url":
                results.append(ingest_url(ref, **kwargs))
            elif ref.source_type == "pdf":
                results.append(ingest_pdf(ref, **kwargs))
            else:
                logger.warning("알 수 없는 source_type: {} (skip)", ref.source_type)
        except Exception as e:
            logger.error("source #{} ({}) 처리 실패: {}", i, ref.display_name, e)
            continue

    logger.info("총 {}/{} source 추출 성공", len(results), len(refs))
    return results


# ---------------------------------------------------------------------------
# Fair use helpers (LLM 호출 없이 deterministic)
# ---------------------------------------------------------------------------


def _simple_summary(body: str, max_chars: int = DEFAULT_SUMMARY_CHARS) -> str:
    """단순 trim 요약 (LLM 호출 없이)."""
    if len(body) <= max_chars:
        return body
    return body[:max_chars].rsplit(" ", 1)[0] + "..."


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?。!?])\s+|\n+")


def extract_key_facts(body: str, max_facts: int = DEFAULT_MAX_FACTS) -> list[str]:
    """핵심 fact 추출 (LLM 없이 결정론적).

    전략:
    - 본문을 문장 단위로 분리
    - "숫자 + 단위" 또는 "고유명사" 포함 문장 우선
    - 길이 30-300자 문장 위주

    ⚠️ Fair use 1차 출처: "amount and substantiality 최소화"
       - 이 함수는 researcher.py가 LLM으로 재구성할 때 참고용으로만 사용
       - 원문 그대로 복제 X, fact만 발췌

    Args:
        body: 원문 본문
        max_facts: 최대 fact 수

    Returns:
        핵심 fact 문장 리스트 (최대 max_facts개)
    """
    if not body:
        return []

    # 1) 문장 분리
    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(body) if s.strip()]

    # 2) fact-like sentence 채점
    fact_patterns = [
        re.compile(r"\d"),  # 숫자 포함
        re.compile(r"[\$€£¥₩]\s?\d"),  # 통화
        re.compile(r"\d+\s?(?:%|퍼센트|percent)"),  # 퍼센트
        re.compile(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+"),  # 영문 고유명사
        re.compile(r"[가-힣]{2,}(?:씨|님|대표|회장|교수|박사|연구원)"),  # 한국어 직함
    ]

    scored: list[tuple[float, str]] = []
    seen: set[str] = set()
    for sent in sentences:
        # 너무 짧거나 긴 문장 제외 (20자 이상, 350자 이하)
        # 1차 출처: 짧은 fact도 허용 (예: 영문 "Apple stock rose 5%.")
        if not (20 <= len(sent) <= 350):
            continue
        # 중복 제거 (앞 50자 기준)
        key = sent[:50]
        if key in seen:
            continue
        seen.add(key)

        # 점수 계산 (fact pattern 매치 수)
        score = sum(1.0 for p in fact_patterns if p.search(sent))
        # 길이 패널티 (너무 짧으면 약간 감점)
        if len(sent) < 30:
            score -= 0.3
        if len(sent) > 250:
            score -= 0.2

        if score > 0:
            scored.append((score, sent))

    # 3) 점수순 정렬 후 상위 N개
    scored.sort(key=lambda x: (-x[0], len(x[1])))
    return [sent for _, sent in scored[:max_facts]]


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "SourceRef",
    "ExtractedText",
    "SourceType",
    "ingest_url",
    "ingest_pdf",
    "ingest_sources",
    "extract_key_facts",
    "DEFAULT_URL_TIMEOUT",
    "DEFAULT_SUMMARY_CHARS",
    "DEFAULT_MAX_FACTS",
    "DEFAULT_PDF_MAX_PAGES",
]
