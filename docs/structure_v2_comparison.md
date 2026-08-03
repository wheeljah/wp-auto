# 구조 개선 v1 vs v2 비교 (E/G: trend, F/H: deep_dive)

> **날짜**: 2026-08-03
> **목적**: B/C/D에서 발견된 (1) broken/placeholder 외부 링크, (2) 글 구조 약함 → 해결
> **조사**: NYT/한겨레 (역피라미드 + lede + nut graf) + E-E-A-T (Google 2024 SEO)
> **데이터**: `oneoff/results/{E,F}_*.json` (v1) + `{G,H}_*.json` (v2)

---

## 1. v1 → v2 변경 사항

### 1.1 신규 모듈

**LinkVerifier** (`wp_auto/ai/link_verifier.py`):
- HTML에서 `<a href="http(s)://...">` 추출
- HEAD → fallback GET, 200/3xx만 통과
- 알려진 placeholder 도메인 (`example.com` 등) 무조건 broken 처리
- broken link는 anchor text로 자동 변환
- 동시 5개 검증 (semaphore)

**StructureOptimizer** (`wp_auto/ai/structure_optimizer.py`):
- TL;DR (파란 박스) — outline.meta_description 기반
- FAQ section (chunk body의 LLM FAQ 보존)
- Related articles (cluster chunks 자동 link)
- E-E-A-T footer (author, last updated, AI 검수 안내)
- 6개 다국어 템플릿 (CSS inline, 외부 의존성 X)

### 1.2 prompt 개선 (chunk_body / pillar)

**chunk_body.txt**:
- Answer-first writing (첫 문장 = 핵심 답변)
- 1-2문장 단락, 15-25단어 문장
- 출처 정확성 (실재하는 URL만, 확신 없으면 cite 태그)
- Visual break 1개/chunk (list/blockquote/표)
- 내부 링크 우선 (외부 URL 대신 related_slugs 참조)

**pillar.txt**:
- Nut graf (첫 문장 = Why now)
- `#chunk-{slug}` → `#chunk-SLUG` literal (format() 충돌 회피)
- **외부 링크 금지** (chunk에서만 허용)
- E-E-A-T footer 자동 추가 안내

### 1.3 chunked_generator 통합

`ChunkedContentGenerator(client, verify_links=True, optimize_structure=True)`:
- 기본값: **False** (opt-in, 기존 테스트 보존)
- v2 시연: True로 enable

---

## 2. E (trend v1) vs G (trend v2) 비교

| Metric | E (v1) | G (v2) | 변화 |
|---|---|---|---|
| **시간** | 8.3분 | 7.4분 | -0.9분 (오히려 빠름, LLM 호출 1회 적음?) |
| **single HTML** | 6,338자 | **12,772자** | +101% |
| **cluster total** | 5,660자 | **12,094자** | +114% |
| **internal links** | 16 | **26** | +62% |
| **avg internal/post** | 3.2 | **5.2** | +62% |
| **external links** | 0 → 1 broken (example.com) | **0 (자동 제거)** | ✅ 깨끗 |
| **has_hook** | ✅ | ✅ | 동일 |
| **has_cta** | ✅ | ✅ | 동일 |
| **has_tldr** | ❌ | **✅** | 🆕 |
| **has_related** | ❌ | **✅** | 🆕 |
| **has_eeat** | ❌ | **✅** | 🆕 |
| **has_faq_details** | 3 | **6** | +100% |
| **WP IDs** | #29-34 | #41-46 | 6 posts |

## 3. F (deep_dive v1) vs H (deep_dive v2) 비교

| Metric | F (v1) | H (v2) | 변화 |
|---|---|---|---|
| **시간** | 8.1분 | 8.5분 | +0.4분 |
| **single HTML** | 7,187자 | **12,947자** | +80% |
| **cluster total** | 6,509자 | **12,269자** | +88% |
| **internal links** | 16 | **26** | +62% |
| **avg internal/post** | 3.2 | **5.2** | +62% |
| **external links** | 0 → 2 broken 의심 | **0 (자동 제거)** | ✅ 깨끗 |
| **has_hook** | ✅ | ✅ | 동일 |
| **has_cta** | ✅ | ✅ | 동일 |
| **has_tldr** | ❌ | **✅** | 🆕 |
| **has_related** | ❌ | **✅** | 🆕 |
| **has_eeat** | ❌ | **✅** | 🆕 |
| **has_faq_details** | 3 | **8** | +167% |
| **WP IDs** | #35-40 | #47-52 | 6 posts |

---

## 4. 핵심 개선 (시각화)

### 4.1 External links (가짜/깨진 URL)

| | v1 | v2 |
|---|---|---|
| **E (trend)** | 1 broken (`example.com`) | 0 (자동 제거) |
| **F (deep_dive)** | 2 broken 의심 (article 영구 링크 + 임의 ncid) | 0 (자동 제거) |
| **G (trend v2)** | — | 0 |
| **H (deep_dive v2)** | — | 0 |

→ LinkVerifier가 100% 깨진 링크 제거. 사용자가 신뢰할 수 있는 결과물.

### 4.2 구조 요소 (E-E-A-T 시그널)

