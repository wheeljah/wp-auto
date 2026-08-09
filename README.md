# WP-auto

> **Dopaminews.com (multi-category news aggregator) — 1인 self-use WordPress 자동화 도구**
>
> Source-grounded draft (NotebookLM or Qwen 2.5 7B) → 자동 image fetch (Pexels/Wikimedia/NASA) → WP 발행 (Mock or Real)

[![Tests](https://img.shields.io/badge/Tests-377%20passed-brightgreen.svg)](./tests/unit)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Qwen 2.5 7B (Apache 2.0)](https://img.shields.io/badge/Model-Qwen%202.5%207B-blue.svg)](https://huggingface.co/Qwen/Qwen2.5-7B)
[![Code License](https://img.shields.io/badge/Code-Apache%202.0-green.svg)](./LICENSE)
[![Site](https://img.shields.io/badge/Site-dopaminews.com-orange.svg)](https://dopaminews.com)

---

## 🎯 한 줄 요약

```
[News URL] → NotebookLM (Blog Post + Nano Banana image) → export .md
    → inbox/ 저장 → python -m wp_auto publish-md → WP 발행
```

또는:

```
[Topic + Keyword] → Qwen 2.5 7B (로컬 Ollama) → 자동 image fetch
    → WebP 변환 + 라이선스 자동 → WP 발행
```

---

## 📊 현재 상태 (v0.10.1 + launchers + NotebookLM workflow)

| 항목 | 값 | 출처 |
|---|---|---|
| **Tests** | **377 passed** | `pytest tests/unit` |
| **모델** | Qwen 2.5 7B (Apache 2.0, 상업용 OK) | [LICENSE](https://huggingface.co/Qwen/Qwen2.5-7B/blob/main/LICENSE) |
| **Image** | Pexels + Wikimedia + NASA (모두 상업용 무료) | [Pexels](https://www.pexels.com/license/) / [Wikimedia](https://commons.wikimedia.org/wiki/Commons:Licensing) / [NASA](https://www.nasa.gov/nasa-brand-center/images-and-media/) |
| **Site** | https://dopaminews.com (Cloudflare + InfinityFree) | Live |

자세한 변경 이력: [CHANGELOG.md](./CHANGELOG.md)
모든 1차 출처 검증: [CHANGELOG.md § 1차 출처](./CHANGELOG.md#1차-출처-verified)

---

## 🚀 사용법 (3가지 워크플로우)

### A. NotebookLM (source-grounded) — **추천**
[가이드](./docs/notebooklm_workflow.md)

1. [notebooklm.google.com](https://notebooklm.google.com) → New notebook
2. News article URL 추가 (출처)
3. Studio → **Reports → Blog Post** (한국어, 친근한 전문가 톤) → Download as Markdown
4. Studio → **Image (Nano Banana)** → 16:9 hero → Download PNG
5. `D:\Google_blog\wp-auto\inbox\<slug>.md` 저장 (frontmatter 보강)
6. Hero image → `assets/images/<slug>_hero.png`
7. `python -m wp_auto publish-md inbox/<slug>.md` → WP 발행

### B. Qwen 2.5 7B (현재 워크플로우)
1. `start-both.bat` 더블클릭 (또는 Desktop .lnk)
2. 브라우저 `http://127.0.0.1:8767/generate`
3. Topic + keyword 입력 → `enable_images=true` + `hero_image=true`
4. Submit → 자동 draft + image + WebP
5. WP 발행 (Mock 또는 수동)

### C. NotebookLM + wp-auto 하이브리드
- 글: NotebookLM (source-grounded)
- Image: Pexels/Wikimedia/NASA (다양성)
- WP 발행: publish-md 자동화

---

## 🛠️ 설치 / 실행

### 1) PowerShell 2개 창 띄우기
```powershell
# 창 1: Ollama
cd D:\Google_blog\wp-auto
.\start-ollama.bat

# 창 2: wp-auto UI
cd D:\Google_blog\wp-auto
.\start-wp-auto.bat
```

### 2) 또는 단일 통합 (권장)
```powershell
# 한 번 클릭으로 두 서버 동시
D:\Google_blog\wp-auto\start-both.bat
```

### 3) Desktop shortcut (1회 setup)
```powershell
# Desktop에 "Ollama Server (Google_blog).lnk" + "wp-auto UI (Google_blog).lnk" 생성
D:\Google_blog\wp-auto\make-shortcuts.bat
```

### 4) 브라우저
- **wp-auto UI**: `http://127.0.0.1:8767`
- **Ollama API**: `http://127.0.0.1:11434` (자동 연결)

---

## 📁 모듈 구조 (요약)

```
wp-auto/
├── ai/                 # Qwen 2.5 7B, JSON-LD, affiliate
├── image/              # v0.10.0+ Pexels + Wikimedia + NASA + PIL infographic
├── cli/                # ui, publish, publish_md, ingest, verify
├── core/               # content_score, html_parser, seo_analyzer
├── optimize/           # image_optimizer (WebP), cwv_measurer
├── web/                # FastAPI routes
├── wp/                 # Mock + Real WP client
├── docs/               # 가이드 (NotebookLM, Affiliate, WP Admin, ...)
├── inbox/              # NotebookLM export .md (로컬 only)
├── tests/unit/         # 377 tests
└── start-both.bat + make-shortcuts.ps1/bat
```

자세한 architecture: [CHANGELOG.md § 아키텍처](./CHANGELOG.md#%EC%95%84%ED%82%A4%ED%85%8D%EC%B2%98)

---

## 🔄 워크플로우 3가지 비교

| | NotebookLM (A) | Qwen 7B (B) | Hybrid (C) |
|---|---|---|---|
| **출처** | 필요 (URL/PDF) | 불필요 (LLM 지식) | A: NotebookLM + C: Hybrid |
| **Hallucination** | 낮음 (출처 citation 자동) | 보통 | A: 낮음 / C: 중간 |
| **한국어** | ✅ 50+ 언어 | ✅ 우수 | ✅ |
| **무료** | Free tier | ✅ 무제한 (로컬) | ✅ |
| **Image** | Nano Banana (Google) | Pexels/Wikimedia/NASA | A: Nano Banana + C: Pexels |
| **Export** | Markdown → publish-md | HTML → publish | Markdown → publish-md |
| **Hallucination 검증** | 출처 citation 자동 | 수동 (1차 출처 link) | A: 자동 / C: 수동 |

---

## 🛠️ 1차 출처 (Verified)

- **모델**: [Qwen 2.5 7B LICENSE (Apache 2.0)](https://huggingface.co/Qwen/Qwen2.5-7B/blob/main/LICENSE)
- **이미지**: [Pexels License](https://www.pexels.com/license/), [Wikimedia Commons Licensing](https://commons.wikimedia.org/wiki/Commons:Licensing), [NASA Brand Center](https://www.nasa.gov/nasa-brand-center/images-and-media/)
- **NotebookLM**: [Google blog 2026-07](https://blog.google/innovation-and-ai/products/notebooklm/better-research-notebooklm/)
- **HTML**: [MDN HTML figure](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/figure)

자세한 출처: [CHANGELOG.md § 1차 출처](./CHANGELOG.md#1차-출처-verified)

---

## ⚠️ 알려진 이슈

| # | 이슈 | 해결 |
|---|---|---|
| 1 | **PowerShell 5.1 + 한글 UTF-8 큰 본문 = Latin-1 mojibake** | Python httpx + `Path.write_text(encoding='utf-8')` 사용 |
| 2 | **Wikimedia API 403** | `User-Agent` 헤더 필수 (이미 source_resolver에 적용) |
| 3 | **InfinityFree REST API 차단** | WP Admin 수동 publish (Real mode) 또는 Mock mode |
| 4 | **`D:\Google_blog\wp-auto` OS file lock** (rename 막힘) | 시스템 재시작 후 `Rename-Item D:\Google_blog\wp-auto D:\Google_blog\wp_auto` |

자세한 내용: [CHANGELOG.md § 알려진 이슈](./CHANGELOG.md#%EC%95%8C%EB%A0%A4%EC%A7%84-%EC%9D%B4%EC%8A%88)

---

## 📜 라이선스

- **Code**: Apache 2.0 ([LICENSE](./LICENSE))
- **Content** (dopaminews.com 발행 글/이미지): dopaminews.com (모든 권리)
- **사용 모델**: Qwen 2.5 7B (Apache 2.0) — 상업용 무료
- **사용 image source**:
  - Pexels License ([pexels.com/license](https://www.pexels.com/license/))
  - Wikimedia Commons CC0/CC BY/CC BY-SA ([commons.wikimedia.org/wiki/Commons:Licensing](https://commons.wikimedia.org/wiki/Commons:Licensing))
  - NASA Public Domain (US 정부 저작물, attribution 권장)

---

## 🎯 다음 사이클 (사용자 다음 단계)

1. **시스템 재시작** + `Rename-Item D:\Google_blog\wp-auto D:\Google_blog\wp_auto` (file lock 해제)
2. **PowerShell 2개 창 띄우기** (또는 Desktop .lnk 더블클릭)
3. **첫 글 발행** — NotebookLM (A) 또는 Qwen (B)
4. **5개 generate** (Science & Health, World & Politics, Climate & Environment, Culture & Media) — Tech & AI (v4) + Business & Finance (business_1)는 이미 생성됨
5. **GSC 등록** + Affiliate 마케팅 (CJ → Amazon → Awin)
6. **180일 내 $100 commission 목표**

---

**최종 업데이트**: 2026-08-09
**버전**: v0.10.1 + launchers + NotebookLM workflow
**테스트**: 377 passed
**GitHub**: https://github.com/wheeljah/wp-auto
**Site**: https://dopaminews.com
