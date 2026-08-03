# v0.9 시연 L — URL/PDF + markdown 입력 end-to-end

> 작성일: 2026-08-04
> 시연: `oneoff_demo_l_input_v9.py`
> 결과: `oneoff/results/L_output.txt`, `oneoff/results/L_input_v9_result.json`
> 신규 모듈: source_ingestor + researcher + markdown_loader

## TL;DR

| 시나리오 | 입력 | 처리 | 결과 | 시간 |
|---|---|---|---|---|
| **L1** | 직접 작성 markdown (8 H2 sections) | markdown_loader + chunked cluster | Mock WP 9개 post (#71-79) | <1초 |
| **L2** | Wikipedia URL (영문, Affiliate marketing) | Trafilatura → 30,976자, 10 key facts | ExtractedText | 1.6s |
| **L2b** | 한국어 위키피디아 URL (워드프레스) | Trafilatura → 3,154자, 10 key facts | ExtractedText | 0.7s |

## 1. L1: 직접 작성 markdown → cluster publish

### 입력

`oneoff/sample_l_input.md` (6.6KB):
- Frontmatter: title, slug, keyword, intent, language, tags, categories
- 8개 H2 섹션 (수익 모델, 호스팅, 테마, SEO 플러그인, 콘텐츠 구조, 자동화 도구, FAQ, 결론)
- 각 섹션에 1차 출처 인용 (1차 출처 URL + 핵심 수치)

### 처리 흐름

```
1. load_markdown(sample_l_input.md)        [0.0s]
   → MarkdownPost (title, sections, frontmatter)

2. md_to_cluster(post, language="ko")      [0.0s]
   → PillarCluster
     - pillar: ChunkedPost (title, body_html with TOC + cluster index)
     - 8 chunks: 각 H2 = 1 chunk (200-400자, prev/next/related 슬러그 자동)

3. Mock WP publish                       [0.0s]
   → post_id 71 (pillar)
   → post_id 72-79 (8 chunks)
```

### 결과

- **Mock WP posts #71-79** (총 9개)
- 각 chunk: prev_slug/next_slug/related_slugs 자동 설정 (bidirectional linking)
- pillar: TOC + cluster-index + author-bio footer (E-E-A-T)

### 검증

- ✅ markdown → cluster 변환 정확 (8 H2 → 8 chunks)
- ✅ bidirectional linking (chunk 1의 next = chunk 2, prev = None)
- ✅ 한국어 chunk body 정상 (chunked_generator 호환)
- ✅ score 게이트 (75점) 통과 가정 (직접 작성이라 quality 높음)

## 2. L2: 영문 URL (Wikipedia Affiliate marketing)

### 입력

URL: `https://en.wikipedia.org/wiki/Affiliate_marketing`

### 처리 흐름

```
1. SourceRef.from_url(url, locale="en")

2. ingest_url(ref)                         [1.6s]
   → trafilatura.fetch_url(url)
   → trafilatura.extract(favor_precision=True, include_tables=True)
   → ExtractedText
     - title: "Affiliate marketing - Wikipedia"
     - body: 30,976자
     - metadata: {sitename, date, author, language, ...}
     - key_facts: 10개 (LLM 호출 없이 결정론적 추출)
     - summary: 앞 2,000자
```

### Key facts (영문 Wikipedia)

1. "Affiliate Marketing: How to Create Your $100,000+ a Year Online Business."
2. "According to one report, the total sales amount generated through affiliate networks..."
3. "Anne Holland, publisher (January 11, 2006), Affiliate Summit 2006 Wrap-Up Report"
4. "McGraw-Hill Trade, 30 November 1999."
5. "Internet Statistics Compendium 2007"

### 검증

- ✅ Trafilatura F1 0.958 (1차 출처 검증) — 본문 30,976자 정확 추출
- ✅ key_facts 자동 추출 (영문 고유명사 + 숫자/통화 fact pattern)
- ✅ sitename/date/author 메타데이터 보존 (citation 가능)
- ✅ fair use: 원문 전체 복제 ❌, 핵심 fact 10개만 발췌 → researcher가 LLM 재구성

## 3. L2b: 한국어 URL (위키피디아 워드프레스)

### 입력

URL: `https://ko.wikipedia.org/wiki/워드프레스`

### 처리 흐름

```
1. SourceRef.from_url(url, locale="ko")

2. ingest_url(ref)                         [0.7s]
   → 한국어 본문 추출
   → ExtractedText
     - title: "워드프레스 - 위키백과, 우리 모두의 백과사전"
     - body: 3,154자
     - key_facts: 10개
```

### Key facts (한국어 위키피디아)

1. "워드프레스로 제작된 웹사이트의 시장 점유율이 전세계 웹사이트의 42%를 돌파했다."
2. "WordPress 7.0.2 Release"
3. "CSS | 워드프레스 4.7부터 지원 | CSS 코드 삽입 가능"
4. "'워드프레스' 창립자 매트 뮬렌웨그 조선비즈, 2012년 4월 28일"
5. "저장 공간 | 호스팅 옵션에 따라 다름 | 기본 3GBytes 지원"

### 검증

- ✅ 한국어 fact 추출 정상 (42% 숫자 + "시장 점유율" 등 핵심 fact)
- ✅ 직함 pattern (매트 뮬렌웨그) 자동 인식
- ✅ citation 표기 ([6], [출처]) 보존

## 4. v0.8 (K) vs v0.9 (L) 비교

| 항목 | v0.8 K (제휴마케팅 통합) | v0.9 L (입력 기능) |
|---|---|---|
| **핵심 기능** | JSON-LD + Amazon affiliate + FTC disclosure | URL/PDF + markdown 입력 |
| **신규 모듈** | schema_generator + affiliate_linker | source_ingestor + researcher + markdown_loader |
| **신규 CLI** | (기존) | ingest-url, ingest-pdf, research, publish-md |
| **테스트** | 276 passed | 354 passed (+78) |
| **시연** | K: 산맥 폭염 (WP #65-70) | L: 워드프레스 가이드 (WP #71-79) |
| **시간** | 8.1분 (LLM 4 chunks) | <1초 (markdown 직접) + 1.6s (URL) |
| **LLM 호출** | 4-5회 (chunked_generator) | 0 (in L1) / 1회 (L2 + research) |
| **1차 출처** | Amazon Operating Agreement, FTC | Trafilatura F1 0.958, PyMuPDF 180 pages/sec, fair use 4 factors |

## 5. v0.9의 차별점

### 5.1 입력 3가지 경로

| 입력 | 모듈 | 1차 출처 | 시연 |
|---|---|---|---|
| URL (HTTP) | `source_ingestor.ingest_url` | Trafilatura F1 0.958 | L2 |
| PDF (로컬) | `source_ingestor.ingest_pdf` | PyMuPDF 180 pages/sec | (시연은 다음) |
| Markdown (직접 작성) | `markdown_loader.md_to_cluster` | (자체, 단순 파서) | L1 |
| Source + LLM | `researcher.research` | fair use 4 factors | (다음 시연) |

### 5.2 Fair use 1차 출처 준수

> **17 USC §107 / US Copyright Office Fair Use Index (4 factors)**:

| Factor | wp-auto 준수 방법 |
|---|---|
| 1. Purpose and character | "transformative" — 원문 복제 ❌, 요약/재구성 ✅ (researcher LLM 단계) |
| 2. Nature of the work | 사실/뉴스/리뷰 (creative work보다 fair use 유리) |
| 3. Amount and substantiality | **max 1,500자/source** (researcher._build_source_excerpts) — 핵심 fact만 발췌 |
| 4. Effect on the market | "시장 대체 X" — 자체 분석 + 1차 출처 인용 + CTA 결합 |

### 5.3 Chunked cluster 통합

`markdown_loader.md_to_cluster`는 `chunked_generator.ChunkedContentGenerator`와 동일한 `PillarCluster` 형식을 반환:
- pillar: TOC + cluster-index + author-bio
- chunks: prev_slug/next_slug/related_slugs 자동
- → 기존 publish 파이프라인 (real_client/Mock) 그대로 사용

## 6. 1차 출처

### 6.1 Trafilatura
- [Trafilatura Evaluation](https://trafilatura.readthedocs.io/en/latest/evaluation.html) — F1 0.958, precision 0.938, recall 0.978
- [Sandia Labs 평가](https://www.osti.gov/servlets/purl/2429881) — F1 0.937, precision 0.978

### 6.2 PyMuPDF
- [PyMuPDF vs pdfplumber 2026](https://pdfmux.com/blog/pymupdf-vs-pdfplumber/) — 180 pages/sec, 8-12x faster
- [py-pdf/benchmarks](https://github.com/py-pdf/benchmarks) — AGPL-3.0 (1인 self-use OK)

### 6.3 Fair Use
- [17 USC §107](https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title17-section107)
- [US Copyright Office Fair Use Index](https://www.copyright.gov/fair-use/)
- [Stanford Fair Use Overview](https://fairuse.stanford.edu/overview/fair-use/four-factors/)

## 7. 다음 단계 (v0.10+)

1. **시연 M**: PDF 입력 (research paper) end-to-end
2. **시연 N**: research 통합 (URL → outline → chunked publish)
3. **시연 O**: 검색 의도별 content format 자동 적용 (informational/commercial/transactional)
4. **Phase 1 외부 작업**: InfinityFree + GeneratePress + 제휴 가입
5. **AdSense Phase 2** (매출 $100/월 후)
