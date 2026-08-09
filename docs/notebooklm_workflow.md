# NotebookLM → wp-auto 워크플로우 가이드 (2026-08)

NotebookLM의 source-grounded RAG + Gemini 3.5 + Nano Banana image gen을 활용해서
dopaminews.com (multi-category news aggregator) 초안을 작성하는 워크플로우.

## 왜 NotebookLM인가

| 항목 | NotebookLM (소스 기반 RAG) | Qwen 2.5 7B (LLM 직접) |
|---|---|---|
| **Hallucination** | 낮음 (출처 citation 자동) | 보통 (검증 필요) |
| **출처 인용** | ✅ 자동 | ❌ 수동 |
| **한국어** | ✅ (50+ 언어, 한국어 native) | ✅ |
| **무료** | Free tier (Blog Post 무제한, Audio 3/day) | ✅ 무제한 (로컬) |
| **Image** | Nano Banana (Google image gen) | Pexels/Wikimedia/NASA |
| **Export** | Markdown / docx / PDF | HTML (WP 직접) |
| **출처** | 필요 (URL/PDF/Google Drive) | 불필요 |

**하이브리드 추천**: NotebookLM (1차 source-grounded 초안 + Nano Banana image) → wp-auto (자동 WP 발행 + Pexels image 보강).

---

## Step 1 — NotebookLM 접속

- **URL**: https://notebooklm.google.com
- Google 계정 로그인 (개인 Gmail OK, Workspace도 가능)
- **"New notebook"** 클릭 → 이름 지정 (예: `dopaminews-climate-2026-08-09`)

---

## Step 2 — 출처 (Sources) 추가

`+ Add source` 클릭 → 4가지 옵션:

### 2.1 Website (가장 일반적) — news article URL
- 예: `https://www.reuters.com/...` (climate change 2026-08-09 article)
- 출처가 **다 load될 때까지 대기** (보통 30초~2분)
- NotebookLM이 자동으로 본문 추출 + 요약

### 2.2 YouTube URL
- 관련 industry talk, news video
- 자동 transcript 추출

### 2.3 Google Drive (Docs, Sheets, Slides, PDF)
- 사내 보고서, 산업 분석
- 연동된 Google 계정에서 자동 import

### 2.4 직접 붙여넣기
- 긴 article 본문, news 클립
- `+ Add source` → `Paste text` → 본문 붙여넣기

**권장**: News article URL 1개 (1차 출처) + 선택적으로 YouTube 1개 (보강 출처).

---

## Step 3 — Blog Post 초안 생성 (Studio)

NotebookLM 우측 `Studio` 패널 → **`Reports`** → **`Blog Post`** 클릭.

### 3.1 Customize (연필 아이콘)
- **Language**: `한국어` (Korean)
- **Format/Length**:
  - "Brief" → 500-1000자 (짧은 글)
  - "Detailed" → 1500-2500자 (기본 권장, dopaminews.com 1차 글)
  - "Long" → 3000자+ (pillar article)
- **Tone**: `친근한 전문가` (dopaminews.com 톤)
- **Custom instructions** (선택):
  ```
  한국 독자 대상으로 작성. 5W1H 명확. 핵심 메시지 먼저 (역피라미드).
  출처 citation 자동 삽입 ([1], [2] 형식). 짧은 문장 (1-2줄).
  dopaminews.com 톤 — 친근하지만 권위 있는. 1차 섹션에 1차 경험 메모.
  ```

### 3.2 Generate
- "Generate" 클릭 → 30초~2분
- 결과 preview 표시

### 3.3 편집 (선택)
- 결과에서 직접 inline edit 가능 (NotebookLM 2026-07 update)
- 또는 그대로 export

---

## Step 4 — Hero Image 생성 (Nano Banana)

Studio → **`Image`** → 연필 아이콘.

### 4.1 Customize
- **Format**: 16:9 (1920x1080) — dopaminews.com hero 표준
- **Style**: "Photorealistic" 또는 "Professional" (default)
- **Prompt** (예시):
  ```
  Abstract news hero image for [topic], dark blue navy background,
  subtle gradient, no text overlay, 1920x1080, professional photography
  style, dopaminews.com editorial aesthetic
  ```
  - `[topic]`을 실제 주제 (예: "climate change 2026")로 교체
  - "no text overlay"는 텍스트는 별도 layer로 추가 (PIL 등)
