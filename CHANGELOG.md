# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- v0.4.0: 안정화 (테스트 커버리지 80%, Docker 옵션, README 보강)
- v1.0.0: 외부 공개 가능 상태 (의존성 핀 고정, 시그너처, GitHub Pages 문서)

## [0.3.0] - 2026-08-02

### Added — Phase 4: Web UI (1인 self-use)

**FastAPI 기반 로컬 웹 UI**
- `wp_auto/web/server.py` — FastAPI app factory + uvicorn 진입점
  - `wp-auto ui` 명령으로 시작 (기본 `http://127.0.0.1:8765`)
  - `WP_AUTO_PORT` 환경변수로 포트 변경 가능 (예: 8765 충돌 시 7777)
  - localhost only, 인증 없음 (1인 self-use)
- `wp_auto/web/routes.py` — 7개 페이지 + 7개 API
  - `GET /` — 대시보드 (최근 발행 5개)
  - `GET /verify` + `POST /api/verify` — 콘텐츠 + (--full) SEO 통합 점수화
  - `GET /generate` + `POST /api/generate` — Ollama AI 초안 생성 (1~3분)
  - `GET /publish` + `POST /api/publish` — 점수화 게이트 + WP 발행
  - `GET /optimize` + `POST /api/optimize` — Pillow 이미지 WebP/AVIF
  - `GET /measure` + `POST /api/measure` — Playwright CWV (LCP/INP/CLS)
  - `GET /settings` + `GET /api/posts` + `GET /api/health` — 설정 + 글 목록 + 헬스 체크
- `wp_auto/web/templates/` — 7개 HTML (base + 6 페이지)
  - TailwindCSS CDN (빌드 불필요)
  - vanilla JS (AJAX, 진행 표시, 결과 렌더링)
- `wp_auto/cli/ui.py` — `wp-auto ui` CLI 명령
  - `--port`, `--host`, `--reload` 옵션
- `tests/unit/test_web.py` — 18개 (FastAPI TestClient, 7개 페이지 + 7개 API + 404 + 정적 자산)

### Tested
- **149 passed** in 6.32s
  - 기존 131 + web 18
- ruff: All checks passed
- 7개 페이지 라이브 검증: 200 OK (`/api/health` 정상 응답)

### Project Structure (v0.3.0)
```
wp-auto/
├── wp_auto/
│   ├── ai/                       # W2: LLM 통합
│   ├── cli/
│   │   ├── main.py                # 최상위 (--version, doctor, example, verify, publish, list-posts, ui)
│   │   ├── verify.py              # 콘텐츠 + SEO 점수화
│   │   ├── publish.py             # WP 발행 (Mock/Real)
│   │   └── ui.py                  # v0.3.0: Web UI 시작
│   ├── core/                      # 점수화, SEO 분석
│   ├── optimize/                  # W3: 이미지, lazy, CWV
│   ├── wp/                        # W4: WP 연동
│   └── web/                       # v0.3.0: FastAPI UI
│       ├── server.py
│       ├── routes.py
│       └── templates/             # 7개 HTML
└── tests/unit/                    # 8개 파일, 149개 테스트
```

### Notes
- 1인 self-use 패턴 확정: 도구 우선 빌드 + HTML UI + 로컬 PC + localhost only
- 8000/9000 포트 점유 중 → 8765 기본, 충돌 시 환경변수 `WP_AUTO_PORT` 또는 CLI `--port`
- W5/W6 (분석/자동화) 보류 — 1인용 ROI 낮음, score history만 슬림 버전으로 추후 검토
- 외부 공개 시(v1.0) 풀 W5/W6 + Docker + 문서 사이트

## [0.2.0] - 2026-08-02

## [0.2.0] - 2026-08-02

### Added — Phase 2~3: AI + 최적화 + WP 연동

**W2 - AI 콘텐츠 생성 (Ollama)**
- `wp_auto/ai/ollama_client.py` — OllamaClient (httpx), MockOllamaClient, LLMClient Protocol
  - 100% 무료, 온디바이스, API 키 불필요
  - Ollama 미설치 환경에서도 Mock으로 단위 테스트 가능
