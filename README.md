# WP-Free-Blog-Automation

> 워드프레스 블로그 자동화 도구 (1인 운영자용, 무료 / 1인 / 도구 우선 빌드)
>
> **도구 우선 빌드** — 점수화 코어 같은 WP-독립 모듈을 먼저 완성하고, WP 연동은 추후.

[![MIT License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/wheeljah/wp-auto/blob/main/LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/Tests-65%20passed-brightgreen.svg)](#테스트)
[![WP Dependencies](https://img.shields.io/badge/WP%20deps-0-success.svg)](#features)

---

## ✨ Features (v0.1.0)

- ✅ **콘텐츠 점수화 (100점 만점)** — 자료 `범용_로직1.txt` L97-272 이식, 19개 단위 테스트
- ✅ **HTML 파서 (D2)** — BeautifulSoup4로 자동 채움 (15+ 휴리스틱), 21개 테스트
- ✅ **Rank Math 스타일 SEO 분석기 (D3)** — 100점 (basic 30 / additional 40 / title 15 / content 15), 25개 테스트
- ✅ **통합 점수 카드 (D4~D7)** — 콘텐츠 + SEO 동시 평가 + 우선순위 권고 10개
- ✅ **마크다운 리포트** (`--save-report`)
- ✅ **JSON 출력** (`--json`, CI/CD 연동)
- ✅ **CLI 4개 명령**: `example`, `doctor`, `verify`, `--full` 통합 모드
- 🚧 **WP 연동** — Phase 3 (W4) 예정, Mock 우선

> **WP 의존성 0개** — 점수화/SEO/CWV는 실 WP 사이트 없이도 단독 실행.

---

## 📦 설치

```bash
# 1. 가상환경
python -m venv .venv
.venv\Scripts\Activate.ps1    # Windows PowerShell
# source .venv/bin/activate   # macOS/Linux

# 2. 의존성 (editable, dev 포함)
pip install -e ".[dev]"

# 또는 uv (10배 빠름)
uv sync --extra dev
```

## 🚀 빠른 시작

### 환경 진단

```bash
python -m wp_auto doctor
# → [OK] click / loguru / pydantic / beautifulsoup4 / lxml
# → [OK] 점수화 코어 작동
```

### 콘텐츠 점수화 (자료 `범용_로직1.txt` L246-272 sample)

```bash
python -m wp_auto example
# → 총점: 100 / 100, 판정: 우수
```

### HTML 파일 점수화

```bash
python -m wp_auto verify tests/fixtures/excellent_post.html --focus-keyword "워드프레스 SEO"
# → 총점: 77/100, PASS (발행 가능)
# → 권고: 글자 수 부족, 불필요한 JS/CSS ...
```

### 통합 점수 카드 (콘텐츠 + SEO)

```bash
python -m wp_auto verify tests/fixtures/excellent_post.html \
    --focus-keyword "워드프레스 SEO" --full
```

```
============================================================
  WP-AUTO 통합 점수 카드 (--full)
============================================================
  파일: tests/fixtures/excellent_post.html
  포커스 키워드: 워드프레스 SEO

┌─ 콘텐츠 품질 (100점) ────────────────────────
│  총점: 77 / 100  │  content_depth 28  eeat 25  seo 13  speed 11
└───────────────────────────────────────────────

┌─ SEO 분석 (Rank Math 스타일, 100점) ──────────
│  총점: 39 / 100  │  basic_seo 4  additional 15  title 10  content 10
└───────────────────────────────────────────────

┌─ 개선 권고사항 ───────────────────────────────
│   1. URL/슬러그에 메인 키워드를 포함하세요.
│   2. Title이 메인 키워드로 시작하면 좋습니다.
│   3. 메타 설명 길이를 120-160자로 조정하세요.
│   ...
│  10. 심층 분석과 가이드를 더 추가하세요.
└───────────────────────────────────────────────

>>> 종합 판정: SEO 보완 필요
============================================================
```

### 마크다운 리포트 저장

```bash
python -m wp_auto verify file.html --focus-keyword "X" --full --save-report out/report.md
```

### JSON 출력 (CI/CD)

```bash
python -m wp_auto verify file.html --focus-keyword "X" --full --json | jq '.'
```

---

## 📊 점수화 시스템

### 콘텐츠 품질 (SpecializedContentOptimizer)

| 카테고리 | 배점 | 평가 항목 |
|---------|-----|----------|
| Content Depth | 40 | 글자 수, 원본 분석, 단계별 가이드, 데이터/사례, 비교표, FAQ |
| E-E-A-T | 25 | 1차 경험, 저자 소개, 출처(3+), 업데이트 날짜 |
| SEO Technical | 20 | 키워드 in 제목, H2(4+), 내부링크(3+), 외부링크(2+), 메타 설명(140-165) |
| Page Speed | 15 | 이미지 최적화, lazy, 불필요 JS/CSS 제거, LCP ≤ 2.5s |

**합격 기준**:
- 90+ : 우수 (EXCELLENT)
- 75~89 : 발행 가능 (PASS)
- <75 : 보완 필요 (FAIL)

### SEO 분석 (Rank Math 스타일)

| 카테고리 | 배점 | 항목 수 |
|---------|-----|--------|
| Basic SEO | 30 | 8개 (URL, title 시작/포함, meta desc, permalink, 첫/마지막 문단) |
| Additional | 40 | 8개 (H2, density, 첫/마지막 10%, 내부/외부 링크, image alt, url slug) |
| Title Readability | 15 | 3개 (숫자, power word, 길이 50-60) |
| Content Readability | 15 | 3개 (600+ 단어, 단락 길이, 모든 img alt) |

---

## 🛠 CLI 명령어

| 명령 | 설명 |
|------|------|
| `wp-auto --version` | 버전 출력 |
| `wp-auto doctor` | 환경 + 의존성 + 점수화 코어 점검 |
| `wp-auto example` | EXCELLENT 케이스 점수화 실행 (자료 원본 sample) |
| `wp-auto verify <html-file>` | HTML 파일 점수화 (100점 콘텐츠) |
| `wp-auto verify <html-file> --focus-keyword "X"` | 키워드 자동 체크 |
| `wp-auto verify <html-file> --full` | **콘텐츠 + SEO 통합 카드** (focus-keyword 필수) |
| `wp-auto verify <html-file> --json` | JSON 형식 (CI/CD) |
| `wp-auto verify <html-file> --save-report FILE` | 마크다운 리포트 |

---

## ✅ 테스트

```bash
pytest
# 65 passed in 0.34s
```

세부:
- `tests/unit/test_content_score.py` — 19개 (점수화 코어)
- `tests/unit/test_html_parser.py` — 21개 (HTML 파서)
- `tests/unit/test_seo_analyzer.py` — 25개 (SEO 분석기)

---

## 📂 디렉토리 구조

```
wp-auto/
├── .env.example
├── .gitignore
├── CHANGELOG.md
├── LICENSE                          # MIT (GitHub이 추가)
├── README.md
├── pyproject.toml
├── wp_auto/
│   ├── __init__.py
│   ├── __main__.py                  # python -m wp_auto 진입점
│   ├── cli/
│   │   ├── main.py                  # example, doctor
│   │   └── verify.py                # verify (--full 통합)
│   └── core/
│       ├── content_score.py         # SpecializedContentOptimizer (Day 1)
│       ├── html_parser.py           # HTML → ContentMetrics (D2)
│       └── seo_analyzer.py          # Rank Math 스타일 (D3)
└── tests/
    ├── fixtures/
    │   ├── excellent_post.html
    │   └── thin_post.html
    └── unit/
        ├── test_content_score.py    # 19개
        ├── test_html_parser.py      # 21개
        └── test_seo_analyzer.py     # 25개
```

---

## 🗺 로드맵

| Phase | 상태 | 내용 |
|------|------|------|
| **Phase 1: WP-독립 코어** | ✅ 완료 (v0.1.0) | 점수화 + SEO + HTML 파서 + 통합 카드 |
| Phase 2: AI 초안 + 이미지 (W2~W3) | 🚧 예정 | Ollama + Pillow |
| Phase 3: WP 연동 (W4) | 🚧 예정 | MockWordPressClient 우선 |
| Phase 4: 분석 & 리포트 (W5~W6) | 🚧 예정 | GSC API, GitHub Actions |
| Phase 5: 안정화 (W7~W8) | 🚧 예정 | 테스트 커버리지 80%, 첫 외부 사용자 |

자세한 내용은 [`기획서.md`](./기획서.md) + [`코딩계획서.md`](./코딩계획서.md) (워크스페이스 루트) 참조.

---

## 🔧 환경

- Python 3.11+ (검증: 3.14.5)
- 의존성: click, loguru, pydantic, beautifulsoup4, lxml
- dev: pytest, pytest-asyncio, ruff
- **WP 의존성 0개** (도구 단독 작동)

## 📄 License

[MIT](./LICENSE) © 2026 wheeljah

## 🤝 Contributing

1인 운영자 도구. 이슈/PR 환영.

## 📚 자료

- 점수화 로직 원본: `범용_로직1.txt` (사용자 제공 자료)
- WP 자동화 트렌드: `워드프레스_자동화1.txt` (사용자 제공 자료)
- Rank Math 점수 항목: <https://rankmath.com/kb/>
