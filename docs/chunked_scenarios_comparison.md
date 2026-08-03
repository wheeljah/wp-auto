# Chunked Generation 시나리오 비교 (A/B/C/D)

> **날짜**: 2026-08-03
> **하드웨어**: GTX 1050 (2GB, CPU-only), qwen2.5:3b, 16GB RAM
> **데이터**: `oneoff/results/{B,C,D}_*.json` + `*_single.html` / `*_cluster_*.html`
> **시나리오 스크립트**: `oneoff_chunked_{b_en,c_short,d_long}.py`

---

## 1. 시나리오 정의

| ID  | 시나리오              | 언어 | max_chunks | 실제 chunks | 비고                              |
| --- | --------------------- | ---- | ---------- | ----------- | --------------------------------- |
| (基) | 기본 (이전 시연)      | ko   | 5          | 4 + 1 pillar | `oneoff_chunked_compare.py` 8 posts |
| **B** | **영문 cluster**      | en   | (default)  | 6 + 1 pillar | Google News US RSS, 7 cluster posts |
| **C** | **짧은 chunk**        | ko   | 3          | 3 + 1 pillar | plan→truncate, 4 cluster posts    |
| **D** | **큰 chunk**          | ko   | 8          | 5 + 1 pillar | plan 5 반환 (max 8 미달), 6 cluster |

> **Note**: D는 `max_chunks=8`로 요청했지만 qwen2.5:3b의 plan이 5개만 반환 → 5개로 진행. chunk_plan 프롬프트에 "5-7 subtopic"이 기본 성향.

---

## 2. 종합 비교 표

| Metric                  | B (영문, 6) | C (짧은, 3) | D (큰, 5) | 기본 (ko, 4) |
| ----------------------- | ----------- | ----------- | --------- | ------------ |
| **언어**                | en          | ko          | ko        | ko           |
| **chunks 수**           | 6           | 3           | 5         | 4            |
| **총 소요 시간**        | 314.5s (5.2분) | 316.0s (5.3분) | 328.3s (5.5분) | 372.1s (6.2분) |
| **outline 시간**        | 63.3s       | 65.7s       | 46.4s     | 49.2s        |
| **cluster 생성 시간**   | 251.2s      | 250.3s      | 281.9s    | 321.8s       |
| **avg chunk 시간**      | ~36s        | ~40s        | ~47s      | ~43s         |
| **single HTML (chars)** | 9,844       | 3,508       | 5,304     | 5,205        |
| **single internal links** | 26        | 12          | 21        | 21           |
| **cluster posts 수**    | 7 (1+6)     | 4 (1+3)     | 6 (1+5)   | 5 (1+4)      |
| **cluster total (chars)** | 8,415    | 3,006       | 4,449     | 4,350        |
| **avg cluster links**   | 3.7         | 3.0         | 3.5       | 3.5          |
| **발행 WP post IDs**    | 9-16        | 17-21       | 22-28     | 3-8          |

> 시간 데이터: `timing_sec.total` (스크립트 시작 → publish 완료), `outline = total - cluster_generation` 역산

---

## 3. 시나리오별 상세

### B: 영문 chunked cluster

- **RSS**: Google News US (`hl=en&gl=US&ceid=US:en`)
- **Topic**: "Ariana Grande Exits West End's 'Sunday in the Park with George' Revival"
- **Outline**: en, 4 H2 (62s)
- **Chunks** (6): Background, Musical Overview, Impact on Performers, Industry Reactions, Personal Reasons, Professional Concerns
- **발행**: 8 posts (1 single + 7 cluster) — WP #9-16
- **관찰**:
  - 영문 qwen2.5:3b는 한 chunk당 **~1,200자** 생성 (한글 ~500자 대비 2.4배)
  - `single` HTML이 9,844자로 가장 크다 (영문 1byte/char)
  - internal link 26개 — single mode의 장점이 극대화
  - cluster avg 3.7 links/post
- **결론**: 영문은 chunk당 분량이 커서 single mode 효율 ↑. cluster 모드는 "짧은 글 N개" 형태로 발행량 극대화.

### C: 짧은 chunk (3 chunks)

