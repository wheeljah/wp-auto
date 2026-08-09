# wp-auto CHANGELOG

> **Dopaminews.com (multi-category news aggregator) — 1인 self-use WordPress 자동화 도구.**
> GitHub: https://github.com/wheeljah/wp-auto
> Site: https://dopaminews.com (Cloudflare + InfinityFree)
> License: 프로젝트 = Apache 2.0 (코드), 콘텐츠 = dopaminews.com (모든 권리)

---

## 🎯 한 줄 요약

`NotebookLM으로 source-grounded 한국어 draft → wp-auto로 자동 image fetch + WP 발행` 워크플로우의 도구.
또는 직접 Qwen 2.5 7B로 generate + Pexels/Wikimedia/NASA image + WP 발행.

---

## 📊 현재 상태 (v0.10.1 + launchers + NotebookLM)

| 항목 | 상태 | 출처 |
|---|---|---|
| **테스트** | **377 passed** (1 warning) | `pytest tests/unit` |
| **모델** | Qwen 2.5 7B (Apache 2.0, 상업용 OK) | [HuggingFace LICENSE](https://huggingface.co/Qwen/Qwen2.5-7B/blob/main/LICENSE) |
| **Image source** | Pexels (KEY ✅) + Wikimedia + NASA | [Pexels](https://www.pexels.com/license/) + [Wikimedia](https://commons.wikimedia.org/wiki/Commons:Licensing) + [NASA](https://www.nasa.gov/nasa-brand-center/images-and-media/) |
| **WP 발행** | Mock (SQLite) 또는 Real (InfinityFree REST API 차단 → 수동) | `wp_auto/cli/publish.py` + `publish_md.py` |
| **NotebookLM** | 워크플로우 가이드 + inbox/ 통합 | [Google blog 2026-07](https://blog.google/innovation-and-ai/products/notebooklm/better-research-notebooklm/) |
| **Hero image** | `<figure class="article-hero">` + dark gradient | [MDN figure](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/figure) |

---

## 🆕 v0.10.x (2026-08-09)

### v0.10.1 — hero image + background style
**commit `01f4c3e`**
- `ImageEmbedder.embed_hero()` — 첫 H1 직후 `<figure class="article-hero">` + dark gradient + attribution
- `ImageEmbedder.embed_background_style()` — CSS background-image 방식 (alternative)
- `ImagePipeline.run()` 에 `hero_image=True` + `hero_height=400` 옵션
- `routes.py /api/generate` 에 `hero_image` + `hero_height` Form fields
- +7 tests → **377 total**
- 1차 출처: [MDN HTML figure](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/figure)

### v0.10.0 — image pipeline
**commit `9e2d410`**
- `wp_auto/image/` 모듈 5개 추가 (~1100 lines):
  - `models.py` — ImageResult + LicenseKind
  - `source_resolver.py` — Pexels + Wikimedia + NASA 통합
  - `generator.py` — PIL infographic (16:9/9:16/1:1)
  - `embedder.py` — HTML 자동 `<figure>` 삽입 + WebP 변환
  - `pipeline.py` — orchestrator + license sidecar JSON
- `routes.py /api/generate` — `enable_images=true` 옵션
- `.gitignore` — `pexels.txt`, `work/`, `oneoff/results/` 차단
- `start-ollama.bat`, `start-wp-auto.bat` 작성 (cp949 cmd safe)
- +16 tests → **370 total**
- 1차 출처: [Pexels API docs](https://www.pexels.com/api/documentation/), [Wikimedia Commons Licensing](https://commons.wikimedia.org/wiki/Commons:Licensing), [Wikimedia User-Agent policy](https://meta.wikimedia.org/wiki/User-Agent_policy)

### v0.10.x — NotebookLM workflow + inbox
**commit `cb588ac`**
- `docs/notebooklm_workflow.md` — 10-step 가이드
- `inbox/` — NotebookLM export .md 저장소 (로컬 only)
- `inbox/README.md` + `inbox/news_template.md` (frontmatter 템플릿)
- 1차 출처: [Google blog 2026-07](https://blog.google/innovation-and-ai/products/notebooklm/better-research-notebooklm/), [2025-08 Blog Post format](https://blog.google/innovation-and-ai/models-and-research/google-labs/notebooklm-student-features/), [Workspace Updates 2026-03](https://workspaceupdates.googleblog.com/2026/03/new-ways-to-customize-and-interact-with-your-content-in-NotebookLM.html), [Google blog 한국어](https://blog.google/intl/ko-kr/company-news/technology/notebooklm-audio-overviews-50-languages-kr/)

### v0.10.x — Server launchers (Desktop shortcut)
**commit `987958d`**
- `start-both.bat` — 한 번 클릭으로 Ollama + wp-auto UI 2개 서버 동시 실행
- `make-shortcuts.ps1` — Desktop에 2개 `.lnk` (Ollama Server, wp-auto UI)
- `make-shortcuts.bat` — PowerShell Bypass wrapper

### v0.10.x — Path rename (진행 중)
**commit `c7a5c0d`**
- `.bat/.ps1` 경로 `wp-auto` → `wp_auto` update (commit)
- **디렉토리 rename은 OS file lock으로 막힘** — 시스템 재시작 후 `Rename-Item D:\Google_blog\wp-auto D:\Google_blog\wp_auto` 필요

---

## 📜 v0.1 ~ v0.9 (이전 세션)

### v0.9 — URL/PDF 입력 + 직접 작성 markdown
**commit `b3a667b`**
- News article URL / PDF → 한국어 초안 (NotebookLM style)
- 직접 작성 markdown → `publish-md` CLI
- 무료 vs 자체 구현 분석

### v0.8 — JSON-LD schema + Amazon affiliate + FTC disclosure
**commit `c63c8d8`**
- JSON-LD 자동 생성 (Schema.org)
- Amazon affiliate 자동 삽입
- FTC disclosure (영문, 한국어)

### v0.7 — 제휴마케팅 워드프레스 셀프호스팅 가이드
**commit `a1f9bd4`**
- Amazon Associates / Awin / CJ Affiliate 가이드
- 180일 내 $100 commission 목표

### v0.6.x — chunked pillar-cluster + bilingual
- `c7a5c0d` v0.6.3 — 주제 맞춤 subtopic + 실제 요약 + 자연스러운 마무리
- `6204a86` v0.6.2 — 랜덤 뉴스 end-to-end 시연
- `3a1e482` v0.6.2 — 이미지 무료 소스 + 구조/문장 정리
- `050d7cc` v0.6.1 — H 당구 hallucination 수정 + F/G 기사 이미지
- `0c7c1a8` v0.6.0 — link verification + structure optimization

### v0.5 — HookGenerator + CTAInjector
**commit `3357281` + `fb9fa25`**
- 트렌드 + deep_dive style
- Chunked pillar-cluster + bilingual
- `clean-mock` CLI

### v0.1~v0.4 (Phase 1-4)
- 기본 content generation pipeline
- Mock / Real WP client
- FastAPI Web UI
- 한글 / 영문 bilingual
- HTML parser + content score
- E-E-A-T / SEO 자동화

---

## 🏗️ 아키텍처

```
┌──────────────────────────────────────────────────────┐
│                  wp-auto pipeline                    │
├──────────────────────────────────────────────────────┤
│                                                      │
│  1) Draft     Ollama (qwen2.5:7b) + custom prompt    │
│     OR        NotebookLM export (inbox/*.md)         │
│            ↓                                         │
│  2) Image     Pexels API (KEY) / Wikimedia / NASA     │
│            Hero (1장) + Body (max 2장)               │
│            WebP 변환 + License sidecar JSON          │
│            ↓                                         │
│  3) Score     content_score 100점 (75+ PASS)         │
│            + H2 / FAQ / 출처 / 1차 경험 / 비교표     │
│            ↓                                         │
│  4) Publish   Mock (SQLite) 또는 Real WP (REST API)  │
│            InfinityFree = REST API 차단 → 수동       │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### 모듈 구조
```
wp-auto/
├── ai/
│   ├── content_generator.py    # Qwen 2.5 7B
│   ├── ollama_client.py         # Ollama API
│   ├── markdown_loader.py       # .md → HTML
│   ├── schema_generator.py      # JSON-LD
│   ├── affiliate_linker.py      # Amazon
│   └── source_ingestor.py       # URL/PDF → text
├── image/                       # v0.10.0+
│   ├── models.py                # ImageResult
│   ├── source_resolver.py       # Pexels + Wikimedia + NASA
│   ├── generator.py              # PIL infographic
│   ├── embedder.py              # <figure> + hero embed
│   └── pipeline.py              # orchestrator
├── cli/
│   ├── ui.py                    # FastAPI Web UI
│   ├── publish.py               # Real WP
│   ├── publish_md.py            # .md → WP
│   ├── ingest.py                # URL/PDF ingest
│   └── verify.py                # content score
├── core/
│   ├── content_score.py         # 100점 채점
│   ├── html_parser.py           # HTML 메트릭
│   └── seo_analyzer.py
├── optimize/
│   ├── image_optimizer.py       # WebP/AVIF
│   ├── cwv_measurer.py          # Core Web Vitals
│   └── lazy_loader.py
├── web/                          # FastAPI
│   ├── server.py
│   └── routes.py                # /api/generate
├── wp/                          # WP client
│   ├── client.py / factory.py
│   ├── mock_client.py           # SQLite
│   └── real_client.py           # REST API
├── integrations/
│   └── visitor_timezone.js
├── docs/                        # 가이드
│   ├── notebooklm_workflow.md
│   ├── affiliate_marketing_setup.md
│   ├── wp_admin_generatepress_setup.md
│   ├── wordpress_api_auto_publish.md
│   ├── monetization_blog_plan.md
│   └── ...
├── inbox/                       # NotebookLM export (로컬 only)
│   ├── README.md
│   └── news_template.md
├── assets/images/               # 다운로드 image (WebP)
├── out/                         # 생성 초안 (로컬)
├── data/wp_auto.db              # Mock WP DB
├── tests/unit/                  # 377 tests
└── start-both.bat / make-shortcuts.ps1/bat
```

---

## 🔄 워크플로우 3가지

### A. NotebookLM (source-grounded) — **추천**
1. News URL → NotebookLM source 추가
2. Studio → Reports → Blog Post (한국어) → Download .md
3. Nano Banana image generate → Download PNG
4. `inbox/<slug>.md` 저장 (frontmatter 보강)
5. Hero image → `assets/images/<slug>_hero.png`
6. `python -m wp_auto publish-md inbox/<slug>.md` → WP 발행

### B. Qwen 2.5 7B (현재 워크플로우)
1. UI: `http://127.0.0.1:8767/generate` 접속
2. Topic + keyword 입력
3. `enable_images=true` + `hero_image=true`
4. Submit → 자동 draft + image + WebP
5. WP 발행 (Mock DB 또는 수동)

### C. NotebookLM + wp-auto 하이브리드
- 1차 source-grounded: NotebookLM
- Image 다양성: Pexels/Wikimedia (wp-auto)
- WP 발행: publish-md 자동화

---

## ⚠️ 알려진 이슈

| # | 이슈 | 해결 |
|---|---|---|
| 1 | **PowerShell 5.1 + 한글 UTF-8 큰 본문 = Latin-1 mojibake** | Python httpx + `Path.write_text(encoding='utf-8')` 사용. PowerShell 7 (`pwsh`) 권장. |
| 2 | **Wikimedia API 403 Forbidden** | `User-Agent` 헤더 필수 (`wp-auto/1.0 (https://github.com/wheeljah/wp-auto; wheeljah@gmail.com) Python/3.14`) |
| 3 | **Qwen 2.5 7B raw 짧음 (1.6-4KB)** | 후처리 (E-E-A-T/FAQ/출처/비교표) 또는 `length=5000+` |
| 4 | **InfinityFree REST API 차단** | WP Admin에서 수동 publish (Real mode) 또는 Mock mode (로컬) |
| 5 | **OneDrive/D:\Google_blog\wp-auto OS file lock** (rename 막힘) | 시스템 재시작 후 `Rename-Item D:\Google_blog\wp-auto D:\Google_blog\wp_auto` |
| 6 | **Qwen 2.5 3B/72B = Research License (non-commercial)** | **Qwen 2.5 7B/14B/32B만 사용** (Apache 2.0) |

---

## 🛠️ 사용법 (다음 사이클)

### 1) Ollama + wp-auto UI 실행
```powershell
# 옵션 1: 단일 클릭
D:\Google_blog\wp-auto\start-both.bat

# 옵션 2: Desktop shortcut (1회 setup)
D:\Google_blog\wp-auto\make-shortcuts.bat
# → Desktop에 "Ollama Server (Google_blog).lnk" + "wp-auto UI (Google_blog).lnk" 생성
```

### 2) WP 발행 워크플로우
- **A. NotebookLM** → `inbox/<slug>.md` → `publish-md` → WP
- **B. UI** (`http://127.0.0.1:8767`) → Generate → Publish
- **C. CLI** (Python httpx 직접 호출)

### 3) WP 수동 publish (InfinityFree)
1. `https://dopaminews.com/wp-admin/edit.php` 접속
2. Draft → Publish 클릭
3. 시크릿 창에서 `https://dopaminews.com/<slug>` 🔒 확인

---

## 🎯 다음 사이클 (사용자 다음 단계)

1. **시스템 재시작** + `Rename-Item D:\Google_blog\wp-auto D:\Google_blog\wp_auto` (file lock 해제)
2. **PowerShell 2개 창 띄우기** (Ollama + UI) 또는 Desktop .lnk 더블클릭
3. **첫 글 발행** (NotebookLM or UI)
4. **5개 generate** (Science & Health, World & Politics, Climate & Environment, Culture & Media) — Tech & AI (v4) + Business & Finance (business_1)는 이미 생성됨
5. **GSC 등록** + Affiliate 마케팅 (CJ → Amazon → Awin)
6. **180일 내 $100 commission 목표**

---

## 📊 통계

- **Total commits**: 24+
- **Total tests**: 377 (354 baseline + 16 image + 7 hero)
- **Total .py files**: 40+
- **Total docs**: 9
- **Site**: https://dopaminews.com (live, HTTPS, Cloudflare Front)
- **Mock posts**: 108+ (v0.1~v0.10)
- **License**: Apache 2.0 (code) + dopaminews.com (content)

---

## 1차 출처 (Verified)

### Models
- [Qwen 2.5 7B LICENSE (Apache 2.0)](https://huggingface.co/Qwen/Qwen2.5-7B/blob/main/LICENSE) — 2026-08
- [Qwen2.5: A Party of Foundation Models](https://qwenlm.github.io/blog/qwen2.5/) — 2026-08

### Image sources
- [Pexels License](https://www.pexels.com/license/) — 2026-08
- [Pexels API documentation](https://www.pexels.com/api/documentation/) — 2026-08
- [Wikimedia Commons Licensing](https://commons.wikimedia.org/wiki/Commons:Licensing) — 2026-08
- [Wikimedia User-Agent policy](https://meta.wikimedia.org/wiki/User-Agent_policy) — 2026-08
- [NASA Brand Center: Images and Media](https://www.nasa.gov/nasa-brand-center/images-and-media/) — 2026-08

### NotebookLM
- [Google blog 2026-07: Better research with NotebookLM](https://blog.google/innovation-and-ai/products/notebooklm/better-research-notebooklm/)
- [Google blog 2025-08: NotebookLM student features](https://blog.google/innovation-and-ai/models-and-research/google-labs/notebooklm-student-features/)
- [Workspace Updates 2026-03](https://workspaceupdates.googleblog.com/2026/03/new-ways-to-customize-and-interact-with-your-content-in-NotebookLM.html)
- [Google blog 한국어: Audio Overview 50+ 언어](https://blog.google/intl/ko-kr/company-news/technology/notebooklm-audio-overviews-50-languages-kr/)

### HTML standards
- [MDN HTML figure](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/figure) — 2026-08

---

**최종 업데이트**: 2026-08-09 (commit `c7a5c0d` + 1차 출처 검증 기반)
