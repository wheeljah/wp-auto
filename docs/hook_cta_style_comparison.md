# Hook + CTA + Style 비교 (E: trend / F: deep_dive)

> **날짜**: 2026-08-03
> **하드웨어**: GTX 1050 (2GB, CPU-only), qwen2.5:3b, 16GB RAM
> **목적**: B/C/D 시연에서 발견한 한계 — "글은 잘 썼지만, 방문자 hook이 약하고 CTA가 없음" — 를 해결하기 위한 trend / deep_dive style 추가
> **데이터**: `oneoff/results/{E,F}_*.json` + `E_*_log.txt` / `F_*_log.txt`

---

## 1. 신규 기능 개요

### 1.1 HookGenerator (`wp_auto/ai/hook_generator.py`)

**4종 hook 자동 생성** (첫 1-2문장으로 reader scroll stop):

| Type | 의도 | 예시 |
| --- | --- | --- |
| `question` | 호기심 자극 | "왜 X는 Y일까?" |
| `stat` | 구체적 수치 충격 | "X%의 사용자가 Y를 모른다" |
| `story` | 인물/사례 도입 | "어느 날 A는 B를 발견했다" |
| `reversal` | 상식 뒤집기 | "X라고 알려진 Y의 진실은 Z" |

- LLM 1회 호출 → 4종 후보 JSON 반환
- `select_best(criterion="engagement")` 로 가장 강력한 hook 1개 선택 (길이 50-200자 + "?" 또는 숫자 가산)
- language isolation (qwen이 다른 언어로 새는 것 방지) — SYSTEM_PROMPTS dict 사용

### 1.2 CTAInjector (`wp_auto/ai/cta_injector.py`)

**3종 CTA 자동 생성 + HTML injection**:

| Type | 라벨 (ko/en) | 색상 | 예시 |
| --- | --- | --- | --- |
| `informational` | 📚 더 알아보기 / Learn more | blue | "더 알아보기" |
| `action` | 🚀 지금 시작 / Get started | red | "지금 시작하기" |
| `social_proof` | 👥 함께해요 / Join us | green | "커뮤니티 참여" |

- LLM 1회 호출 → 3종 후보 JSON
- `select_best(criterion="engagement")` — 강한 동사 + 적정 길이 가산
- CSS inline box로 삽입 (외부 스타일시트 불필요)
- `position="end" | "after_first_h2"` 지원

### 1.3 ChunkedContentGenerator style 통합

신규 파라미터 `style: str = "standard"`:

| Style | prompt 추가 | hook | CTA | 용도 |
| --- | --- | --- | --- | --- |
| `standard` | 없음 | X | X | 기본 정보성 글 (기존 동작) |
| `trend` | [트렌드 리포트 스타일] — 최신 데이터/통계/뉴스 앵글, Why Now, 시각적 요소 | O (pillar) | O (chunks + pillar, round-robin) | newsjacking, hot topic |
| `deep_dive` | [심층 분석 스타일] — 다각도 분석, 인용, 데이터, 반론, 출처 | O (pillar) | O (chunks + pillar, round-robin) | 전문 리포트, 가이드 |

**메커니즘**:
- style instruction은 prompt 끝에 append (prompt 파일 변경 없음)
- chunked 5개당 CTA는 1번 LLM 호출로 3종 생성 → round-robin 분배
- pillar CTA는 chunk에서 안 쓴 type 우선 (다양성)
- hook은 pillar 시작 부분에 yellow callout box로 prepend

---

## 2. E / F 시연 결과

### E: trend_report (한글 4 chunks, 8.3분)

- **RSS**: "오늘 광주·대구·부산 39도" (한겨레)
- **Topic**: "39도의 폭염…올 여름 최고 온도 동네별 막강 정보"
- **Chunks**: 배경/방법/사례/주의사항
- **Hook (pillar)**: type=**question** — "왜 이 수치가 현실인지 궁금해? 광주, 대구, 부산의 폭염 최고기온은 각각 얼마나 높았나?"
- **CTA 분배** (4 chunks): informational / action / social_proof / informational (3종 모두 사용)
- **Pillar CTA**: action
- **Single HTML**: 6,338자, 16 internal links → WP #29
- **Cluster**: 5 posts (pillar + 4 chunks), 5,660자, avg 3.2 links → WP #30-34

