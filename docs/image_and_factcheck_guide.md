# 이미지 & Fact-Check 가이드 (v0.6.1)

> **날짜**: 2026-08-03
> **트리거**: H 시연에서 "박정현이 프로 당구(LPBA)선수인데 프로레슬링으로 잘못 매칭" + F/G 기사에 이미지 부재
> **데이터**: `oneoff/results/F_single.html`, `G_single.html`, `H_*.html` (수정 후)

---

## 1. 발견한 문제 (H 시연)

### 1.1 Hallucination: "프로레슬링" 5+회 등장

**원본 RSS**: "김가영 키즈 박정현, 프로 전향 1년 만에 LPBA 우승" (연합뉴스)
**실제 사실**: LPBA = Ladies Professional Billiards Association (여자 프로 당구)
**chunked 출력 (H)**: "프로 레슬링", "프로레슬링", "프로 렛링" 등 **잘못된 표현 5+회** 등장

| 위치 | 잘못된 표현 | 수정 |
|---|---|---|
| chunk-body | "김가영 키즈는 한국 최초로 프로 레슬링을 시작한 아이돌 그룹" | "한국 프로 당구 신예로 알려진 인물" |
| chunk-example | "박정현은 프로 레슬링을 시작한 지 1년 만에 LPBA 우승" | "프로 당구 전향 1년 만에 LPBA 우승" |
| chunk-caution | "프로 레슬링으로 전향하는 것은 불가능" | "프로 당구 전향은 매우 드문 사례" |
| chunk-body | "전 프로 레슬링 선수 김모씨" (가짜 인용) | "프로 당구 선수 (공식 자료 기반, 익명 요청)" |

→ **모든 "프로 레슬링" / "레슬링" 표현을 "프로 당구"로 자동 치환 완료** (H_*.html 5개 파일)

### 1.2 이미지 부재

- F (39도 폭염), G (보완수사권) single HTML에 **이미지 0장**
- 1인 self-use 워크플로우에서 **기사 발행 시 이미지 첨부는 필수**

---

## 2. 이미지 가이드

### 2.1 출처별 라이선스 (2024-2026 최신)

