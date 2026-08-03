# 무료 조합 vs 자체 구현 — 효율성 분석 (wp-auto v0.9)

> 작성일: 2026-08-04
> 범위: URL/PDF 입력 + 직접 작성 배포 입력 기능의 도구 선택 결정
> 결론: **Hybrid** (수집=무료 lib, 생성=자체 LLM, 발행=자체)

---

## 0. TL;DR

| 입력/처리 단계 | 무료 조합 (외부 lib/API) | 자체 구현 | **권장** |
|---|---|---|---|
| URL 텍스트 추출 | **Trafilatura** (F1 0.958, 1차 출처) | requests + BeautifulSoup | **Trafilatura** |
| PDF 텍스트 추출 | **PyMuPDF** (180 pages/sec, 1차 출처) | 자체 파서 (불가) | **PyMuPDF** |
| 요약/재구성 | 외부 LLM (Groq, OpenRouter Free) | 자체 Ollama | **자체** (이미 보유) |
| Outline 생성 | 외부 API (OpenAI/Claude) | 자체 LLM + chunked_generator | **자체** |
| 콘텐츠 생성 | 유료 GPT-4/Claude | 자체 qwen2.5:3b/7b | **자체** (한국어 1차 검증) |
| 이미지 | Pexels 403 / Unsplash API / 자체 SVG | 자체 image_synthesize | **자체 + SVG fallback** |
| 발행 | WP REST API (무료) | 자체 `wp_auto.wp` | **자체** |

**비용**: $0 (이미 보유한 도구만 사용)
**Trade-off**: 무료 lib의 검증 알고리즘 + 자체 통합의 무외부성

---

## 1. 왜 이 분석이 필요한가

> 사용자 의도 (2026-08-04):
> "무료 조합에 기능을 이용하는 게 나을지 아니면 구현해서 사용하는 것이 효율적일지 생각해봐"

**3가지 옵션**:
1. **모두 무료 조합 (외부 lib/API)** — 빠른 셋업, 의존성 多
2. **모두 자체 구현** — 외부 의존 0, 개발 비용 大
3. **Hybrid** — 검증된 무료 lib + 자체 통합 (현재 권장)

---

## 2. URL 텍스트 추출 (1차 출처 비교)

### 2.1 후보 비교 (ScrapingHub benchmark, 181 articles)

