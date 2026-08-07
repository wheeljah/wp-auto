@echo off
REM ============================================================
REM wp-auto Web UI quick start
REM ============================================================
REM Usage: start-wp-auto.bat [port]
REM Example: start-wp-auto.bat       (default 8765 or WP_AUTO_PORT env)
REM          start-wp-auto.bat 7777  (specific port)
REM
REM This .bat runs as a server — closing the window stops the server.
REM Stop: Ctrl+C
REM ============================================================

chcp 65001 >nul
setlocal
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

REM bat is in D:\Google_blog\wp-auto\. Use that as cwd.
cd /d %~dp0

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [ERROR] venv not found. Run D:\Google_blog\setup-wp-auto.bat first.
    echo.
    pause
    exit /b 1
)

REM Port decision
if not "%1"=="" (
    set WP_PORT=%1
) else if not "%WP_AUTO_PORT%"=="" (
    set WP_PORT=%WP_AUTO_PORT%
) else (
    set WP_PORT=8765
)

call ".venv\Scripts\activate.bat"
python -m wp_auto ui --port %WP_PORT%

REM Server stopped
pause
