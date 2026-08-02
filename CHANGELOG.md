# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- W5: GSC API 연동 + 월간 리포트
- W6: GitHub Actions cron (CWV 자동 측정)
- W7~W8: 안정화, 외부 사용자 온보딩

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