### F: deep_dive (한글 4 chunks, 8.1분)

- **RSS**: "'3백억 원대 사기 의혹' 차가원 대표 구속영장" (MBC 뉴스)
- **Topic**: "차가원 대표 사기 의혹, 구속영장 실질심사에서의 출석"
- **Chunks**: 배경/방법/사례/주의사항
- **Hook (pillar)**: type=**question** (deep_dive 적합)
- **CTA 분배**: informational / action / social_proof / informational (3종 모두 사용)
- **Pillar CTA**: action
- **Single HTML**: 7,187자, 16 internal links → WP #35
- **Cluster**: 5 posts, 6,509자, avg 3.2 links → WP #36-40

---

## 3. 종합 비교 (Standard vs Trend vs Deep Dive)

| Metric | Standard (D, 5 chunks) | Trend (E, 4 chunks) | Deep Dive (F, 4 chunks) |
| --- | --- | --- | --- |
| **style** | standard | trend | deep_dive |
| **chunks** | 5 | 4 | 4 |
| **총 시간** | 5.5분 | 8.3분 (+51%) | 8.1분 (+47%) |
| **cluster 시간** | 4.7분 | 7.0분 | 7.3분 |
| **hook 있음?** | X | O (question) | O (question) |
| **CTA 개수** | 0 | 5 (1+4) | 5 (1+4) |
| **single HTML** | 5,304자 | 6,338자 (+19%) | 7,187자 (+35%) |
| **single links** | 21 | 16 | 16 |
| **cluster posts** | 6 | 5 | 5 |
| **cluster total** | 4,449자 | 5,660자 (+27%) | 6,509자 (+46%) |
| **avg links** | 3.5 | 3.2 | 3.2 |
| **WP IDs** | #22-28 | #29-34 | #35-40 |

> **시간 +50%**: hook LLM 호출 1 + cta LLM 호출 2 + style instruction이 prompt를 길게 만듦 → chunk당 5-10s 추가

### 3.1 주요 차이

**Standard (D)**:
- ✅ 빠름 (5.5분), 단순
- ❌ Hook 없음 → 첫 문단이 일반적 intro
- ❌ CTA 없음 → 클릭/전환 행동 유도 약함

**Trend (E)**:
- ✅ 강력한 hook (Why Now)
- ✅ 다양한 CTA (informational/action/social_proof) round-robin
- ✅ single HTML +19% (더 풍부한 본문)
- ⚠️ +3분 (LLM 호출 3회 추가)
- 사용 사례: 뉴스/트렌드 기고, hot topic 발행

**Deep Dive (F)**:
- ✅ 가장 풍부한 본문 (+35-46%)
- ✅ 다각도 분석 (인용, 데이터, 반론)
- ✅ 권위있는 톤
- ⚠️ +3분, chunk당 가장 길음 (50s+)
- 사용 사례: 전문 리포트, 가이드, 백서

---

## 4. Engagement 메트릭 (예측)

style=trend / deep_dive가 추가한 engagement 요소:

| 요소 | 효과 (예측, 검증 필요) | 위치 |
| --- | --- | --- |
| **Hook** (yellow callout) | 첫 5초 scroll stop ↑ | pillar 시작 |
| **CTA 3종 round-robin** | chunk 끝마다 행동 유도 (정보/행동/사회증거) | 각 chunk |
| **Pillar CTA** | 마지막 1회 (action 추천) | pillar 끝 |
| **Style instruction** (트렌드/심층) | 글의 톤/깊이 자체가 engagement ↑ | 본문 전반 |

> ⚠️ 실제 dwell time / CTR / 전환율은 **publish 후 실측 필요** (MockWP는 측정 안 함)

