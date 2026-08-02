@echo off
REM ============================================================
REM wp-auto Web UI 빠른 시작
REM ============================================================
REM 사용법: start-wp-auto.bat [포트]
REM 예:     start-wp-auto.bat       (8765 또는 WP_AUTO_PORT)
REM         start-wp-auto.bat 7777  (특정 포트)
REM
REM 이 .bat은 서버로 동작 — 창을 닫으면 서버도 종료.
REM 백그라운드 시작은 wpu 별칭 (PowerShell profile) 참고.
REM ============================================================

chcp 65001 >nul
setlocal
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

cd /d %~dp0\wp-auto

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [ERROR] venv 없음. 먼저 실행: D:\Google_blog\setup-wp-auto.bat
    echo.
    pause
    exit /b 1
)

REM 포트 결정
if not "%1"=="" (
    set WP_PORT=%1
) else if not "%WP_AUTO_PORT%"=="" (
    set WP_PORT=%WP_AUTO_PORT%
) else (
    set WP_PORT=8765
)

echo.
echo  wp-auto Web UI: http://127.0.0.1:%WP_PORT%
echo  종료: Ctrl+C
echo.

call ".venv\Scripts\activate.bat"
python -m wp_auto ui --port %WP_PORT%

REM 서버 종료 후
echo.
echo  서버 종료됨.
pause
