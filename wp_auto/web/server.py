"""FastAPI 서버: `wp-auto ui` 로 시작.

기본: http://localhost:8765

사용법:
    wp-auto ui                    # 기본 포트 8765
    wp-auto ui --port 7777        # 다른 포트
    wp-auto ui --reload           # 개발 모드 (auto-reload)
"""

from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from loguru import logger

from wp_auto import __version__

# 경로
WEB_DIR = Path(__file__).parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"


def create_app() -> FastAPI:
    """FastAPI app factory."""
    app = FastAPI(
        title="wp-auto",
        description="워드프레스 블로그 자동화 도구 (1인 self-use)",
        version=__version__,
    )

    # 정적 파일
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # 라우트 등록 (lazy import)
    from wp_auto.web.routes import router

    app.include_router(router)

    return app


# 모듈 레벨 app (uvicorn 진입점)
app = create_app()


def run_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    reload: bool = False,
) -> None:
    """서버 실행."""
    logger.info("Starting wp-auto UI: http://{}:{}", host, port)
    print(f"\n  wp-auto UI ready: http://{host}:{port}")
    print("  종료: Ctrl+C\n")
    uvicorn.run(
        "wp_auto.web.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


__all__ = ["app", "create_app", "run_server"]