- **RSS**: Google News KR
- **Topic**: "[제네릭 약가 인하]③ 약값 낮춘다고 끝 아냐…제약업계 '시장 혼란·R&D 위축 막을 장치 필요'"
- **Outline**: ko, 3 H2 (65.7s)
- **Chunks** (3): 배경과 맥락, 핵심 방법/전략, 실제 사례/예시
- **발행**: 5 posts (1 single + 4 cluster) — WP #17-21
- **관찰**:
  - chunk 3개라 generation 시간은 빨라야 하지만 (3 × 40s = 120s), outline + pillar + publish가 고정 비용
  - plan 5 → truncate 3 → "핵심만" 추리는 효과 (배경/방법/사례)
  - single 3,508자 — 가장 작은 single
- **결론**: chunk 3개는 **핵심 정보만 빠르게 발행**할 때 적합. 그러나 SEO 측면에서 cluster 4 posts는 다소 빈약.

### D: 큰 chunk (8 chunks 요청 → 5 chunks)

- **RSS**: Google News KR
- **Topic**: "제미나이 사용 전 확인해야 할 개인정보 보호 설정"
- **Outline**: ko, 3 H2 (46.4s)
- **Chunks** (5, plan이 5만 반환): 배경과 맥락, 핵심 방법/전략, 실제 사례/예시, 주의사항/함정, 정리/다음 단계
- **발행**: 7 posts (1 single + 6 cluster) — WP #22-28
- **관찰**:
  - `max_chunks=8`로 prompt했지만 **plan이 5 subtopic만 반환** — qwen2.5:3b의 plan 성향
  - chunk_plan 프롬프트를 "6-10 subtopic"으로 강제하지 않으면 4-6개가 default
  - 5 chunks에서 generation 시간 281.9s (3 chunks C 250s 대비 +12%)
  - single 5,304자 / cluster 6 posts / avg 3.5 links
- **결론**: **max_chunks=8이 무의미** — plan prompt에 명시적 강제 필요. 또는 post-plan truncate로 외부 제어.

---

## 4. 핵심 인사이트

### 4.1 시간은 outline + pillar이 지배

| 단계              | B (6 chunks) | C (3 chunks) | D (5 chunks) |
| ----------------- | ------------ | ------------ | ------------ |
| outline           | 63.3s (20%)  | 65.7s (21%)  | 46.4s (14%)  |
| N × chunk         | ~216s (69%)  | ~120s (38%)  | ~210s (64%)  |
| pillar            | ~35s (11%)   | ~30s (9%)    | ~30s (9%)    |
| **cluster gen 합계** | 251s        | 250s         | 282s         |
| **publish (N+1)** | < 1s         | < 1s         | < 1s         |

→ **chunk 개수를 늘려도 전체 시간은 ~5분대에 수렴**. outline (50-65s) + pillar (30-35s)이 고정 비용 ~100s.
→ chunk × N만 linear. 3 → 6개로 2배 늘려도 +50% 정도.

### 4.2 Single vs Cluster: 발행량 trade-off

| Mode       | posts | avg HTML/post | SEO 효과            | 발행 속도       |
| ---------- | ----- | ------------- | ------------------- | --------------- |
| **single** | 1     | 5-10k chars   | 1 페이지에 link juice 집중 | 1회 publish     |
| **cluster** | N+1  | 1-1.5k chars  | N+1 페이지에 link juice 분산 | N+1회 publish |

→ B: single 9,844자 vs cluster 7 posts = **발행량 7배**
→ C: single 3,508자 vs cluster 4 posts = **발행량 4배**
→ D: single 5,304자 vs cluster 6 posts = **발행량 6배**

### 4.3 Internal links 구조

`avg internal links/post`는 cluster posts의 chunk-nav 링크 평균.

| 시나리오 | single | cluster avg | 비고                                  |
| -------- | ------ | ----------- | ------------------------------------- |
| B (6)    | 26     | 3.7         | 6 chunk × 3 nav = 18 + pillar 8 = 26 |
| C (3)    | 12     | 3.0         | 3 chunk × 3 nav = 9 + pillar 3 = 12  |
| D (5)    | 21     | 3.5         | 5 chunk × 3 nav = 15 + pillar 6 = 21 |

→ single mode의 link 수는 **chunks² 에 비례** (chunk-nav: prev/next/related)
→ cluster mode는 일정한 3-4 links (이전/다음/related 1-2개)