- `wp_auto/ai/content_generator.py` — ContentGenerator 오케스트레이션
  - 흐름: outline (JSON) → draft (HTML) → review (점수 < 75 시)
  - 자동 점수화 게이트 + 최대 max_iterations (default 3) 반복
- `wp_auto/ai/prompts/`: outline.txt, draft.txt, review.txt, alt_text.txt
  - 자료 `워드프레스_자동화1.txt` L137-141의 "AI 80% + 사람 20% 하이브리드" 모델 구현
- `tests/unit/test_content_generator.py` — 20개 (MockOllamaClient + Outline/GeneratedPost)

**W3 - 최적화**
- `wp_auto/optimize/image_optimizer.py` — Pillow WebP/AVIF 변환 + 리사이즈
  - EXIF 회전 보정, LANCZOS 리사이즈, 평균 -40% 크기 감소
- `wp_auto/optimize/lazy_loader.py` — HTML lazy loading + width/height 자동 주입
  - 첫 번째 img는 LCP로 `loading="eager" + fetchpriority="high"` (자료 `범용_로직1.txt` L301-308)
- `wp_auto/optimize/cwv_measurer.py` — Playwright + web-vitals 측정
  - 3회 반복 중앙값, 모바일 뷰포트 (375x812), LCP/INP/CLS Good/Needs Improvement/Poor 판정
  - 자동 권고 생성 (LCP > 2.5s → preload, INP > 200ms → defer JS, CLS > 0.1 → dimensions)
- `tests/unit/test_image_optimizer.py` — 13개
- `tests/unit/test_cwv_measurer.py` — 15개 (rating/recommendations 단위)

**W4 - WordPress 연동 (도구 우선 빌드)**
- `wp_auto/wp/client.py` — `WordPressClient` Protocol + Post/Category/Media dataclass
- `wp_auto/wp/mock_client.py` — `MockWordPressClient` (in-memory + SQLite 옵션)
  - SQLite 모드: 여러 CLI 호출에 걸쳐 데이터 유지
  - 모든 CRUD 메서드 구현 (create_draft, update_post, publish, schedule_publish, upload_image 등)
- `wp_auto/wp/real_client.py` — `RealWordPressClient` (httpx + WordPress Application Password)
  - HTTP Basic Auth, Rate Limiter (5분당 100req)
  - 5분 window 토큰 버킷 알고리즘
- `wp_auto/wp/factory.py` — `get_wp_client()` 환경변수 자동 라우팅
  - `WP_SITE_URL` 비어있거나 `WP_MOCK=true` → Mock
  - `DB_PATH` 환경변수로 SQLite 영속화 활성화
- `wp_auto/cli/publish.py` — `wp-auto publish <html>` + `wp-auto list-posts`
  - 점수화 게이트 (75점 미만 + status=publish/future면 차단, --force로 무시)
  - HTML에서 <h1>/<title> 추출, canonical URL에서 slug 추출
- `tests/unit/test_mock_wp_client.py` — 18개 (CRUD + SQLite 영속화 + factory)

### Tested
- **131 passed** in 4.87s
  - content_score: 19 + html_parser: 21 + seo_analyzer: 25 + content_generator: 20 +
    image_optimizer: 13 + cwv_measurer: 15 + mock_wp_client: 18
- ruff: All checks passed

### Integration Smoke
- `python -m wp_auto publish tests/fixtures/excellent_post.html` → post_id=1 생성 (Mock, SQLite 영속화)
- `python -m wp_auto list-posts` → post_id=1 표시
- `ollama pull llama3.1:8b` (4.9GB) → AI 초안 생성 가능

