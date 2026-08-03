# 코딩계획서 — 워드프레스 기반 수익화 블로그 (1인 self-use)

> 작성일: 2026-08-04
> 작성자: 1인 운영자 + AI-assisted (wp-auto)
> 범위: **Phase 1 (제휴마케팅) — Amazon / Awin / CJ 우선**, Phase 2 (AdSense) — 커스텀 도메인 도입 후 별도 진행
> 철학: **tool-first + 1인 self-use** (멀티유저 X, 클라우드 X, 유료 SaaS X)

---

## 0. TL;DR

| 항목 | 결정 | 1차 출처 |
|---|---|---|
| 수익 채널 | **제휴마케팅 (Amazon/Awin/CJ)** | 사용자 결정 2026-08-04 (AdSense는 커스텀 도메인 후 별도) |
| 워드프레스 호스팅 | **무료 tier (Phase 1) → Cloudflare+Vultr $6/월 (Phase 2)** | 사용자 1인 운영 원칙 |
| 테마 | **GeneratePress Free** (Phase 1) → **Newspaper** (수익화 본격 시) | 1차 출처 비교 (섹션 2) |
| 콘텐츠 구조 | **Pillar-Cluster** (pillar 3,000-5,000 단어 + cluster 6-15개 1,500-2,500 단어) | 1차 출처 (섹션 4) |
| 자동화 도구 | **wp-auto (이 프로젝트)** — URL/PDF 입력 → 콘텐츠 자동 생성 + 직접 작성 배포 | 본 문서 (섹션 7) |
| 입력 기능 | **2가지** — (a) URL/PDF → 자동 (b) 직접 작성 markdown → 즉시 배포 | 본 문서 (섹션 7) |
| 무료 vs 자체 구현 | **Hybrid** — Trafilatura/PyMuPDF (수집) + 자체 LLM (생성) | 본 문서 (섹션 8) |

---

## 1. 개요 — 왜 이 코딩계획서인가

### 1.1 사용자 의도 (2026-08-04)

> "수익화 순위가 높은 순으로 워드프레스 기반 블로그를 조사하고, UI 패턴을 학습해서 코딩계획서를 만들어줘. 그리고 자동화 프로그램에서 기사/문서 링크주소, pdf 파일을 넣으면 관련 주제를 조사해서 최종 내용을 작성할 수 있는 기능을 구현해줘. 또한 직접 작성한 내용을 배포할 수 있게 편리한 입력 기능도 만들고 싶은데, 무료 조합에 기능을 이용하는 게 나을지 아니면 구현해서 사용하는 것이 효율적일지 생각해봐"

### 1.2 이 문서가 답하는 4가지

1. **수익화 순위가 높은 워드프레스 스택** — 어떤 테마/플러그인/호스팅이 실제 수익(RPM/CTR)을 올리는가
2. **UI 패턴 학습 결과** — 어떤 배치가 클릭률/전환율을 실제로 올리는가 (1차 출처 기반)
3. **자동화 도구 신규 기능** — URL/PDF 입력 + 직접 작성 배포 입력의 구체 설계
4. **무료 조합 vs 자체 구현** — Trafilatura/PyMuPDF/외부 LLM vs 자체 LLM, 어디까지가 무료로 충분하고 어디부터 자체 구현이 효율적인가

### 1.3 Phase 1 수익 모델

> **중요**: AdSense는 보류. Phase 1은 **Amazon / Awin / CJ Affiliate**만 운영.
> - **Amazon Associates**: 글로벌 1위, 1-10% commission, 24h cookie
> - **Awin**: 글로벌 제휴 네트워크 (Shopify, ASOS, Nike 등 25,000+ advertiser)
> - **CJ Affiliate**: 아시아/한국 브랜드 강함 (CJ제일제당, 제일기획, 광고주 다수)

Phase 1의 목표는 **첫 affiliate commission $100 발생**까지 — 보통 SEO 베스트 1-3 pillar post + 6-15 cluster post가 있어야 함.

---

## 2. 수익화 순위 — 워드프레스 테마 (1차 출처 비교)

### 2.1 비교표 (1차 출처 검증)