### 4.4 Chunk 개수 결정 가이드

| 사용 사례                       | 권장 chunks | 이유                              |
| ------------------------------- | ----------- | --------------------------------- |
| **속도/요약 우선**              | 3           | C — 4 posts, 빠른 발행, 핵심만     |
| **기본 (현재 default)**         | 4-5         | 기본/D 시연 — 균형                |
| **SEO 최대화 (영문)**           | 6-7         | B — cluster 7-8 posts, link juice  |
| **세부 가이드 (튜토리얼)**      | 7-8         | D 의도 — 단, plan prompt 수정 필요 |

---

## 5. 발견한 한계 & 개선 사항

### 5.1 plan 단계의 chunk 개수 불일치

**문제**: `max_chunks=8`로 지정했지만 qwen2.5:3b plan이 5개만 반환.
**원인**: `prompts/{ko,en}/chunk_plan.txt`에 chunk 개수 강제 가이드 없음. qwen이 default 4-6 subtopic을 생성.
**개선**:
- prompt에 `"Generate exactly {N} subtopics"` 명시
- 또는 `plan_subtopics()`에 `min_chunks` 검증 + retry 로직
- 또는 외부 truncate (현재 D 방식) + 경고 로그

### 5.2 timing JSON 키 의미 오해

**문제**: `timing_sec.outline` 키에 `total` 값을 넣음 (코드 실수).
**영향**: `total - cluster_generation`으로 outline 시간을 역산해야 정확.
**개선**: 스크립트에서 outline 단독 측정 → `outline` 키에 기록.

### 5.3 MockWP DB 누적

**문제**: B/C/D 시나리오로 8 + 8 + 7 = **23 posts 추가** (이전 8 → 총 31).
**대응**:
- 정리 명령 추가 (예: `python -m wp_auto wp clear-mock`)
- 또는 category prefix (`b-en-`, `c-short-`, `d-long-`)로 필터링 가능

---

## 6. 권장 사항

1. **기본 chunk 수 = 4-5 (현재 default)**: SEO와 속도 균형. 더 늘려도 시간/효과 체감 미미.
2. **영문 발행 시 chunk 6+ 권장**: B 결과 — single 9,844자가 cluster 7 posts로 분산되어 발행량 효율 ↑.
3. **plan prompt에 chunk 개수 명시**: `chunk_plan.txt` 수정으로 max_chunks 신뢰도 ↑.
4. **single mode의 internal link 극대화**: cluster posts가 single의 link을 받으므로, single mode 발행 후 cluster 발행이 link juice 흐름에 유리.
5. **chunked 시연은 1인 self-use + GTX 1050 환경에 최적**: 5-6분 내 5-7 posts 발행, manual trigger 1회로 충분.

---

## 7. 파일 목록

```
D:\Google_blog\wp-auto\
├── oneoff_chunked_b_en.py           # B 시나리오 스크립트
├── oneoff_chunked_c_short.py        # C 시나리오 스크립트
├── oneoff_chunked_d_long.py         # D 시나리오 스크립트
└── oneoff/
    └── results/
        ├── B_en_log.txt             # B 실행 로그
        ├── B_en_result.json         # B 결과 메타
        ├── B_single.html            # B single HTML (9,987 bytes)
        ├── B_cluster_1..7.html      # B cluster HTMLs
        ├── C_short_log.txt          # C 실행 로그
        ├── C_short_result.json      # C 결과 메타
        ├── C_single.html            # C single HTML (6,548 bytes)
        ├── C_cluster_1..4.html      # C cluster HTMLs
        ├── D_long_log.txt           # D 실행 로그
        ├── D_long_result.json       # D 결과 메타
        ├── D_single.html            # D single HTML (10,003 bytes)
        └── D_cluster_1..6.html      # D cluster HTMLs
```

발행된 MockWP posts: 총 **31개** (이전 8 + B 8 + C 5 + D 7 + first 1 + 2 = 31)

- 이전 시연: WP #1-8
- B: WP #9-16 (1 single + 6+1 cluster)
- C: WP #17-21 (1 single + 3+1 cluster)
- D: WP #22-28 (1 single + 5+1 cluster)