---

## 5. 사용법

```python
from wp_auto.ai.chunked_generator import ChunkedContentGenerator

# Trend report
gen = ChunkedContentGenerator(client, target_chunks=4, style="trend")
cluster = gen.generate_pillar_cluster(outline, language="ko", target_chunks=4)

# Deep dive
gen = ChunkedContentGenerator(client, target_chunks=4, style="deep_dive")
cluster = gen.generate_pillar_cluster(outline, language="ko", target_chunks=4)

# Standard (기존, default)
gen = ChunkedContentGenerator(client)
cluster = gen.generate_pillar_cluster(outline, language="ko")
```

CLI / Web UI 통합은 다음 단계.

---

## 6. 한계 & 다음 단계

### 6.1 한계

1. **시간 +50%**: hook/cta LLM 호출이 추가 비용. qwen 7B에서 더 길어질 수 있음.
2. **Hook 다양성 부족**: qwen 3B가 question type을 선호 (E/F 모두 question). 7B 또는 더 큰 모델에서 stat/reversal 더 다양해질 듯.
3. **CTA 위치 고정**: chunk 끝 + pillar 끝. mid-article CTA는 현재 미사용.
4. **A/B 테스트 부재**: 어떤 hook/CTA가 효과적인지 실측 안 됨.
5. **Engagement 실측 없음**: dwell time / CTR / scroll depth는 publish 후 분석 필요.

### 6.2 다음 개선 (선택)

1. **Hook type 우선순위**: style별로 선호 hook type 강제 (trend → stat/reversal, deep_dive → question/story)
2. **Mid-article CTA**: 5+ chunks일 때 중간 chunk에 CTA 삽입
3. **Schema markup 자동**: Article, FAQ, HowTo JSON-LD 자동 추가
4. **A/B 테스트 인프라**: 동일 outline에 2개 style 생성 → WP에 2개 post 발행 → 비교
5. **Engagement 분석**: MockWP visit log → 가장 효과적인 hook/CTA 추적

---

## 7. 파일 목록

```
D:\Google_blog\wp-auto\
├── wp_auto\ai\
│   ├── hook_generator.py                    # 신규: 4종 hook
│   ├── cta_injector.py                      # 신규: 3종 CTA + HTML injection
│   ├── chunked_generator.py                 # 수정: style 파라미터 + hook/CTA 통합
│   └── prompts\
│       ├── ko\hooks.txt                     # 신규: 한국어 hook prompt
│       ├── ko\cta.txt                       # 신규: 한국어 CTA prompt
│       ├── en\hooks.txt                     # 신규: 영문 hook prompt
│       └── en\cta.txt                       # 신규: 영문 CTA prompt
├── tests\unit\
│   ├── test_hook_generator.py               # 신규: 8 tests
│   ├── test_cta_injector.py                 # 신규: 10 tests
│   └── test_chunked_generator.py            # 수정: +6 style tests
├── oneoff_chunked_e_trend.py                # 신규: trend 시연
├── oneoff_chunked_f_deep_dive.py            # 신규: deep_dive 시연
├── oneoff\results\
│   ├── E_trend_log.txt                      # E 실행 로그
│   ├── E_trend_result.json                  # E 결과 메타
│   ├── E_single.html                        # E single HTML
│   ├── E_cluster_1..5.html                  # E cluster HTMLs
│   ├── F_deepdive_log.txt                   # F 실행 로그
│   ├── F_deepdive_result.json               # F 결과 메타
│   ├── F_single.html                        # F single HTML
│   └── F_cluster_1..5.html                  # F cluster HTMLs
└── docs\
    └── hook_cta_style_comparison.md         # 이 문서
```

발행된 MockWP posts: 총 **40개** (이전 28 + E 6 + F 6 = 40)

- 이전 (B/C/D/기본): WP #1-28
- E (trend): WP #29-34 (1 single + 5 cluster)
- F (deep_dive): WP #35-40 (1 single + 5 cluster)