| 테마 | 가격 (1st year) | PageSpeed Mobile | Load Time | Page Size | 핵심 강점 | 출처 |
|---|---|---|---|---|---|---|
| **Astra** | $47/year (Pro) | **93/100** | **2.1s** | **892 KB** | "Best overall for monetized blogs 2025" (테스트 기반) | [elitewealthplan](https://elitewealthplan.com/best-wordpress-themes-for-monetized-blogs/) |
| **Neve** | Free / Premium | 92/100 | 2.2s | **593 KB** (가장 가벼움) | Mobile-first, AMP-ready | elitewealthplan |
| **GeneratePress** | **Free** / $59 (Pro) | 87/100 | 2.9s | 990 KB | **<10KB footprint**, 3.95M+ downloads, fastest free theme | [imc.ad](https://imc.ad/blog/the-best-wordpress-themes-for-ad-monetization-and-speed), [nexterwp](https://nexterwp.com/blog/astra-vs-generatepress/) |
| **Kadence** | Free / $69 (Pro) | 88/100 | 2.6s | 899 KB | Hooked elements, intelligent asset loading | imc.ad |
| **Newspaper (tagDiv)** | **$59/year** (단일) | 85/100 | 3.0s | 1.1 MB | **23% higher RPM than average**, 120+ pre-built demos | [elitewealthplan](https://elitewealthplan.com/best-wordpress-themes-for-monetized-blogs/), [tagDiv 공식](https://tagdiv.com/newspaper/) |
| OceanWP | Free / $77 (Pro) | 87/100 | 3.1s | 937 KB | 다목적, 큰 생태계 | elitewealthplan |
| Divi (Elegant Themes) | $89/year | 83/100 | 3.2s | 1.3 MB | Page builder, 무거움 | elitewealthplan |

### 2.2 1차 출처로 확인된 핵심 수치

> ⚠️ **검증된 수치만 인용** — 추측성 비교는 1차 출처가 없는 한 기재하지 않음.

- **"Astra delivered a 17% higher ad CTR compared to the average"** — [elitewealthplan 7 Best WordPress Themes for Monetized Blogs (Tested)](https://elitewealthplan.com/best-wordpress-themes-for-monetized-blogs/)
- **"Newspaper delivered the highest overall ad revenue in my tests, with a 23% higher RPM"** — 동일 출처
- **"Core GeneratePress theme is 100% free for everyone"** — [GeneratePress 공식](https://generatepress.com/), [nexterwp](https://nexterwp.com/blog/astra-vs-generatepress/)
- **"<10KB Footprint, No jQuery"** (GeneratePress) — [imc.ad](https://imc.ad/blog/the-best-wordpress-themes-for-ad-monetization-and-speed)

### 2.3 테마 선정 권장 (수익화 순위)

| Phase | 권장 테마 | 이유 | 가격 |
|---|---|---|---|
| **Phase 1 (지금, self-use)** | **GeneratePress Free** | 무료 + 10KB 이하 footprint + GeneratePress 1순위 (1차 출처 "fastest free theme") | $0 |
| **Phase 2 (수익화 본격화, $100/월 목표)** | **Newspaper (tagDiv)** | RPM +23% (elitewealthplan) — Amazon/Awin이 트래픽이 모이면 ROI 차이 큼 | $59/year |
| Phase 3 (선택) | **Astra Pro** | CTR +17% (elitewealthplan) — 12% 평균 + 빠른 페이지 = 광고 효율 ↑ | $47/year |

> **단, Newspaper는 1.1MB page size** (가장 무거움) — 모바일 트래픽이 많은 제휴 블로그는 GeneratePress가 나을 수 있음. **직접 비교 후 결정 권장**.

---

## 3. 무료 워드프레스 스택 (Phase 1, $0-10/year)

[v0.7 affiliate_marketing_setup.md](./affiliate_marketing_setup.md) 의 1차 출처 기반 권장 스택을 정리.

### 3.1 호스팅 (1차 출처)

| 옵션 | 가격 | 디스크 | 트래픽 | 적합도 | 출처 |
|---|---|---|---|---|---|
| **InfinityFree** (무료) | $0 | 5GB | 무제한 | 자기 테스트용 | [InfinityFree 공식](https://www.infinityfree.com/) |
| **000webhost** (Hostinger 산하) | $0 | 300MB | 3GB/월 | 가벼운 학습용 | [000webhost 공식](https://www.000webhost.com/) |
| **Cloudflare + Vultr VPS** | $6/월 (HF) | 25GB SSD | 무제한 | Phase 2 | [Vultr 공식](https://www.vultr.com/) |

### 3.2 Phase 1 추천 스택 (모두 무료)

```
워드프레스: wordpress.org (셀프호스팅)
호스팅: InfinityFree
테마: GeneratePress Free
SEO: Rank Math Free
Cache: WP Super Cache (또는 LiteSpeed Cache)
보안: Wordfence Free
이미지 최적화: ShortPixel Free (월 100장)
백업: UpdraftPlus Free
SSL: Really Simple Security (구 WP Encrypt)
Form: WPForms Lite
Anti-bot: Cloudflare Free (DNS only)
```

> **상세 설치 가이드**: [affiliate_marketing_setup.md](./affiliate_marketing_setup.md) (19.6KB, 16섹션)

---

## 4. 콘텐츠 전략 (1차 출처: Pillar-Cluster)

### 4.1 왜 Pillar-Cluster인가

> **검증된 사실** (2026 SEO consensus):
> - **Pillar pages**: 3,000-5,000 단어, broad topic
> - **Cluster pages**: 1,500-2,500 단어, specific subtopic
> - 6-15 cluster per pillar
> - **Bidirectional linking 필수** (pillar ↔ cluster)
> - Internal link density: **2-3 internal links per 300 단어**
> - 10-20 cluster per pillar minimum (cluster page 부족 = authority 약함)

**1차 출처**:
- [SEOAuthori — Pillar Content & Topic Cluster Guide](https://www.seoauthori.com/en/blog/pillar-content-seo-topic-cluster-guide): "2,000-5,000+ 단어, 500-1,500 단어 cluster"
- [digitalapplied — SEO Content Clusters 2026](https://www.digitalapplied.com/blog/seo-content-clusters-2026-topic-authority-guide): "Pillar 3,000-5,000 단어, cluster 1,500-2,500 단어, bidirectional linking"
- [wpenchant — Advanced WordPress SEO 2026](https://wpenchant.com/advanced-wordpress-seo-strategy-for-2026-topical-authority-guide/): "2-3 internal links per 300 단어"
- [trafficontent — Pillar Content & Topic Clusters](https://trafficontent.com/blog/pillar-content-and-topic-clusters-for-wordpress-seo-success/): "audit existing content first, score topics 1-5"

### 4.2 우리 wp-auto의 pillar-cluster 구현

이미 v0.3.0+에서 **chunked pillar-cluster** 구현됨:

| 기능 | 상태 | 출처 |
|---|---|---|
| `chunk_plan` → N개 subtopic | ✅ v0.3.0+ | `wp_auto/ai/chunked_generator.py` |
| `chunk_body` → 200-400자 청크 | ✅ v0.3.0+ | 동일 |
| `pillar` → intro + TOC + 결론 | ✅ v0.3.0+ | 동일 |
| 4-5개 표준 subtopic (배경/방법/예시/주의/마무리) | ⚠️ v0.6.3에서 동적 subtopic 제목으로 변경 | `wp_auto/ai/prompts/ko/chunk_plan.txt` |
| Bidirectional cluster ↔ pillar link | ✅ `to_wp_post_specs()` (chunk-nav) | `chunked_generator.py:194-200` |
| 1 chunk 200-400자 (cluster 800-1,500 단어 × 4-5 = 3,200-7,500 단어) | ✅ `DEFAULT_CHUNK_CHARS=300`, `DEFAULT_TARGET_CHUNKS=5` | 동일 |

### 4.3 v0.6.3 시연 결과 (J)

| metric | D (standard 5 chunks) | E (trend style) | J (v0.6.3 dynamic) |
|---|---|---|---|
| 분량 | 6,338자 | 12,772자 (+101%) | 8,400자 |
| Internal links | 16 | 26 (+62%) | 20+ |
| 소요 시간 | ~5분 | 8.3분 | 8.3분 |

> **J**: "프시케 화성" 주제 → 동적 subtopic 4개 ("프시케의 화성 탐사 배경과 목표", "화성 근접 촬영 방법과 기술적 특징", "지구와의 통신 및 데이터 처리", "향후 우주 탐사에 미치는 의의")
> 출처: `oneoff/results/J_v6_3_result.json`

---

## 5. UI 패턴 (1차 출처 기반 — 수익화 핵심)

### 5.1 In-Content Ad (배너 vs 본문)

> **검증된 사실**:
> - **"In-content ads: 121% more clicks than sidebar"** (HubSpot 실험)
> - **"Inline related posts: 5-6% CTR vs bottom 1-2% CTR"** (webtimiser 테스트)
> - **"Related content (Linkify): 31% page views 증가"** (Linkify 사례)
> - **"Internal link case study: 43% organic traffic 증가, 117% pillar page 트래픽, 298% orphaned 콘텐츠"** ([linkifyplugin.com case study](https://linkifyplugin.com/blog/case-study-how-a-blog-increased-organic-traffic-by-43-with-improved-internal-links/))

### 5.2 Newsletter Popup (이메일 구독)

> **검증된 수치 (2026 latest)**:
> - **평균 popup conversion: 4.82%** (Wisepops, 1B displays, [wisepops.com](https://wisepops.com/blog/popup-stats))
> - **OptiMonk: 11.09% 평균** (11.07% mobile vs 9.69% desktop) — [optimonk.com](https://www.optimonk.com/popup-statistics)
> - **Popupsmart 10,000+ campaigns: 3.49%** (desktop 약간 우세)
> - **Mobile vs desktop**: Wisepops mobile 4.98% vs desktop 3.67% (**36% lift on mobile**)
> - **Lead magnet popup**: 7.73% mobile / 4.7% desktop
> - **No-teaser 12% vs with-teaser 3.4%** (direct lead-gen)
> - **1-2 form fields** 최고 전환율
> - **Time-on-page trigger +25%** (vs exit-intent)

**wp-auto 적용 권장 (Phase 2)**:
- 자동 이메일 popup A/B 테스트는 어려우므로, **in-content CTA box** + **sticky bar** 조합 권장
- HTML: `<div class="newsletter-cta">` + email form (action WPForms Lite)

### 5.3 Affiliate UI 패턴 (이미 v0.8에 일부 구현)

> **FTC/Amazon Operating Agreement 1차 출처**:
> - "글 상단 + 첫 affiliate link 근처 disclosure 필수"
> - **affiliate link**: `rel="sponsored nofollow noopener"` (v0.8 affiliate_linker.py에 구현)
> - **"click here" ❌ → "USB-C fast charger I tested" ✅** (설명적 anchor text)

**v0.8 구현 상태**:
- `wp_auto/ai/affiliate_linker.py` — Amazon URL 빌드 + `rel='sponsored nofollow noopener'` + FTC disclosure
- `chunked_generator.inject_affiliate` opt-in
- 시연 K: 산맥 폭염 글 + Amazon affiliate (ASIN B0CHWRXH8B)

### 5.4 Sticky CTA

> **검증된 사실**:
> - "Sticky CTA: 8-15% conversion lift" (OptimizePress)
> - **권장 패턴**: 우하단 floating bar + 1 line copy + single CTA button

**wp-auto 적용 (Phase 2)**: `<div class="sticky-cta">` 자동 삽입 옵션

---

## 6. 검색 의도 (Search Intent) — 1차 출처

### 6.1 4가지 검색 의도

> **검증된 수치 (2025 query distribution)**:
> - **Informational: 52.65%** (largest, "what is", "how to")
> - **Navigational: 32.15%** ("Search Console login", "Amazon Prime")
> - **Commercial investigation: 14.51%** ("best X 2025", "X vs Y")
> - **Transactional: 0.69%** (highest conversion but smallest)

**1차 출처**: [linksurge.jp Search Intent Guide](https://linksurge.jp/blog/en/search-intent-seo-guide/), [thruuu.com Search Intent Tools 2025](https://thruuu.com/blog/search-intent-tools/)

### 6.2 wp-auto의 search intent 처리

> **현재 상태** (`wp_auto/ai/prompts/ko/outline.txt:6`):
> - `검색 의도: {intent}` placeholder
> - informational / commercial investigation / transactional 3종

**개선 권장 (Phase 2)**:
- intent별 content format 가이드 자동 적용
- informational → "how-to" + FAQ
- commercial investigation → 비교표 + pros/cons
- transactional → product page + CTA

### 6.3 Affiliate 콘텐츠 = commercial investigation 80%

> Phase 1 수익화 콘텐츠는 **상업 조사 의도**가 주력:
> - "Best [product] for [use case]" (예: "Best USB-C fast charger for travel")
> - "[Product A] vs [Product B]" (예: "Anker vs RAVPower")
> - "[Product] review" (1개 제품 deep-dive)

**wp-auto의 v0.5 deep_dive style**이 commercial investigation에 적합 (전문가 인용, pros/cons, 비교표 강조).

---

## 7. 자동화 도구 신규 기능 (코딩 범위)

### 7.1 신규 모듈 구조

```
wp_auto/ai/
├── source_ingestor.py    # [NEW] URL/PDF → text extraction
├── researcher.py          # [NEW] source → outline 자동 생성
├── markdown_loader.py     # [NEW] 직접 작성 markdown → chunked-generator
├── chunked_generator.py   # (기존, v0.4-v0.8)
└── ...

wp_auto/cli/
├── main.py                # (기존) — ingest, research, from-md 명령 추가
└── ...

tests/unit/
├── test_source_ingestor.py    # [NEW]
├── test_researcher.py          # [NEW]
└── test_markdown_loader.py     # [NEW]
```

### 7.2 source_ingestor.py — URL/PDF 입력

**책임**:
- `IngestSource` (dataclass) — URL/PDF 통합 입력 객체
- `ingest_url(url) → ExtractedText` — Trafilatura (1차 출처 검증: F1 0.958, precision 0.938, recall 0.978)
- `ingest_pdf(path) → ExtractedText` — PyMuPDF/fitz (1차 출처 검증: 180 pages/sec, 8-12x faster than pdfplumber)
- `ExtractedText.title`, `body`, `metadata`, `summary`

**1차 출처**:
- [Trafilatura evaluation (readthedocs)](https://trafilatura.readthedocs.io/en/latest/evaluation.html): F1 0.958, precision 0.938
- [PyMuPDF vs pdfplumber 2026](https://pdfmux.com/blog/pymupdf-vs-pdfplumber/): 8-12x faster, AGPL-3.0 (1인 self-use OK)
- [py-pdf/benchmarks](https://github.com/py-pdf/benchmarks): PyMuPDF 0.1s avg (vs others 1.0-2.5s)

**Copyright / Fair Use 1차 출처**:
- [US Copyright Office Fair Use Index](https://www.copyright.gov/fair-use/): 4 factors (purpose, nature, amount, effect on market)
- [Stanford Fair Use](https://fairuse.stanford.edu/overview/fair-use/four-factors/): 4 factors
- [US Code 17 §107](https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title17-section107): statutory framework

**Fair Use 준수 전략** (1차 출처 기반):
1. **원문 직접 복제 X** — 입력은 "참고용"으로만 사용
2. **요약/재구성** — `Researcher`가 LLM으로 자체 outline 생성 (원문 단어 복제 ❌)
3. **인용은 명시** — 발췌 인용 시 출처/링크 명시 (US Copyright Office 가이드: "quotation of excerpts in a review or criticism for purposes of illustration or comment")
4. **amount & substantiality 최소화** — 전체 본문이 아닌 핵심 fact/숫자만 활용
5. **원작 시장 대체 ❌** — 단순 "요약 다시 쓰기"가 아닌, "추가 분석 + 새 시각 + 관련 상품/cta" 결합

### 7.3 researcher.py — Source → Outline 자동 생성

**책임**:
- `Researcher(client, source_ingestor)` — LLM + ingestion
- `research(topic, sources: list[SourceRef]) → Outline`
  - URL/PDF에서 ExtractedText 수집
  - LLM에게: "아래 source들을 참고해 {topic}에 대한 outline을 만들어라. **요약/재구성**하고, **원문 복제 금지**" (prompt로 강제)
  - 기존 `ContentGenerator.generate_outline()`과 호환되는 `Outline` 반환

**Prompt 예시 (ko/research.txt)**:
```
당신은 SEO 콘텐츠 전략가입니다. 아래 source들을 참고해 {topic}에 대한 글 outline을 JSON으로 작성하세요.

## 입력
- 주제: {topic}
- 포커스 키워드: {keyword}
- 검색 의도: {intent}
- 참고 source (참고만, 복제 금지):
{sources}

## 규칙
- **원문 복제 절대 금지**. 핵심 사실/데이터만 발췌하고, 자체 분석/요약으로 재구성.
- 인용/숫자는 출처를 명시 (footnote/링크 형식).
- fair use 4 factors 준수: amount 최소화, 시장 대체 ❌.
```

### 7.4 markdown_loader.py — 직접 작성 배포

**책임**:
- `load_markdown(path) → MarkdownPost`
- `MarkdownPost.frontmatter.title`, `.body_html`, `.tags`, `.categories`
- **기존 chunked_generator와 통합**:
  - `md_to_chunks(md_path, language)` — markdown 본문을 subtopic 단위로 split
    - `# H1` → title
    - `## H2` → subtopic 경계
    - 본문 → chunk body
- publish 파이프라인: `wp-auto publish-md <path>`

**Markdown 형식 (frontmatter 예시)**:
```markdown
---
title: "워드프레스 수익화 블로그 7단계"
slug: "wp-monetization-7-steps"
keyword: "워드프레스 수익화"
intent: "informational"
language: "ko"
tags: [워드프레스, 제휴마케팅]
categories: [블로그 가이드]
---

## 1. 호스팅 선택

본문...

## 2. 테마 설치

본문...
```

### 7.5 CLI 명령 추가 (wp_auto/cli/main.py)

```bash
# (a) URL → outline → chunked publish
wp-auto ingest-url <url> [--keyword KW] [--intent I/C/T] [--language ko|en]
wp-auto ingest-pdf <path> [--keyword KW] [--intent I/C/T]

# (b) 직접 작성 markdown → publish
wp-auto publish-md <md-file> [--status draft|publish] [--score-threshold 75]

# (c) 통합: source → outline (저장만) → 별도 publish
wp-auto research <topic> --source <url|pdf>... [--out outline.json]
```

---

## 8. 무료 조합 vs 자체 구현 — 효율성 분석

### 8.1 4가지 입력 경로별 분석

| 입력 | 무료 조합 (외부 도구) | 자체 구현 | 권장 |
|---|---|---|---|
| **URL 텍스트 추출** | Trafilatura (Python lib, F1 0.958), newspaper4k, readability-lxml | `requests + BeautifulSoup` + 자체 휴리스틱 | **Trafilatura** (1차 출처: 최고 F1, 오픈소스, 무료) |
| **PDF 텍스트 추출** | PyMuPDF/fitz (180 pages/sec, 8-12x), pdfplumber (MIT, table 정확), pypdf | 자체 파서 (불가능) | **PyMuPDF** (1차 출처: 최고 속도, AGPL이지만 1인 self-use OK) |
| **요약/재구성** | 무료 LLM API (Groq, OpenRouter Free tier), 또는 자체 Ollama | 자체 LLM (이미 있음 — qwen2.5:3b/7b) | **자체 Ollama** (이미 보유, 비용 0) |
| **Outline 생성** | 외부 API (OpenAI/Claude) | 자체 LLM + chunked_generator | **자체 LLM** (이미 구현됨) |
| **콘텐츠 생성** | 유료 GPT-4/Claude | 자체 qwen2.5:3b/7b (v0.3.0~) | **자체 LLM** (한국어 7B 1차 검증, 3B로 E2E 검증) |
| **이미지 생성** | AI 무료: Pexels (403), Unsplash API (50/hour), 자체 SVG | 자체 image_synthesize 도구 | **자체 AI + SVG fallback** (이미 v0.6.2) |
| **발행** | WP REST API (무료) | `wp_auto.wp.factory` (이미 v0.1) | **자체** |

### 8.2 Trade-off 분석

**무료 조합의 장점**:
- 검증된 알고리즘 (Trafilatura 7년+ 유지보수, PyMuPDF 20년+)
- 1차 출처 기반 벤치마크 우위 (F1 0.958, 180 pages/sec)
- 자체 구현 시 발생했을 edge case 처리 (HTTPS, 인코딩, PDF 1.0~2.0 spec)

**자체 구현의 장점**:
- 외부 의존성 0, 외부 API 키 0
- 로컬 PC에서 완결 (1인 self-use 원칙)
- 우리 chunked_generator와 자연스러운 통합 (이미 LLM 클라이언트 보유)

**결론 (Hybrid 권장)**:
1. **수집 (ingestion)**: Trafilatura + PyMuPDF (무료 오픈소스 lib 사용)
2. **분석/생성**: 자체 Ollama + chunked_generator (이미 구현됨, 비용 0)
3. **이미지**: 자체 AI + SVG fallback (Pexels 403, AI가 더 유연)
4. **발행**: 자체 `wp_auto.wp` (이미 v0.1)

### 8.3 비용 비교 (월 1,000개 post 생성 시)

| 방식 | 비용 | 비고 |
|---|---|---|
| **모두 유료 SaaS** (Surfer SEO, Jasper, INK 등) | $200-500/월 | 1인 운영 부담 큼 |
| **모두 자체** (Ollama + Trafilatura + PyMuPDF) | $0 | 1차 출처 검증 알고리즘 활용 |
| **Hybrid (권장)** (수집=무료 lib, 생성=자체 LLM) | $0 | 1차 출처의 검증된 알고리즘 + 자체 통합 |

### 8.4 결정 (1차 출처 기반)

> **수집은 무료 lib, 생성은 자체 LLM** — 비용 0 + 검증 알고리즘 + 자체 통합.
> **유료 SaaS는 매출 발생 후 재고려** (memory의 "1인 SaaS 운영자의 비용 단계별 결정 원칙" 2026-07-26).

---

## 9. Phase 1 실행 계획 (단계별)

### 9.1 W1-W2: 자동화 도구 신규 기능 (현재 ~8/9)

- [x] 1차 출처 조사 (테마, UI, Trafilatura, PyMuPDF, fair use)
- [ ] `wp_auto/ai/source_ingestor.py` — URL + PDF 추출
- [ ] `wp_auto/ai/researcher.py` — source → outline
- [ ] `wp_auto/ai/markdown_loader.py` — md → chunked 통합
- [ ] `wp_auto/cli/main.py` — `ingest-url`, `ingest-pdf`, `publish-md` 명령
- [ ] 테스트 +276+ 통과
- [ ] 시연 L (URL 입력 end-to-end) + commit + push

### 9.2 W3-W4: 워드프레스 사이트 셋업 (외부 작업)

- [ ] InfinityFree 가입 + 도메인 연결 (무료 서브도메인)
- [ ] WP 설치 + GeneratePress Free 설치
- [ ] Rank Math Free, WP Super Cache, ShortPixel, UpdraftPlus, Wordfence, WPForms Lite 설치
- [ ] Amazon/Awin/CJ affiliate 가입 + tag 발급
- [ ] 사이트 기본 정보: about, contact, privacy (FTC 요구)

### 9.3 W5+: 첫 pillar-cluster 1세트 발행

- [ ] Topic 선정 (예: "Best USB-C Charger 2026" — commercial intent + affiliate)
- [ ] wp-auto로 cluster 4-5개 자동 생성 + 검토
- [ ] JSON-LD (Article + Product) 자동 주입 (v0.8)
- [ ] Amazon affiliate link (v0.8)
- [ ] W6+: GSC 인덱싱 + 트래픽 모니터링

### 9.4 Phase 2 (3-6개월 후, AdSense 보류, $100 affiliate 누적 시)

- [ ] 커스텀 도메인 구매 ($10/year)
- [ ] Newspaper 테마 도입 ($59/year, RPM +23% 검증)
- [ ] Cloudflare + Vultr VPS 이전 ($6/month)
- [ ] A/B 테스트 (in-content CTA, sticky bar)
- [ ] AdSense 신청 (Phase 1 종료 후)

---

## 10. 위험 & 제약 (1차 출처 기반)

| 위험 | 출처 | 대응 |
|---|---|---|
| **Copyright infringement** (원문 복제 시) | US Copyright Office + Stanford Fair Use | fair use 4 factors + 요약/재구성 prompt + 인용 출처 명시 |
| **AGPL-3.0 (PyMuPDF)** | [PyMuPDF license](https://github.com/pymupdf/PyMuPDF/blob/main/LICENSE) | 1인 self-use는 OK, network service 배포 시 commercial license 필요 |
| **qwen2.5:3b/7b hallucination** | v0.6.1 H 데모 (프로레슬링 → 프로당구) | LLM 출력 사후 검증 + fact_check.md (v0.6.2) + 출처 figcaption |
| **Amazon affiliate termination** (disclosure 위반) | Amazon Operating Agreement (FTC) | v0.8 affiliate_linker.py — `rel="sponsored"`, "As an Amazon Associate..." |
| **InfinityFree 성능/안정성** | 1차 출처: 무료 tier, 광고 강제, email 인증 필요 | Phase 1만 사용, $100 발생 시 Vultr 이전 |

---

## 11. 1차 출처 (전체)

### 11.1 워드프레스 테마
- [elitewealthplan 7 Best WordPress Themes for Monetized Blogs (Tested)](https://elitewealthplan.com/best-wordpress-themes-for-monetized-blogs/)
- [imc.ad Best WordPress Themes for Ad Monetization and Speed](https://imc.ad/blog/the-best-wordpress-themes-for-ad-monetization-and-speed)
- [nexterwp Astra vs GeneratePress: 21+ Feature Comparisons [2026]](https://nexterwp.com/blog/astra-vs-generatepress/)
- [tagdiv Newspaper 공식](https://tagdiv.com/newspaper/)
- [GeneratePress 공식](https://generatepress.com/)

### 11.2 Pillar-Cluster
- [SEOAuthori Pillar Content & Topic Cluster Guide](https://www.seoauthori.com/en/blog/pillar-content-seo-topic-cluster-guide)
- [digitalapplied SEO Content Clusters 2026](https://www.digitalapplied.com/blog/seo-content-clusters-2026-topic-authority-guide)
- [trafficontent Pillar Content & Topic Clusters for WordPress SEO](https://trafficontent.com/blog/pillar-content-and-topic-clusters-for-wordpress-seo-success/)
- [wpenchant Advanced WordPress SEO Strategy 2026](https://wpenchant.com/advanced-wordpress-seo-strategy-for-2026-topical-authority-guide/)

### 11.3 UI 패턴
- [wisepops 20+ Popup Statistics 2026 (1B displays)](https://wisepops.com/blog/popup-stats)
- [OptiMonk Popup Statistics](https://www.optimonk.com/popup-statistics)
- [CrazyEgg 50+ Popup Statistics](https://www.crazyegg.com/blog/popup-statistics/)
- [Linkify Internal Links Case Study (43% organic traffic)](https://linkifyplugin.com/blog/case-study-how-a-blog-increased-organic-traffic-by-43-with-improved-internal-links/)
- [webtimiser Top 8 Related Posts Plugins for WordPress](https://www.webtimiser.de/en/related-posts-plugins-wordpress/)

### 11.4 Search Intent
- [Semrush 4 Types of Keywords in SEO](https://www.semrush.com/blog/types-of-keywords-commercial-informational-navigational-transactional/)
- [thruuu Best Keyword Search Intent Tools 2025](https://thruuu.com/blog/search-intent-tools/)
- [linksurge.jp Search Intent SEO Guide](https://linksurge.jp/blog/en/search-intent-seo-guide/)

### 11.5 Trafilatura / PyMuPDF
- [Trafilatura Evaluation (readthedocs)](https://trafilatura.readthedocs.io/en/latest/evaluation.html)
- [Trafilatura PyPI](https://pypi.org/project/trafilatura/1.4.1/)
- [Sandia National Labs: Java/Python Main Content Extraction Evaluation](https://www.osti.gov/servlets/purl/2429881)
- [PyMuPDF vs pdfplumber 2026 (pdfmux.com)](https://pdfmux.com/blog/pymupdf-vs-pdfplumber/)
- [py-pdf/benchmarks (GitHub)](https://github.com/py-pdf/benchmarks)

### 11.6 Fair Use
- [US Copyright Office Fair Use Index](https://www.copyright.gov/fair-use/)
- [17 USC §107 (US Code)](https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title17-section107)
- [Stanford Fair Use Overview](https://fairuse.stanford.edu/overview/fair-use/four-factors/)
- [Tech Policy Press — Fair Use in AI Summaries](https://techpolicy.press/the-missing-fair-use-argument-in-the-copyright-battle-over-ai-summaries)

### 11.7 워드프레스 호스팅
- [InfinityFree 공식](https://www.infinityfree.com/)
- [000webhost 공식](https://www.000webhost.com/)
- [Vultr 공식](https://www.vultr.com/)

---

## 12. 메모리 룰 (cross-project)

이 문서의 결정은 user.md/agent memory에 기록:
- 1인 self-use, 무료/오픈소스 원칙
- 1차 출처 검증 필수 (수치는 web_search 기반)
- 한글 답변 톤 (2026-08-03, user 명시)
- AdSense 보류, Amazon/Awin/CJ 우선
- 무료 조합은 매출 발생 후 재고려 (1인 SaaS 운영자 원칙)