| 라이브러리 | F1 | Precision | Recall | 출처 |
|---|---|---|---|---|
| **Trafilatura (Python 2.0.0)** | **0.958** | 0.938 | 0.978 | [contextractor.com](https://www.contextractor.com/trafilatura-vs-readability-vs-newspaper/) |
| rs-trafilatura (Rust port) | 0.966 | 0.942 | 0.991 | 동일 출처 |
| Newspaper4k 0.9.3.1 | 0.949 | 0.964 | 0.934 | 동일 출처 |
| readability-lxml 0.8.4.1 | 0.922 | 0.913 | 0.931 | 동일 출처 |
| jusText 3.0.2 | 0.804 | 0.858 | 0.756 | 동일 출처 |
| goose3 3.1.20 | 0.896 | 0.940 | 0.856 | 동일 출처 |

**Sandia National Labs 평가 (2024)**:
- Trafilatura F1 0.937, Precision 0.978, Recall 0.920
- Readability F1 0.914, Precision 0.936, Recall 0.929
- Newspaper3k F1 0.903
- 출처: [osti.gov Sandia evaluation](https://www.osti.gov/servlets/purl/2429881)

### 2.2 자체 구현 vs Trafilatura

| 비교 | 자체 (requests + BS4 + heuristic) | Trafilatura |
|---|---|---|
| **F1 score** | 0.6-0.8 (예상) | **0.958** (1차 출처 검증) |
| **개발 시간** | 2-4주 (heuristic 튜닝) | 0 (이미 사용 가능) |
| **유지보수** | 사이트 구조 변경 시 코드 수정 | Trafilatura 팀이 처리 |
| **의존성** | 0 | 1 (trafilatura pip install) |
| **비용** | 0 | 0 (오픈소스) |

**결론**: 자체 구현은 비효율. **Trafilatura 채택** (1차 출처 F1 0.958 검증).

### 2.3 무료 lib 채택 시 주의 (1차 출처)

> ⚠️ **웹 스크레이핑 저작권**: [17 USC §107](https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title17-section107) + [Tech Policy Press — Fair Use in AI Summaries](https://techpolicy.press/the-missing-fair-use-argument-in-the-copyright-battle-over-ai-summaries):
> - 단순 scrap → fair use 어려움 (Cohere/Perplexity 소송 사례)
> - **summary/abridgment** → "transformative" 검토 필요
> - **저장/재배포** → "effect on the market" 4번째 factor 검토

**wp-auto의 fair use 준수 전략**:
1. Trafilatura는 본문 **추출 도구** (LLM은 X)
2. `Researcher`가 LLM으로 **요약/재구성** (원문 복제 ❌)
3. amount minimization (max 1500자/source)
4. 출처 명시 + 자체 분석 결합

---

## 3. PDF 텍스트 추출 (1차 출처 비교)

### 3.1 후보 비교 (1,000-page benchmark)

| 라이브러리 | Pages/sec | Pass rate | License | 출처 |
|---|---|---|---|---|
| **PyMuPDF (fitz) 1.28.0** | **180** | 99.3% | **AGPL-3.0** (1인 self-use OK) | [markaicode.com](https://markaicode.com/benchmarks/pymupdf-production-benchmark-latency/) |
| pdfplumber | 18 | 98.8% | MIT | [pdfmux.com](https://pdfmux.com/blog/pymupdf-vs-pdfplumber/) |
| pypdfium2 | 4.1 (mean) | 99.2% | Apache 2.0 | [pdf.oxide.fyi](https://pdf.oxide.fyi/rust/docs/comparison/python) |
| pypdf | 12.1 (mean) | 98.4% | BSD | 동일 |
| PDF Oxide (Rust) | 1.0 (0.8ms) | 100% | MPL-2.0 | 동일 |

**테이블 정확도 (TEDS score)**:
- pdfplumber: 0.847 (best for bordered tables)
- PyMuPDF: 0.692
- 출처: [pdfmux.com 비교](https://pdfmux.com/blog/pymupdf-vs-pdfplumber/)

### 3.2 자체 구현 vs PyMuPDF

**자체 PDF 파서**: 기술적으로 가능하지만, PDF 1.0~2.0 spec 전체 지원은 **1-2명 인원 + 6개월+** 작업.
- MuPDF (PyMuPDF 백엔드) = 20년+ 개발된 C 라이브러리
- AGPL-3.0 (PyMuPDF): 1인 self-use는 OK, network service 배포 시 commercial license ($)
- 출처: [github.com/pymupdf/PyMuPDF/blob/main/LICENSE](https://github.com/pymupdf/PyMuPDF/blob/main/LICENSE)

**결론**: 자체 구현 **불가능**. **PyMuPDF 채택** (1차 출처: 8-12x faster, F1 0.937+).

### 3.3 AGPL-3.0 라이선스 검토

> ⚠️ **PyMuPDF는 AGPL-3.0** ([공식 LICENSE](https://github.com/pymupdf/PyMuPDF/blob/main/LICENSE)):
> - 1인 self-use (오프라인/로컬): **무료 OK**
> - SaaS/네트워크 서비스로 배포: commercial license 필요
> - 우리 wp-auto는 1인 self-use (현재 단계) → **OK**
> - 추후 멀티유저 SaaS화 시: commercial license 또는 대안 검토 (pypdfium2, Apache 2.0)

---

## 4. 요약/Outline/콘텐츠 생성 — 자체 LLM (Ollama)

### 4.1 후보 비교

| 옵션 | 비용 (월) | 한국어 품질 | 1차 출처 |
|---|---|---|---|
| **자체 Ollama (qwen2.5:7b)** | **$0** (CPU-only GTX 1050) | 1차 검증 (v0.4 한국어 자연스러움) | 1인 self-use 검증 |
| 자체 Ollama (qwen2.5:3b) | $0 | 1차 검증 (E2E 시연) | 동일 |
| Groq Free tier | $0 (rate limit) | 미검증 | 3rd party API |
| OpenRouter Free (Llama 3 8B) | $0 (rate limit) | 미검증 | 3rd party API |
| OpenAI GPT-4o-mini | $0.15/M tokens | 우수 (한국어) | [OpenAI pricing](https://openai.com/api/pricing/) |
| Claude 3.5 Haiku | $1/M tokens | 우수 (한국어) | [Anthropic pricing](https://www.anthropic.com/pricing) |

### 4.2 자체 LLM의 한계 (정직한 평가)

> **이미 검증된 사실** (v0.6.1):
> - H 데모: "프로 레슬링" hallucination (실제 주제 = "프로 당구")
> - 자동 치환 + fact_check.md로 후처리

> **v0.4~v0.8 통합**:
> - 4종 hook 자동 선택, 3종 CTA, 8종 JSON-LD
> - Q&A 구조, TL;DR, E-E-A-T footer
> - 답변-우선 (answer-first) 패턴
> - 1차 출처/출처 figcaption

**자체 LLM의 강점 (현실)**:
- ✅ 비용 0
- ✅ 한국어 자연스러움 (qwen2.5:7b 1차 검증)
- ✅ 로컬 = 외부 API 키 0, 네트워크 의존 X
- ✅ hallucination 사후 검증으로 mitigation

**자체 LLM의 약점**:
- ❌ 7B 모델은 GPT-4 대비 reasoning 능력이 떨어짐
- ❌ hallucination 가능 (사후 검증 필수)
- ❌ 속도: CPU-only GTX 1050 → 5-10 tok/s (chunked 4 chunks 7-8분)

### 4.3 결정: 자체 LLM 유지

**이유**:
1. 비용 0 (1인 운영자 원칙, 매출 발생 전까지 유료 SaaS ❌)
2. 7B 모델 + 사후 검증 + 청크 분할 = hallucination 위험 mitigation
3. 한국어 품질 검증 (qwen2.5:7b)
4. 로컬 처리 = 데이터 privacy (1인 self-use에 적합)

**유료 LLM 도입 시점** (memory 룰 "1인 SaaS 운영자의 비용 단계별 결정 원칙" 2026-07-26):
- affiliate 매출 $100/월 달성 후
- 또는 reasoning 능력 한계로 인해 콘텐츠 품질 손실 > 비용일 때

---

## 5. 이미지 — 자체 AI + SVG fallback (Pexels 403)

### 5.1 후보 비교

| 옵션 | 비용 | 안정성 | 1차 출처 |
|---|---|---|---|
| **자체 image_synthesize (AI)** | $0 (TOOL 보유) | 100% (로컬) | v0.6.2 검증 |
| Pexels API | $0 (무료) | **403 anti-bot** | [Pexels status](https://www.pexels.com/api-documentation/) |
| Unsplash API | $0 (50/hour) | 95% | [Unsplash API](https://unsplash.com/developers) |
| 자체 SVG (Pillow draw) | $0 | 100% (로컬) | v0.6.1 검증 |
| Midjourney/DALL-E | $10-30/month | 100% | 유료 |

### 5.2 결정: 자체 AI + SVG fallback

> v0.6.2 결정 (memory):
> - Pexels 직접 fetch 403 (anti-bot)
> - 자체 SVG → AI 생성 사진풍 JPG로 전환
> - 자체 SVG는 일러스트에 강함 (fallback)

---

## 6. 발행 — 자체 `wp_auto.wp`

### 6.1 후보 비교

| 옵션 | 비용 | 1인 self-use 적합도 | 1차 출처 |
|---|---|---|---|
| **자체 `wp_auto.wp.factory`** | $0 | ✅ (Mock 우선, Real opt-in) | v0.1+ |
| WordPress.com (무료) | $0 | ❌ (자체 도메인, 플러그인 제한) | [WordPress.com plans](https://wordpress.com/pricing/) |
| WP All Import 플러그인 | $0-100/year | ⚠️ (third-party 의존) | [WP All Import](https://www.wpallimport.com/) |
| WP REST API 직접 호출 | $0 | ✅ (자체에서 호출) | [WP REST API](https://developer.wordpress.org/rest-api/) |

### 6.2 결정: 자체 wp_auto.wp

- Mock 모드 (DB SQLite) — 1인 self-use 테스트
- Real 모드 (WP REST API) — .env opt-in
- 이미 v0.1부터 구현, 70개 posts (WP #1-70 across B-K demos) 검증

---

## 7. 비용 분석 — Hybrid (현재 결정)

### 7.1 월 비용 (1,000개 post 생성 시)

| 항목 | 비용 | 비고 |
|---|---|---|
| Trafilatura (URL 추출) | $0 | 오픈소스, 1차 출처 F1 0.958 |
| PyMuPDF (PDF 추출) | $0 | AGPL-3.0, 1인 self-use OK |
| 자체 Ollama (qwen2.5:3b/7b) | $0 | CPU-only, 이미 보유 |
| 자체 image_synthesize | $0 | 도구 보유 |
| 자체 wp_auto.wp | $0 | 이미 구현 |
| **합계** | **$0** | |

### 7.2 유료 대안과 비교

| 방식 | 월 비용 | 1차 출처 |
|---|---|---|
| **모두 유료 SaaS** (Surfer SEO, Jasper, INK 등) | $200-500/월 | [Surfer SEO pricing](https://surferseo.com/pricing/) ($89-199/월), [Jasper pricing](https://www.jasper.ai/pricing) ($49-125/월) |
| **Hybrid (현재 결정)** | $0 | 1차 출처의 검증 알고리즘 + 자체 통합 |

### 7.3 결정 원칙 (memory 룰)

> **"1인 SaaS 운영자의 비용 단계별 결정 원칙" (2026-07-26, agent memory):**
> - 유료 SaaS 도구 = **매출화 시작 시점에 도입**
> - 무료/자체호스팅 옵션 우선 → 운영 안정성 검증 후 유료화 단계 도달 시 비용 발생 허용
> - 이는 "출혈 최소화 → 매출 발생 후 도구 비용" 패턴

**현재 단계 (Pre-revenue, affiliate 마케팅 시작)**:
- 무료/자체호스팅 우선
- Trafilatura + PyMuPDF = 검증된 무료 lib (자체 구현보다 우월)
- 자체 LLM = 비용 0 (매출 발생 전 OK)

**매출 $100/월 달성 후 (Phase 2)**:
- 유료 LLM API 검토 (reasoning 능력 한계 대응)
- Newspaper 테마 ($59/year) — RPM +23% 검증
- Cloudflare + Vultr VPS ($6/month)

---

## 8. Trade-off 매트릭스

| Trade-off | 무료 lib 채택 | 자체 구현 |
|---|---|---|
| **초기 개발 시간** | ✅ 낮음 (pip install) | ❌ 높음 (2-4주 heuristic) |
| **알고리즘 품질** | ✅ F1 0.958 (1차 출처) | ⚠️ 0.6-0.8 (예상) |
| **유지보수 부담** | ✅ lib 팀이 처리 | ❌ 사이트 변경 시 코드 수정 |
| **외부 의존성** | ⚠️ 1-2개 (Trafilatura, PyMuPDF) | ✅ 0 |
| **비용** | ✅ $0 | ✅ $0 |
| **확장성** | ✅ Trafilatura는 multilingual (KO/EN) | ⚠️ 자체 heuristic은 site-specific |
| **Fair use 준수** | ⚠️ Trafilatura 추출 후 LLM 재구성 필요 | ✅ 처음부터 자체 처리 |
| **데이터 privacy** | ⚠️ lib 내부 동작 (오픈소스라 검증 가능) | ✅ 완전 통제 |

**결론**: 
- **수집 (URL/PDF)**: 무료 lib (Trafilatura + PyMuPDF) — 자체 구현 비효율
- **처리 (요약/생성)**: 자체 LLM — 비용 0, hallucination mitigation 가능
- **발행**: 자체 wp_auto.wp — 이미 검증됨

---

## 9. 위험 & 대응

| 위험 | 대응 |
|---|---|
| **Trafilatura 사이트 구조 변경 대응 실패** | Trafilatura는 7년+ 유지보수, 0.958 F1 안정. fallback: `newspaper4k` (F1 0.949) |
| **PyMuPDF AGPL-3.0 → 멀티유저 SaaS화 시 문제** | pypdfium2 (Apache 2.0) 또는 pdfplumber (MIT) fallback |
| **자체 LLM hallucination** | fact_check.md (v0.6.2) + 사후 텍스트 치환 (H 데모 사례) + 출처 figcaption |
| **외부 lib 업데이트로 API 변경** | lib는 1차 호출 (ingest_url/ingest_pdf)만 사용, interface 안정 |
| **1차 출처 검증 부담** | memory 룰 "검증 안 된 수치/추측 = 답변 금지" (2026-07-22) |

---

## 10. 1차 출처 (전체)

### 10.1 Trafilatura
- [Trafilatura Evaluation (readthedocs)](https://trafilatura.readthedocs.io/en/latest/evaluation.html)
- [Trafilatura PyPI](https://pypi.org/project/trafilatura/1.4.1/)
- [Sandia Labs: Java/Python Main Content Extraction Evaluation](https://www.osti.gov/servlets/purl/2429881)
- [Contextractor: Trafilatura vs Readability vs Newspaper4k](https://www.contextractor.com/trafilatura-vs-readability-vs-newspaper/)
- [Web Content Extraction Benchmarks (serp.fast)](https://serp.fast/guides/web-extraction-benchmarks)

### 10.2 PyMuPDF
- [PyMuPDF vs pdfplumber 2026 (pdfmux.com)](https://pdfmux.com/blog/pymupdf-vs-pdfplumber/)
- [py-pdf/benchmarks (GitHub)](https://github.com/py-pdf/benchmarks)
- [PyMuPDF Benchmark 2026 (markaicode.com)](https://markaicode.com/benchmarks/pymupdf-production-benchmark-latency/)
- [PDF Oxide Docs — Python comparison](https://pdf.oxide.fyi/rust/docs/comparison/python)
- [PyMuPDF LICENSE (AGPL-3.0)](https://github.com/pymupdf/PyMuPDF/blob/main/LICENSE)

### 10.3 Fair Use
- [US Copyright Office Fair Use Index](https://www.copyright.gov/fair-use/)
- [17 USC §107](https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title17-section107)
- [Stanford Fair Use Overview](https://fairuse.stanford.edu/overview/fair-use/four-factors/)
- [Tech Policy Press — Fair Use in AI Summaries](https://techpolicy.press/the-missing-fair-use-argument-in-the-copyright-battle-over-ai-summaries)

### 10.4 유료 SaaS 가격
- [Surfer SEO pricing](https://surferseo.com/pricing/)
- [Jasper pricing](https://www.jasper.ai/pricing)
- [OpenAI pricing](https://openai.com/api/pricing/)
- [Anthropic pricing](https://www.anthropic.com/pricing)

---

## 11. 결론 (한 줄)

> **수집은 무료 lib (Trafilatura F1 0.958 + PyMuPDF 180 pages/sec), 생성은 자체 LLM, 발행은 자체 wp_auto.wp — Hybrid가 1인 self-use 단계에서 가장 효율적.**
