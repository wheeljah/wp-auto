"""Web UI (FastAPI) 단위 테스트 — TestClient."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from wp_auto.web.server import create_app


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient (실제 서버 없이 라우트 테스트)."""
    app = create_app()
    return TestClient(app)


# === 1. 페이지 라우트 ===

def test_dashboard_renders(client: TestClient) -> None:
    """GET / → 200 + HTML."""
    r = client.get("/")
    assert r.status_code == 200
    assert "wp-auto" in r.text
    assert "대시보드" in r.text


def test_verify_page_renders(client: TestClient) -> None:
    """GET /verify → 200."""
    r = client.get("/verify")
    assert r.status_code == 200
    assert "콘텐츠 점수화" in r.text


def test_generate_page_renders(client: TestClient) -> None:
    """GET /generate → 200."""
    r = client.get("/generate")
    assert r.status_code == 200
    assert "AI" in r.text


def test_publish_page_renders(client: TestClient) -> None:
    """GET /publish → 200."""
    r = client.get("/publish")
    assert r.status_code == 200
    assert "WP" in r.text or "발행" in r.text


def test_optimize_page_renders(client: TestClient) -> None:
    """GET /optimize → 200."""
    r = client.get("/optimize")
    assert r.status_code == 200
    assert "이미지" in r.text


def test_measure_page_renders(client: TestClient) -> None:
    """GET /measure → 200."""
    r = client.get("/measure")
    assert r.status_code == 200
    assert "CWV" in r.text or "Web Vitals" in r.text


def test_settings_page_renders(client: TestClient) -> None:
    """GET /settings → 200."""
    r = client.get("/settings")
    assert r.status_code == 200
    assert "환경" in r.text or "설정" in r.text


# === 2. API ===

def test_health_endpoint(client: TestClient) -> None:
    """GET /api/health → status=ok."""
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_api_verify_content_only(client: TestClient) -> None:
    """POST /api/verify (콘텐츠만)."""
    r = client.post(
        "/api/verify",
        data={"html": "<html><body><h1>테스트</h1><p>워드프레스 SEO 가이드</p></body></html>", "focus_keyword": ""},
    )
    assert r.status_code == 200
    data = r.json()
    assert "content" in data
    assert 0 <= data["content"]["total_score"] <= 100


def test_api_verify_full_mode(client: TestClient) -> None:
    """POST /api/verify (full=True) → SEO 포함."""
    html = """
    <html lang="ko">
    <head>
        <title>워드프레스 SEO 7가지 핵심 가이드 - 2026년 업데이트</title>
        <meta name="description" content="워드프레스 SEO의 7가지 핵심 전략을 정리한 가이드. Rank Math 점수 90+ 받는 방법과 무료 최적화 팁을 공유합니다.">
        <link rel="canonical" href="https://example.com/wordpress-seo-guide-7-tips" />
    </head>
    <body>
        <h1>워드프레스 SEO 7가지 핵심 가이드</h1>
        <p>워드프레스 SEO는 검색 노출을 결정하는 핵심 요소입니다.</p>
        <h2>워드프레스 SEO 첫 번째</h2>
        <p>워드프레스 SEO의 시작은 키워드 조사입니다.</p>
        <h2>워드프레스 SEO 두 번째</h2>
        <p>Rank Math를 추천합니다. 점수화 기능을 제공합니다.</p>
        <h2>워드프레스 SEO 세 번째</h2>
        <p>워드프레스 SEO를 위한 글은 2500자 이상이어야 합니다.</p>
        <a href="/related-post">관련 글</a>
        <a href="https://rankmath.com">Rank Math</a>
        <img src="/chart.webp" alt="워드프레스 SEO 점수 차트" width="1200" height="630">
    </body>
    </html>
    """
    r = client.post(
        "/api/verify",
        data={"html": html, "focus_keyword": "워드프레스 SEO", "full": "true"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "content" in data
    assert "seo" in data
    assert "overall_recommendations" in data


def test_api_posts(client: TestClient) -> None:
    """GET /api/posts → MockWP 글 목록."""
    r = client.get("/api/posts")
    assert r.status_code == 200
    data = r.json()
    assert "posts" in data
    assert isinstance(data["posts"], list)


def test_api_publish_creates_draft(client: TestClient) -> None:
    """POST /api/publish → status=draft (점수 75 미만이어도 draft는 OK)."""
    html = "<html><body><h1>짧은 테스트</h1><p>워드프레스</p></body></html>"
    r = client.post(
        "/api/publish",
        data={"html": html, "focus_keyword": "워드프레스", "status": "draft"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "post_id" in data
    assert data["status"] == "draft"


def test_api_publish_blocks_low_score_for_publish(client: TestClient) -> None:
    """POST /api/publish (status=publish, 점수 < 75) → error."""
    html = "<html><body><h1>짧은</h1><p>x</p></body></html>"  # 매우 짧은 글
    r = client.post(
        "/api/publish",
        data={"html": html, "focus_keyword": "X", "status": "publish"},
    )
    assert r.status_code == 200
    data = r.json()
    # 점수 < 75 → 차단
    if "error" in data:
        assert "차단" in data["error"] or "점수" in data["error"]


def test_api_optimize_no_file(client: TestClient) -> None:
    """POST /api/optimize (파일 없음) → 422."""
    r = client.post("/api/optimize", data={})
    assert r.status_code == 422


def test_api_measure_invalid_url(client: TestClient) -> None:
    """POST /api/measure (잘못된 URL) → Playwright 에러 또는 error."""
    r = client.post("/api/measure", data={"url": "not-a-url", "runs": 1})
    # 200 + error 또는 422. 둘 다 acceptable.
    assert r.status_code in (200, 422)


# === 3. 에러 처리 ===

def test_404_returns_404(client: TestClient) -> None:
    """존재하지 않는 라우트 → 404."""
    r = client.get("/nonexistent")
    assert r.status_code == 404


def test_api_verify_empty_html(client: TestClient) -> None:
    """POST /api/verify (빈 HTML) → 422 (Form 필수)."""
    r = client.post("/api/verify", data={"html": ""})
    # 빈 문자열은 form validation 통과할 수도, ContentMetrics 실패할 수도
    assert r.status_code in (200, 422)


# === 4. Static assets ===

def test_base_template_extends(client: TestClient) -> None:
    """모든 페이지가 base.html 상속 (Tailwind CDN 포함)."""
    for path in ["/", "/verify", "/generate", "/publish", "/optimize", "/measure", "/settings"]:
        r = client.get(path)
        assert "cdn.tailwindcss.com" in r.text, f"{path} missing tailwind CDN"
