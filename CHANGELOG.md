# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Ollama 연동 + AI 초안 생성 (W2)
- Pillow 이미지 자동 최적화 (W3)
- MockWordPressClient + WP 연동 (W4)
- Playwright CWV 측정 (W3)
- GSC API 연동 + 월간 리포트 (W5~W6)

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
