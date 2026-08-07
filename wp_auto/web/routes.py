"""FastAPI 라우트: 페이지 + API.

페이지 (HTML):
- GET /          → 대시보드
- GET /verify    → 점수화
- GET /generate  → AI 초안 생성
- GET /publish   → WP 발행
- GET /optimize  → 이미지 최적화
- GET /measure   → CWV 측정
- GET /settings  → 환경 설정

API (JSON):
- POST /api/verify     → HTML + 키워드 → 점수 결과
- POST /api/generate   → 키워드 + 옵션 → GeneratedPost
- POST /api/publish    → HTML + 옵션 → post_id
- POST /api/optimize   → 이미지 파일 → WebP 결과
- POST /api/measure    → URL → CWV 결과
- GET  /api/posts      → MockWP 글 목록
- GET  /api/health     → 헬스 체크
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from loguru import logger

from wp_auto import __version__

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


# === 페이지 라우트 (HTML) ===

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    """대시보드: 최근 발행 + 점수 추이."""
    # MockWP에서 최근 글 5개
    from wp_auto.wp.factory import get_wp_client
    client = get_wp_client()
    posts = await client.list_posts(status="any", per_page=5)
    post_dicts = [
        {
            "id": p.id,
            "title": p.title,
            "status": p.status,
            "created_at": p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else "-",
        }
        for p in posts
    ]
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "version": __version__,
            "page": "dashboard",
            "posts": post_dicts,
            "wp_mode": "Mock" if not _wp_real() else "Real",
        },
    )


@router.get("/verify", response_class=HTMLResponse)
async def verify_page(request: Request) -> HTMLResponse:
    """점수화 페이지."""
    return templates.TemplateResponse(
        request=request,
        name="verify.html",
        context={"version": __version__, "page": "verify"},
    )


@router.get("/generate", response_class=HTMLResponse)
async def generate_page(request: Request) -> HTMLResponse:
    """AI 초안 생성 페이지."""
    return templates.TemplateResponse(
        request=request,
        name="generate.html",
        context={"version": __version__, "page": "generate"},
    )


@router.get("/publish", response_class=HTMLResponse)
async def publish_page(request: Request) -> HTMLResponse:
    """WP 발행 페이지."""
    return templates.TemplateResponse(
        request=request,
        name="publish.html",
        context={"version": __version__, "page": "publish"},
    )


@router.get("/optimize", response_class=HTMLResponse)
async def optimize_page(request: Request) -> HTMLResponse:
    """이미지 최적화 페이지."""
    return templates.TemplateResponse(
        request=request,
        name="optimize.html",
        context={"version": __version__, "page": "optimize"},
    )


@router.get("/measure", response_class=HTMLResponse)
async def measure_page(request: Request) -> HTMLResponse:
    """CWV 측정 페이지."""
    return templates.TemplateResponse(
        request=request,
        name="measure.html",
        context={"version": __version__, "page": "measure"},
    )


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request) -> HTMLResponse:
    """환경 설정 페이지."""
    import os

    config = {
        "wp_site_url": os.getenv("WP_SITE_URL", ""),
        "wp_user": os.getenv("WP_USER", ""),
        "wp_mock": os.getenv("WP_MOCK", "true"),
        "ollama_host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        "ollama_model": os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
        "db_path": os.getenv("DB_PATH", "./data/wp_auto.db"),
    }
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={"version": __version__, "page": "settings", "config": config},
    )


# === API 라우트 (JSON) ===

@router.get("/api/health")
async def health() -> dict:
    """헬스 체크."""
    return {
        "status": "ok",
        "version": __version__,
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/api/verify")
async def api_verify(
    html: str = Form(...),
    focus_keyword: str = Form(""),
    full: bool = Form(False),
) -> dict:
    """HTML + 키워드 → 점수 결과."""
    from wp_auto.core.content_score import SpecializedContentOptimizer
    from wp_auto.core.seo_analyzer import RankMathStyleAnalyzer

    optimizer = SpecializedContentOptimizer()
    content_result = optimizer.verify_html(html, focus_keyword=focus_keyword or None)

    response = {
        "content": {
            "total_score": content_result.total_score,
            "level": content_result.level.value,
            "category_scores": content_result.category_scores,
            "feedback": content_result.feedback,
            "recommendations": content_result.recommendations,
        }
    }

    if full and focus_keyword:
        seo_analyzer = RankMathStyleAnalyzer()
        seo_result = seo_analyzer.analyze(html, focus_keyword=focus_keyword)
        response["seo"] = {
            "total_score": seo_result.total_score,
            "category_scores": seo_result.category_scores,
            "items": [
                {
                    "name": i.name,
                    "passed": i.passed,
                    "points_earned": i.points_earned,
                    "points_max": i.points_max,
                }
                for i in seo_result.items
            ],
        }
        response["overall_recommendations"] = _merge_recs(
            content_result.recommendations, seo_result.recommendations
        )

    return response


@router.post("/api/generate")
async def api_generate(
    topic: str = Form(...),
    keyword: str = Form(...),
    intent: str = Form("informational"),
    length: int = Form(3000),
    tone: str = Form("친근한 전문가"),
    enable_images: bool = Form(False),
    max_images: int = Form(2),
) -> dict:
    """키워드 + 옵션 → AI 초안 (+ 선택: 상업용 무료 image 자동 embed)."""
    try:
        from wp_auto.ai.content_generator import ContentGenerator
        from wp_auto.ai.ollama_client import OllamaClient

        client = OllamaClient()
        if not client.is_available():
            return {
                "error": "Ollama 서버에 연결할 수 없습니다. `ollama serve` 실행 또는 https://ollama.com 설치 확인",
                "title": "",
                "html": "",
            }
        gen = ContentGenerator(client)  # 웹에서는 review는 generate_full_post에서 False로 지정
        post = gen.generate_full_post(
            topic=topic, keyword=keyword, intent=intent, length=length, tone=tone,
            enable_review=False,
        )
        html = post.html
        image_result: dict | None = None
        if enable_images:
            try:
                import os
                from pathlib import Path
                from wp_auto.image.pipeline import ImagePipeline
                assets_dir = Path("assets/images")
                pexels_key = os.environ.get("PEXELS_API_KEY")
                if not pexels_key:
                    logger.warning("PEXELS_API_KEY not set, skipping image pipeline")
                else:
                    pipe = ImagePipeline(
                        assets_dir=assets_dir,
                        pexels_api_key=pexels_key,
                    )
                    image_result = pipe.run(
                        draft_html=html,
                        keyword=keyword,
                        max_images=max_images,
                        use_infographic_fallback=True,
                        title=post.title,
                        subtitle=topic[:80],
                        aspect="16:9",
                    )
                    html = image_result["html"]
            except Exception as e:
                logger.error("image pipeline failed: {}", e)
                image_result = {"error": str(e)}
        return {
            "title": post.title,
            "meta_description": post.meta_description,
            "slug": post.slug,
            "html": html,
            "iterations": post.iterations,
            "images": (image_result or {}).get("images", []),
            "licenses": (image_result or {}).get("licenses", []),
            "infographic": (image_result or {}).get("infographic"),
        }
    except Exception as e:
        logger.error("api_generate failed: {}", e)
        return {"error": str(e), "title": "", "html": ""}


@router.post("/api/publish")
async def api_publish(
    html: str = Form(...),
    title: str = Form(""),
    focus_keyword: str = Form(""),
    status: str = Form("draft"),
    force: bool = Form(False),
) -> dict:
    """HTML → WP 발행."""
    from wp_auto.cli.publish import _extract_slug_from_html, _extract_title_from_html
    from wp_auto.core.content_score import (
        ContentQualityLevel,
        SpecializedContentOptimizer,
    )
    from wp_auto.wp.factory import get_wp_client

    # 1) 점수화 (게이트)
    optimizer = SpecializedContentOptimizer()
    result = optimizer.verify_html(html, focus_keyword=focus_keyword or None)
    if result.level == ContentQualityLevel.FAIL and not force and status != "draft":
        return {
            "error": f"점수 {result.total_score:.0f}/100 — 발행 차단 (--force 또는 --status draft)",
            "score": result.total_score,
            "recommendations": result.recommendations,
        }

    # 2) WP 발행
    final_title = title or _extract_title_from_html(html)
    slug = _extract_slug_from_html(html)
    client = get_wp_client()
    post_id = await client.create_draft(
        title=final_title, content=html, slug=slug, status="draft"
    )
    if status == "publish":
        await client.publish(post_id)
    return {"post_id": post_id, "title": final_title, "status": status, "score": result.total_score}


@router.post("/api/optimize")
async def api_optimize(
    file: UploadFile = File(...),  # noqa: B008
    max_width: int = Form(1200),  # noqa: B008
    format: str = Form("webp"),
) -> dict:
    """이미지 파일 → WebP/AVIF."""
    import tempfile

    from wp_auto.optimize.image_optimizer import ImageOptimizer

    # 임시 파일로 저장
    suffix = Path(file.filename or "image").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        opt = ImageOptimizer()
        result = opt.optimize(tmp_path, max_width=max_width, format=format)
        return {
            "src_size_kb": round(result.src_size_kb, 1),
            "dst_size_kb": round(result.dst_size_kb, 1),
            "reduction_pct": round(result.reduction_pct, 1),
            "width": result.width,
            "height": result.height,
            "format": result.format,
            "dst_path": str(result.dst_path),
        }
    finally:
        tmp_path.unlink(missing_ok=True)


@router.post("/api/measure")
async def api_measure(url: str = Form(...), runs: int = Form(3)) -> dict:
    """URL → CWV 측정 (Playwright 필요)."""
    try:
        from wp_auto.optimize.cwv_measurer import CWVMeasurer
        measurer = CWVMeasurer()
        result = await measurer.measure(url, runs=runs)
        return {
            "url": result.url,
            "lcp_ms": result.lcp_ms,
            "inp_ms": result.inp_ms,
            "cls": result.cls,
            "rating": result.rating,
            "recommendations": result.recommendations(),
        }
    except Exception as e:
        logger.error("api_measure failed: {}", e)
        return {"error": str(e)}


@router.get("/api/posts")
async def api_posts(status: str = "any", limit: int = 20) -> dict:
    """MockWP 글 목록."""
    from wp_auto.wp.factory import get_wp_client
    client = get_wp_client()
    posts = await client.list_posts(status=status, per_page=limit)
    return {
        "posts": [
            {
                "id": p.id,
                "title": p.title,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in posts
        ]
    }


# === 유틸 ===

def _wp_real() -> bool:
    """WP 모드가 Real인지 확인."""
    import os
    return bool(os.getenv("WP_SITE_URL", ""))


def _merge_recs(content_recs: list[str], seo_recs: list[str]) -> list[str]:
    """중복 제거 권고 합치기."""
    seen: set[str] = set()
    result: list[str] = []
    for r in (seo_recs or []) + (content_recs or []):
        key = r.strip()[:30]
        if key not in seen:
            seen.add(key)
            result.append(r)
    return result[:10]