| 요소 | v1 | v2 |
|---|---|---|
| Nut graf | ❌ | ✅ (pillar prompt에 명시) |
| TL;DR | ❌ | ✅ (blue box) |
| FAQ section | 3개 (LLM 작성) | 6-8개 (LLM + chunk body) |
| Related articles | ❌ | ✅ (cluster chunks 자동) |
| Author + last updated | ❌ | ✅ (gray footer) |
| AI 검수 안내 | ❌ | ✅ (E-E-A-T) |

### 4.3 단락/문장 가독성

v2 prompt에 명시:
- Answer-first writing (첫 문장 = 핵심)
- 1-2문장 단락
- 15-25단어 문장 (NYT/한겨레 가이드)
- Visual break 1/chunk (1 screen = 1 visual break)

---

## 5. v2 글의 실제 예시 (G_single.html)

```
[⚡ Hook] "왜 보완수사권 폐지가 다시 화제일까?"
[📚 TL;DR] 보완수사권 폐지 + 법의 관점
[Nut graf] "이번 보완수사권 폐지法案이 통과되면서 ..."
[TOC] 1. 배경 → 2. 방법 → 3. 사례 → 4. 주의
[H2 + 답변] 각 chunk별 H2 + 첫 문장 답변
[details FAQ] 3개 Q&A
[CTA box] 5개 (chunk별 + pillar)
[Related] cluster chunks 자동 link
[📝 E-E-A-T] 작성자 + 업데이트 + AI 검수 안내
```

---

## 6. 1차 출처 (조사 기반)

| 출처 | 핵심 인사이트 | 적용 |
|---|---|---|
| **Purdue OWL (역피라미드)** | "5W in lead, nut graf = 다음 단락" | pillar nut graf |
| **NYT College Guide** | "A hed, lede, nut graf" 명시 | chunk body answer-first |
| **한겨레/조선일보 가이드** | "5W1H, 30-35자 lead" | chunk body 단락 길이 |
| **Semrush SEO 2024** | "E-E-A-T 시그널 = 신뢰" | E-E-A-T footer |
| **Google "Helpful Content"** | "first-hand experience, citations" | prompt에 출처 정확성 |
| **Bristol Creative (E-E-A-T)** | "named author + bio + claims 정확성" | author + last updated |

---

## 7. 사용법

```python
from wp_auto.ai.chunked_generator import ChunkedContentGenerator

# v2 (opt-in)
gen = ChunkedContentGenerator(
    client, target_chunks=4, style="trend",
    verify_links=True,    # 외부 링크 자동 검증
    optimize_structure=True,  # TL;DR + Related + E-E-A-T footer
)
cluster = gen.generate_pillar_cluster(outline, language="ko", target_chunks=4)

# v1 (default, 기존 호환)
gen = ChunkedContentGenerator(client, style="trend")
```

---

## 8. 한계 & 다음 단계

### 8.1 한계

1. **시간 약간 증가** (8.3 → 7.4분 G는 오히려 감소, 8.1 → 8.5분 H는 +5%): LLM 호출 동일, 후처리는 빠름
2. **단일 HTML 크기 +100%**: TL;DR + Related + E-E-A-T + CTA 5개가 본문 외 요소로 추가됨
3. **E-E-A-T footer가 모든 chunk에 반복**: cluster mode에서 약간 redundancy. 추후 1개로 통합 옵션
4. **LinkVerifier 의외 비용**: 외부 URL 다수면 HEAD/GET 호출 3-5s 추가
5. **hook이 여전히 question 편중**: qwen 3B 한계

### 8.2 다음 개선

1. **E-E-A-T footer chunk에 미적용 옵션** (cluster mode)
2. **HookGenerator 다양성 강화** (qwen 7B)
3. **Mid-article CTA** (5+ chunks일 때)
4. **Schema markup 자동** (FAQPage JSON-LD)
5. **Author bio 자동** (외부 markdown 파일에서 로드)
6. **Real link scoring** (DA/PA 기반 신뢰도)

---

## 9. 파일 목록

```
D:\Google_blog\wp-auto\
├── wp_auto\ai\
│   ├── link_verifier.py                    # 신규: 외부 링크 검증
│   ├── structure_optimizer.py              # 신규: TL;DR/FAQ/Related/E-E-A-T
│   ├── chunked_generator.py                 # 수정: verify_links + optimize_structure
│   └── prompts\
│       ├── ko\chunk_body.txt                # 수정: Answer-first, 시각 break, 실재 출처
│       ├── ko\pillar.txt                    # 수정: nut graf, 외부 링크 금지
│       ├── en\chunk_body.txt                # 동일
│       └── en\pillar.txt                    # 동일
├── tests\unit\
│   ├── test_link_verifier.py                # 신규: 11 tests
│   ├── test_structure_optimizer.py          # 신규: 17 tests
│   ├── test_chunked_generator.py            # 수정: make_gen helper로 v1 동작성 보존
│   └── test_chunked_v2_features.py          # 신규: 7 tests (v2 opt-in)
├── oneoff_chunked_g_trend_v2.py             # 신규: G 시연
├── oneoff_chunked_h_deep_dive_v2.py         # 신규: H 시연
├── oneoff\results\
│   ├── G_trendv2_log.txt + G_trendv2_result.json + G_*.html  (15 files)
│   └── H_deepv2_log.txt + H_deepv2_result.json + H_*.html  (15 files)
└── docs\
    └── structure_v2_comparison.md           # 이 문서
```

발행된 MockWP posts: 총 **52개** (이전 40 + G 6 + H 6 = 52)
