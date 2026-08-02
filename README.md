# WP-Free-Blog-Automation

> 워드프레스 블로그 자동화 도구 (1인 운영자용, 무료 우선)
>
> **도구 우선 빌드** — 점수화 코어 같은 WP-독립 모듈을 먼저 완성하고, WP 연동은 추후.

## Day 1 결과 (2026-08-02)

점수화 코어 이식 + 단위 테스트 19개 통과 + CLI 진입점 작동 확인.

- `wp_auto/core/content_score.py` — `SpecializedContentOptimizer` (자료 `범용_로직1.txt` L55-272 이식)
- `wp_auto/cli/main.py` — `wp-auto example`, `wp-auto doctor`, `wp-auto --version`
- `tests/unit/test_content_score.py` — **19 passed in 0.09s**
- **WP 의존성 0개** — Day 1 범위 어디서든 단독 실행 가능

## 빠른 시작

```bash
# 0. 의존성 (이미 venv 만들어뒀으면 skip)
python -m venv .venv
.venv\Scripts\Activate.ps1    # Windows PowerShell
# source .venv/bin/activate   # macOS/Linux
pip install -e ".[dev]"

# 1. 점수화 코어 스모크 테스트
python -m wp_auto example
# → 총점: 100 / 100, 판정: 우수

# 2. 환경 진단
python -m wp_auto doctor
# → [OK] click / loguru / pydantic / ... / [OK] 점수화 코어

# 3. 단위 테스트
pytest -q
# → 19 passed
```

## CLI 명령어 (Day 1 범위)

| 명령 | 설명 |
|------|------|
| `wp-auto --version` | 버전 출력 |
| `wp-auto doctor` | 환경 + 의존성 + 점수화 코어 점검 |
| `wp-auto example` | EXCELLENT 케이스 점수화 실행 (자료 원본 sample) |

D2에서 추가:
- `wp-auto verify <html-file>` — HTML 파일 점수화
- `wp-auto verify <url>` — 공개 URL 점수화 (W3에서 Playwright)
- `wp-auto verify <wp-post-id>` — WP 글 점수화 (W4)

## 점수화 시스템 (100점 만점)

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

## 상태 (로드맵)

- [x] **Day 1**: 점수화 코어 이식 + 19개 단위 테스트
- [ ] **D2**: HTML 파서 + `verify_html()` + `wp-auto verify <html-file>`
- [ ] **D3**: Rank Math 스타일 SEO 분석기 (100점)
- [ ] **D4~D7**: 통합 점수 카드 출력
- [ ] **W2**: Ollama 연동 + AI 초안 생성
- [ ] **W3**: Pillow 이미지 최적화 + Playwright CWV 측정
- [ ] **W4**: WP REST API (Mock 우선, Real은 사이트 세팅 시)

자세한 로드맵은 워크스페이스 루트의 `기획서.md` + `코딩계획서.md` 참조.

## 환경

- Python 3.14.5 (3.11+ 필요)
- 의존성: click, loguru, pydantic, beautifulsoup4, lxml + dev: pytest, ruff

## 디렉토리 구조 (Day 1)

```
wp-auto/
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
├── wp_auto/
│   ├── __init__.py
│   ├── __main__.py            # python -m wp_auto
│   ├── cli/main.py            # example, doctor
│   └── core/content_score.py  # SpecializedContentOptimizer
└── tests/unit/test_content_score.py  # 19개
```

W2부터 `ai/`, `wp/`, `optimize/`, `analytics/`, `db/`, `utils/`, `scheduler/` 추가 예정.
전체 구조는 `코딩계획서.md §2` 참조.

## 권장 (선택)

- `uv` (https://docs.astral.sh/uv/) — pip보다 10배 빠른 패키지 매니저
  ```bash
  uv sync --extra dev
  uv run python -m wp_auto example
  ```