### Project Structure
```
wp-auto/
├── wp_auto/
│   ├── ai/                       # W2: LLM 통합
│   │   ├── ollama_client.py
│   │   ├── content_generator.py
│   │   └── prompts/
│   ├── cli/
│   │   ├── main.py                # 최상위 (--version, doctor, example, verify, publish, list-posts)
│   │   ├── verify.py              # 콘텐츠 + SEO 점수화
│   │   └── publish.py             # WP 발행 (Mock/Real)
│   ├── core/                      # 점수화, SEO 분석
│   ├── optimize/                  # W3: 이미지, lazy, CWV
│   │   ├── image_optimizer.py
│   │   ├── lazy_loader.py
│   │   └── cwv_measurer.py
│   └── wp/                        # W4: WP 연동
│       ├── client.py              # Protocol
│       ├── mock_client.py         # Mock
│       ├── real_client.py         # Real
│       └── factory.py             # 라우팅
└── tests/unit/                    # 7개 파일, 131개 테스트
```

### Notes
- 도구 우선 빌드 패턴 유지: 실 WP 사이트 없이 모든 모듈 단독 실행 가능
- Phase 4 (분석/리포트) + Phase 5 (안정화) 진행 예정
- 0.x.y 버전이므로 호환성 깨는 변경 자유롭게 가능

## [0.1.0] - 2026-08-02

## [0.1.0] - 2026-08-02

### Added — Phase 1: WP-독립 코어

**콘텐츠 점수화 (Day 1)**
- `wp_auto/core/content_score.py` — `SpecializedContentOptimizer` 이식
  - 자료 `범용_로직1.txt` L55-272 기반
  - 4개 카테고리 100점 만점: content_depth (40) / eeat (25) / seo (20) / speed (15)
  - 합격 기준: 90+ EXCELLENT, 75+ PASS, <75 FAIL
- `wp_auto/core/html_parser.py` — `parse_html_to_metrics()` (D2)
  - 15+ 휴리스틱으로 HTML → ContentMetrics 자동 변환
  - `_count_chars` 버그 학습: soup 변형 회피 (html 직접 받기)
- `wp_auto/core/seo_analyzer.py` — `RankMathStyleAnalyzer` (D3)
  - 4개 카테고리 100점: basic_seo (30) / additional (40) / title_readability (15) / content_readability (15)
  - 22개 SEO 체크 항목 (자료 `워드프레스_자동화1.txt` L165-228 기반)
  - 키워드 밀도, URL slug 매칭, 단락 길이 등

**CLI 진입점 (D2, D6, D7)**
- `wp-auto --version` — 버전 출력
- `wp-auto doctor` — 환경 + 의존성 + 점수화 코어 점검
- `wp-auto example` — EXCELLENT 케이스 실행 (자료 원본 sample)
- `wp-auto verify <html-file>` — 콘텐츠 점수화
- `wp-auto verify <html-file> --focus-keyword "X"` — 키워드 자동 체크
- `wp-auto verify <html-file> --full` — **콘텐츠 + SEO 통합 점수 카드**
- `wp-auto verify <html-file> --json` — JSON 출력 (CI/CD)
- `wp-auto verify <html-file> --save-report FILE` — 마크다운 리포트

**테스트 (65개)**
- `tests/unit/test_content_score.py` — 19개 (점수화 코어 단위)
- `tests/unit/test_html_parser.py` — 21개 (HTML 파싱)
- `tests/unit/test_seo_analyzer.py` — 25개 (SEO 분석)
- `tests/fixtures/excellent_post.html` (5KB) + `tests/fixtures/thin_post.html` (250B)

**문서**
- 기획서 v0.2 (`기획서.md`)
- 코딩계획서 v0.2 (`코딩계획서.md`)
- README.md (Day 1~D7 결과 + 통합 점수 카드 예시)
- LICENSE (MIT)
- CHANGELOG.md (이 파일)

### Project Structure
- Python 3.11+ (검증: 3.14.5)
- 패키지 매니저: pip + venv (uv 권장)
- 빌드: hatchling
- 테스트: pytest + pytest-asyncio
- 린트: ruff
- **WP 의존성 0개** — 도구 단독 실행 가능

### Notes
- 도구 우선 빌드 패턴: 운영 중인 WP 사이트 없이 점수화 코어 / SEO 분석 / HTML 파싱 먼저 완성
- Phase 2~5는 추후 (로드맵 참조)
- 첫 공개 release. 호환성 깨는 변경은 1.0 이전까지 자유롭게 가능