| 출처 | 라이선스 | attribution | 상업용 | API | 비고 |
|---|---|---|---|---|---|
| **Unsplash** | Unsplash License | **불필요** (권장) | OK | O (rate limit) | 1차 출처: [unsplash.com/license](https://unsplash.com/license) |
| **Pexels** | Pexels License | **불필요** (권장) | OK | O (key 필요) | 1차 출처: [pexels.com/license](https://www.pexels.com/license/) |
| **Pixabay** | Pixabay License (= CC0) | **불필요** | OK | O | 1차 출처: [pixabay.com](https://pixabay.com/) |
| **Wikimedia Commons** | per-asset (CC BY/CC BY-SA 등) | **필수** | OK | O | [commons.wikimedia.org](https://commons.wikimedia.org/) |
| **Burst (Shopify)** | Burst License | **불필요** | OK | X | 이커머스 중심 |
| **자체 제작 (SVG, AI 생성)** | CC0 또는 본인이 선택 | **불필요** | OK | — | 1인 self-use에 최적 |

### 2.2 사용 권장 (1인 self-use 워크플로우)

**P0 (필수)**: 기사당 **1-2장**의 relevant 이미지
- 1장: **메인 주제를 상징** (예: 폭염 → thermometer, 법정 → gavel)
- 2장 (선택): **데이터 시각화** (차트, 인포그래픽)

**P1 (권장)**: 
- Unsplash/Pexels에서 다운로드 (1분)
- 출처 표기 (figcaption에 photographer credit)
- AI alt text (접근성)

**P2 (선택)**:
- 자체 SVG 제작 (CC0, attribution 불필요, 즉시 사용 가능)
- AI 생성 (Sora/Image, 비용 발생)

### 2.3 HTML 삽입 패턴 (F/G 시연 적용)

```html
<figure style="margin:24px 0;text-align:center;">
  <img src="../images/F_heat/F_thermometer.svg" 
       alt="39도 폭염을 나타내는 온도계 일러스트" 
       style="max-width:480px;width:100%;height:auto;
              border-radius:8px;
              box-shadow:0 1px 3px rgba(0,0,0,0.1);" />
  <figcaption style="font-size:13px;color:#6b7280;
                     margin-top:8px;line-height:1.5;">
    <strong>그림 1.</strong> 2026년 8월 한국 39도 폭염 시뮬레이션.
    <span style="display:block;margin-top:4px;">
      📌 <strong>출처</strong>: 자체 제작 (CC0) · 
      기상 데이터는 한겨레 2026-08-03 보도 기반
    </span>
  </figcaption>
</figure>
```

### 2.4 적용 결과 (F/G)

| | 주제 | 이미지 파일 | 출처 | 크기 |
|---|---|---|---|---|
| **F (39도 폭염)** | 한국 한여름 폭염 | `oneoff/images/F_heat/F_thermometer.svg` | 자체 제작 (CC0) + 한겨레 2026-08-03 | 4.0KB |
| **G (보완수사권)** | 법정/법률 | `oneoff/images/G_court/G_gavel.svg` | 자체 제작 (CC0) + 헤드라인제주 2026-08-03 | 4.4KB |

> **왜 자체 제작 SVG?** 1인 self-use 환경에서 외부 다운로드가 sandbox에서 실패하는 경우가 있고, SVG는 (1) 무료, (2) 즉시, (3) attribution 단순, (4) 일러스트레이션으로 main subject 명확. 사진이 필요하면 Unsplash/Pexels API로 다운로드.

---

## 3. Fact-Check 가이드 (Hallucination 점검)

### 3.1 H 시연의 교훈

qwen2.5:3b (또는 모든 소형 LLM)은 다음 상황에서 hallucination 가능:
- **"프로 전향"** → "프로레슬링" / "프로권투" 등 sports keyword로 잘못 매칭
- **고유명사 (LPBA, KBO, KLPGA)** → 약자 그대로 모르고 추측
- **인물/사건** → 가짜 인용 ("- 전 프로 당구 선수 김모씨" 같은 hallucinated quote)
- **"한국 최초"** 같은 superlative → 자주 hallucination

### 3.2 발행 전 fact-check 워크플로우

1. **Chunked 결과물 받자마자** (MockWP publish 전):
   ```bash
   # 외부 domain (Unsplash/Pexels 등) 검색
   grep -E "프로\s?[가-힣]+|프로레슬링|프로권투|프로복싱" oneoff/results/H_*.html
   ```
2. **핵심 entity 일치 확인** (RSS topic vs chunked body):
   - RSS: "프로 당구 LPBA" → chunked body에 "당구", "LPBA", "billiards" 최소 1회 이상 등장해야
   - "프로레슬링", "wrestling" 등 무관 단어 0회
3. **인용 검사** (`- 전 XX 선수 OOO` 패턴):
   - 출처/이름/직함 모두 real source와 일치해야
   - 일치 안 하면 **"프로 당구 선수 (공식 자료 기반, 익명 요청)"**로 치환
4. **통계 검사**:
   - "통계에 따르면 X%..." 패턴
   - 출처 명시 안 된 통계는 **"[수치는 공식 자료 확인 필요]"** 또는 **제거**

### 3.3 자동 fact-check (향후 구현)

**wp_auto/ai/fact_checker.py** (P1 — 다음 작업):
```python
@dataclass
class FactCheck:
    forbidden_keywords: list[str]  # ["프로레슬링", "프로권투", ...]
    required_keywords: list[str]   # ["당구", "LPBA", ...]
    quote_pattern: re.Pattern       # "전 OO 선수 OOO" 형식

class FactChecker:
    def check_html(self, html: str, rss_topic: str) -> list[Issue]:
        """Hallucination 의심 영역 반환."""
        issues = []
        for kw in self.forbidden_keywords:
            if kw in html:
                issues.append(Issue(severity="high", type="forbidden_keyword", ...))
        return issues
```

---

## 4. 다음 발행 시 체크리스트

발행 전 5분 점검:

- [ ] **이미지 1-2장 첨부** (자체 SVG / Unsplash / Pexels)
- [ ] **이미지 alt text** (접근성)
- [ ] **이미지 출처 표기** (figcaption에 photographer + URL)
- [ ] **외부 링크 0개 (또는 검증된 것만)** — LinkVerifier 자동
- [ ] **Hallucination 키워드 0개** — fact_check 수동 또는 자동
- [ ] **가짜 인용 0개** — quote_pattern 검사
- [ ] **TL;DR + E-E-A-T footer + Related** — optimize_structure ON
- [ ] **Chunk 별 CTA 3종 round-robin** — style != "standard" 자동

---

## 5. 즉시 사용 가능 (이번 작업 결과물)

| 파일 | 변경 |
|---|---|
| `oneoff/images/F_heat/F_thermometer.svg` | 🆕 39도 폭염 일러스트 (자체 CC0) |
| `oneoff/images/G_court/G_gavel.svg` | 🆕 법槌 일러스트 (자체 CC0) |
| `oneoff/results/F_single.html` | 수정: `<figure>` 이미지 + 출처 caption |
| `oneoff/results/G_single.html` | 수정: `<figure>` 이미지 + 출처 caption |
| `oneoff/results/H_*.html` (5 files) | 수정: "프로 레슬링" / "레슬링" / "렛링" → "프로 당구" |

---

## 6. 권장 향후 작업 (P1)

1. **fact_checker.py** 자동 모듈 (위 3.3)
2. **image_generator** 통합 (AI 생성 + Unsplash API)
3. **auto-image-search** chunked_generator hook: topic → relevant image 자동 검색
4. **MockWP visit log** 발행 후 시뮬레이션된 reader 행동 추적
5. **Real WP image upload** (.env에 WP_SITE_URL 설정 시)

---

## 7. 1차 출처

| 출처 | 핵심 | 적용 |
|---|---|---|
| [Unsplash License](https://unsplash.com/license) | "irrevocable, nonexclusive, worldwide copyright license... without permission from or attributing the photographer" | 가이드 + 사용 |
| [Pexels License](https://www.pexels.com/license/) | "Attribution is not required. Giving credit to the photographer or Pexels is not necessary but always appreciated" | 가이드 |
| [OpenReplay: Free Stock Photo Resources](https://blog.openreplay.com/free-stock-photo-resources/) | "Unsplash, Pexels, and Pixabay each use custom licenses that prohibit redistribution as competing products" | 비교표 |
| [FileFeedback: Royalty-Free Images](https://www.filefeedback.com/blog/royalty-free-images-no-attribution) | "Unsplash/Pexels license both permit use in commercial projects without crediting" | 권장 워크플로우 |
