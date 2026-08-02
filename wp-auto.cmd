@echo off
REM ============================================================
REM wp-auto launcher (Windows)
REM ============================================================
REM Usage (cmd or double-click):
REM   wp-auto doctor
REM   wp-auto verify file.html -k "keyword"
REM   wp-auto publish file.html --status publish
REM   wp-auto ui --port 8765
REM
REM Run 'wp-auto --help' for full options.
REM ============================================================

chcp 65001 >nul
setlocal

REM Python output UTF-8 (prevents hangul garbling in cp949 terminals)
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

cd /d %~dp0

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [ERROR] .venv not found. Run setup first:
    echo.
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -e ".[dev]"
    echo   pip install ollama httpx pillow playwright fastapi uvicorn jinja2 python-multipart
    echo.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] venv activation failed
    pause
    exit /b 1
)

REM 인자 없으면 기본 명령 = 'ui' (1인 self-use 메인 진입점)
if "%1"=="" (
    python -m wp_auto ui
) else (
    python -m wp_auto %*
)
set EXITCODE=%errorlevel%

REM 'ui' runs a long-lived server (no pause). Other commands show output then pause.
if /i not "%1"=="ui" (
    if not "%1"=="" pause
)

exit /b %EXITCODE%
