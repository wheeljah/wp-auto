@echo off
REM ============================================================
REM Start both servers (Ollama + wp-auto UI) in separate windows
REM ============================================================
REM Usage: start-both.bat
REM
REM This .bat launches 2 separate cmd windows:
REM   1. Ollama server (qwen2.5:7b, CPU-only mode)
REM   2. wp-auto Web UI (FastAPI, port 8767)
REM
REM Stop: Close each window (or Ctrl+C inside)
REM
REM Companion files:
REM   - start-ollama.bat: just Ollama
REM   - start-wp-auto.bat: just wp-auto UI
REM   - make-shortcuts.ps1: create 2 desktop .lnk files
REM ============================================================

chcp 65001 >nul

REM Open Ollama server in new window
start "Ollama Server (Google_blog)" cmd /k "cd /d %~dp0\wp_auto && set OLLAMA_NUM_GPU=0 && set CUDA_VISIBLE_DEVICES=-1 && set OLLAMA_VULKAN=0 && ollama serve"

REM Open wp-auto UI in new window
start "wp-auto UI (Google_blog)" cmd /k "cd /d %~dp0\wp_auto && set PYTHONIOENCODING=utf-8 && set WP_MOCK=true && .venv\Scripts\python.exe -m wp_auto ui --port 8767"

echo.
echo  Both servers launched in separate windows.
echo  Ollama:    http://127.0.0.1:11434
echo  wp-auto UI: http://127.0.0.1:8767
echo.
echo  Close each window to stop, or Ctrl+C inside.
echo.
pause
