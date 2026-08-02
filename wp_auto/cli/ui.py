"""`wp-auto ui` 명령: FastAPI 로컬 서버 시작.

사용법:
    wp-auto ui                    # 기본 http://127.0.0.1:8765
    wp-auto ui --port 7777        # 다른 포트
    wp-auto ui --host 0.0.0.0     # 외부 접근 (비추, 인증 없음)
    wp-auto ui --reload           # 개발 모드 (auto-reload)
"""

from __future__ import annotations

import click


@click.command()
@click.option("--host", default="127.0.0.1", help="바인드 호스트 (기본: 127.0.0.1 = localhost only)")
@click.option("--port", type=int, default=8765, help="포트 (기본 8765, 환경변수 WP_AUTO_PORT)")
@click.option("--reload", is_flag=True, help="개발 모드 (파일 변경 시 자동 재시작)")
def ui(host: str, port: int, reload: bool) -> None:
    """FastAPI 로컬 웹 UI 시작 (1인 self-use)."""
    import os

    from wp_auto.web.server import run_server

    # 환경변수 오버라이드
    env_port = os.getenv("WP_AUTO_PORT")
    if env_port:
        try:
            port = int(env_port)
        except ValueError:
            pass

    run_server(host=host, port=port, reload=reload)


__all__ = ["ui"]
