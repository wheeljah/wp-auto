@echo off
REM ============================================================
REM Create 2 desktop shortcuts for Google_blog servers
REM ============================================================
REM Usage: make-shortcuts.bat
REM
REM Creates 2 .lnk files on your Desktop:
REM   - "Ollama Server (Google_blog).lnk"
REM   - "wp-auto UI (Google_blog).lnk"
REM
REM One-time setup. Re-run safely if shortcuts are missing.
REM ============================================================

chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0make-shortcuts.ps1" 2>&1
if (Test-Path "$env:USERPROFILE\Desktop\Ollama Server (Google_blog).lnk") {
    echo Desktop shortcuts already exist.
}
pause
