# WP-Free-Blog-Automation

> 워드프레스 블로그 자동화 도구 (1인 운영자용, 무료 우선)
> 
> **도구 우선 빌드** — 점수화 코어 같은 WP-독립 모듈을 먼저 완성하고, WP 연동은 추후.

## 빠른 시작 (Day 1)

```bash
# 1. 가상환경 (이미 만들어뒀으면 skip)
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows PowerShell
# source .venv/bin/activate  # macOS/Linux

# 2. 의존성 설치 (editable)
pip install -e ".[dev]"

# 3. 점수화 코어 단독 실행
python -m wp_auto verify tests/fixtures/excellent_post.html
```

## 상태 (2026-08-02)

- [x] Day 1: 점수화 코어 이식 (SpecializedContentOptimizer)
- [x] Day 1: 5개 단위 테스트
- [ ] D2~D7: SEO 분석기, HTML 입력 파싱, 통합 CLI
- [ ] W2: AI 초안 생성 (Ollama)
- [ ] W3: 이미지 최적화
- [ ] W4: WP REST API (Mock 우선, Real은 사이트 세팅 시)

자세한 로드맵은 워크스페이스 루트의 `기획서.md` + `코딩계획서.md` 참조.

## 환경

- Python 3.14.5 (3.11+ 필요)
- 의존성: click, loguru, pydantic, beautifulsoup4, lxml + dev: pytest, ruff

## 권장 (선택)

- `uv` (https://docs.astral.sh/uv/) — pip보다 10배 빠른 패키지 매니저
  ```bash
  uv sync --extra dev
  uv run python -m wp_auto verify tests/fixtures/excellent_post.html
  ```
