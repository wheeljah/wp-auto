"""WordPress 클라이언트 팩토리 — 환경변수 기반 Mock/Real 자동 라우팅.

도구 우선 빌드 패턴: WP_SITE_URL 비어있거나 WP_MOCK=true 면 MockWordPressClient.
실 WP 사이트 세팅 후 .env에 WP_SITE_URL + WP_USER + WP_APP_PASSWORD 추가.
"""

from __future__ import annotations

import os
from pathlib import Path

from loguru import logger

from wp_auto.wp.client import WordPressClient
from wp_auto.wp.mock_client import MockWordPressClient
from wp_auto.wp.real_client import RealWordPressClient


def get_wp_client(
    site_url: str | None = None,
    user: str | None = None,
    app_password: str | None = None,
    mock: bool | None = None,
    db_path: Path | None = None,
) -> WordPressClient:
    """환경변수 또는 인자로 WP 클라이언트 생성.

    우선순위:
        1. 명시적 인자
        2. 환경변수 (WP_SITE_URL, WP_USER, WP_APP_PASSWORD, WP_MOCK)
        3. 기본값 (Mock 모드)

    사용법:
        # 환경변수 기반 (권장)
        client = get_wp_client()

        # 명시적 Mock
        client = get_wp_client(mock=True, db_path=Path("./data/wp.db"))

        # 명시적 Real
        client = get_wp_client(
            site_url="https://example.com",
            user="admin",
            app_password="xxxx xxxx xxxx xxxx xxxx xxxx",
        )
    """
    site_url = site_url or os.getenv("WP_SITE_URL", "")
    user = user or os.getenv("WP_USER", "")
    app_password = app_password or os.getenv("WP_APP_PASSWORD", "")

    if mock is None:
        mock_env = os.getenv("WP_MOCK", "true").lower()
        mock = mock_env in ("true", "1", "yes")

    if db_path is None:
        db_env = os.getenv("DB_PATH", "")
        if db_env:
            db_path = Path(db_env)

    if mock or not site_url:
        logger.info(
            "Using MockWordPressClient (WP_MOCK={}, site_url={}, db_path={})",
            mock, site_url or "(empty)", db_path or "(in-memory)",
        )
        return MockWordPressClient(db_path=db_path)

    logger.info("Using RealWordPressClient: site={}", site_url)
    return RealWordPressClient(
        site_url=site_url,
        user=user,
        app_password=app_password,
    )


__all__ = ["get_wp_client"]
