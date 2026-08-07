@echo off
REM ============================================================
REM Ollama server quick start (CPU-only mode for GTX 1050 2GB)
REM ============================================================
REM Usage: start-ollama.bat
REM
REM Use with start-wp-auto.bat:
REM   - Window 1: start-ollama.bat
REM   - Window 2: start-wp-auto.bat
REM
REM This .bat runs as a server — closing the window stops the server.
REM Stop Ollama: Ctrl+C
REM ============================================================

chcp 65001 >nul
setlocal

REM CPU-only mode (GTX 1050 2GB VRAM, 16GB RAM)
set OLLAMA_NUM_GPU=0
set CUDA_VISIBLE_DEVICES=-1
set OLLAMA_VULKAN=0
set OLLAMA_HOST=127.0.0.1:11434

ollama serve

REM Server stopped
pause