- "Generate" 클릭 → 10-30초

### 4.2 Download
- 결과 우측 "Download" → PNG
- 또는 마음에 안 들면 "Regenerate"

**대안**: NotebookLM image가 만족스럽지 않으면 wp-auto의 Pexels/Wikimedia image pipeline 사용 (v0.10.0+).

---

## Step 5 — Export Markdown

Studio → Blog Post 결과 → **`...` 메뉴** (또는 다운로드 아이콘) → **`Download as Markdown`**.

`.md` 파일 download (보통 `~/Downloads/notebooklm-*.md`).

### 5.1 .md 파일 구조 (1차 출처: github.com/philipz/notebooklm_exporter)
```markdown
---
title: Article title (NotebookLM이 자동 생성)
source: NotebookLM
exported: 2026-08-09T...
---

# Article title

[NotebookLM이 자동 생성한 본문, H1/H2/H3 구조]
```

또는 chat export 형식:
```markdown
---
exported: 2026-08-09T...
source: NotebookLM
---

# NotebookLM Conversation
Exported: 8/9/2026, ...

---

## User
[원본 prompt]

---

## Assistant
[NotebookLM 답변 — Blog Post 내용]

---
```

---

## Step 6 — frontmatter 보강 (NotebookLM → wp-auto 형식)

wp-auto의 `publish-md`는 `wp_auto/ai/markdown_loader.py`가 frontmatter 파싱.
**NotebookLM export의 frontmatter는 wp-auto에 필요한 필드가 부족** → 보강 필요.

### 6.1 필수 frontmatter 필드
```markdown
---
title: OpenAI GPT-6 발표: 추론 능력 10배 강화
slug: openai-gpt-6-launch
language: ko
categories:
  - Tech & AI
tags:
  - OpenAI
  - GPT-6
  - LLM
date: 2026-08-09
focus_keyword: OpenAI GPT-6
hero_image: assets/images/openai_gpt6_hero.png
hero_attribution: "by Alice via Pexels"
---
```

| 필드 | 설명 |
|---|---|
| `title` | WP post title |
| `slug` | URL slug (없으면 자동 생성) |
| `language` | `ko` 또는 `en` (bilingual 옵션) |
| `categories` | WP category slug 배열 (미리 생성 필수) |
| `tags` | WP tag 배열 |
| `date` | 발행일 (ISO 8601) |
| `focus_keyword` | SEO focus keyword (Rank Math) |
| `hero_image` | Hero image 경로 (`assets/images/...`) |
| `hero_attribution` | 라이선스 attribution (Pexels 등) |

### 6.2 NotebookLM → wp-auto frontmatter 변환 (수동)

1. NotebookLM export의 첫 줄 (`---`로 시작) 확인
2. 위 필수 필드 추가
3. `title`은 NotebookLM Blog Post 제목 사용
4. `categories`는 dopaminews.com의 6개 category 중 1개:
   - `Tech & AI`, `Business & Finance`, `Science & Health`,
     `World & Politics`, `Climate & Environment`, `Culture & Media`
5. 저장

---

## Step 7 — Hero Image 복사

Nano Banana download한 PNG를 wp-auto 디렉토리로 복사:

```powershell
# 예시: OpenAI GPT-6 article
$downloads = "$env:USERPROFILE\Downloads\*.png"
Copy-Item $downloads "D:\Google_blog\wp-auto\assets\images\openai_gpt6_hero.png"
```

또는 직접 다운로드 폴더에서 `D:\Google_blog\wp-auto\assets\images\` 로 drag & drop.

**파일명 규칙**: `{slug}_hero.png` (예: `openai-gpt-6-launch_hero.png`)

---

## Step 8 — inbox/에 저장

`.md` 파일을 `D:\Google_blog\wp-auto\inbox\` 디렉토리에 저장:

```
D:\Google_blog\wp-auto\inbox\
├── openai-gpt-6-launch.md       (NotebookLM export)
├── climate-2026-q3-report.md
├── fed-rate-cut-september.md
└── ...
```

`.gitignore`에 `inbox/` 추가되어 commit 안 됨 (로컬 콘텐츠).

---

## Step 9 — publish-md 실행

PowerShell 창:

```powershell
cd D:\Google_blog\wp-auto
.\.venv\Scripts\python.exe -m wp_auto publish-md inbox\openai-gpt-6-launch.md
```

또는 wp-auto UI (`http://127.0.0.1:8767/publish`):
- File: `inbox\openai-gpt-6-launch.md` 선택
- Submit

### publish-md 출력 예시
```
Markdown 로드: inbox\openai-gpt-6-launch.md
  Title: OpenAI GPT-6 발표: 추론 능력 10배 강화
  Language: ko
  Sections (H2): 4
  Tags: ['OpenAI', 'GPT-6', 'LLM']
  Categories: ['Tech & AI']

[1] 청크 변환: H2 4개 → 4개 sub-post
[2] WP 발행 (Mock 모드):
  - post_id: 108
  - status: draft
  - url: https://dopaminews.com/openai-gpt-6-launch
```

---

## Step 10 — WP 발행 확인

### 10.1 Mock 모드 (`WP_MOCK=true`)
- SQLite DB에 draft 저장 (`data/wp_auto.db`)
- `data/wp_auto.db` 확인: `sqlite3 data/wp_auto.db "SELECT id, post_title, post_status FROM wp_posts ORDER BY id DESC LIMIT 5;"`

### 10.2 Real 모드 (`WP_MOCK=false`)
- WP REST API로 자동 publish
- `https://dopaminews.com/wp-admin/edit.php` → Draft 상태 확인
- **InfinityFree 무료 tier는 REST API 차단** → publish가 실패할 수 있음
  - 해결: WP Admin에서 수동 publish (InfinityFree plan 한계)

---

## 🎯 5-Post 워크플로우 (Dopaminews.com 다중 카테고리)

매주 5-Post 발행 시:

| 카테고리 | 출처 (예시) | 시간 |
|---|---|---|
| Tech & AI | Reuters Tech / Ars Technica | 5 min |
| Business & Finance | Bloomberg / WSJ | 5 min |
| Science & Health | Nature News / Science Daily | 5 min |
| World & Politics | AP News / BBC | 5 min |
| Climate & Environment | NOAA / NASA Earth Observatory | 5 min |

**전체 25분** (5-Post × 5분). NotebookLM → wp-auto publish-md 자동화.

---

## 💡 Pro Tips

1. **소스 다양성**: 1개 news URL만 쓰지 말고, 관련 YouTube 영상 1개 추가. NotebookLM이 cross-reference로 더 풍부한 초안 생성.
2. **Custom instructions에 dopamiens.com 톤 명시**: "친근하지만 권위 있는" / "기술 용어 쉽게 설명" / "한국 독자 관점".
3. **Image 보강**: Nano Banana 결과가 약하면 wp-auto의 Pexels/Wikimedia image pipeline (v0.10.0+)으로 자동 보강.
4. **Hallucination 검증**: publish 후 1차 출처 link 다시 클릭해서 인용 정확성 검증 (NotebookLM 인용도 100% 정확하지는 않음).
5. **여러 Notebook**: 카테고리별로 notebook 분리 (예: `dopaminews-tech`, `dopaminews-business`). NotebookLM Plus ($19.99/월)는 notebook 500개까지.

---

## 🔗 1차 출처

- [Google blog 2026-07: NotebookLM Gemini 3.5 + Antigravity + Nano Banana image](https://blog.google/innovation-and-ai/products/notebooklm/better-research-notebooklm/)
- [Google blog 2025-08: Blog Post format + Reports](https://blog.google/innovation-and-ai/models-and-research/google-labs/notebooklm-student-features/)
- [Google Workspace Updates 2026-03: Infographics 10 styles, PPTX export, EPUB](https://workspaceupdates.googleblog.com/2026/03/new-ways-to-customize-and-interact-with-your-content-in-NotebookLM.html)
- [Google blog 한국어: Audio Overview 50+ 언어](https://blog.google/intl/ko-kr/company-news/technology/notebooklm-audio-overviews-50-languages-kr/)
- [DigitalOcean: What Is NotebookLM 2026](https://www.digitalocean.com/resources/articles/what-is-notebooklm)
- [Export from NotebookLM Complete Guide (exploreaitogether.com)](https://exploreaitogether.com/export-download-notebooklm-guide/)
- [philipz/notebooklm_exporter (GitHub) — Markdown export format](https://github.com/philipz/notebooklm_exporter)
