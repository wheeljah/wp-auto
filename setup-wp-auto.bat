@echo off
REM ============================================================
REM wp-auto 1회 셋업 (최초 1회만 실행)
REM ============================================================
REM 실행 내용:
REM   1. Python venv 생성
REM   2. 의존성 설치 (Phase 1~4 전체)
REM   3. Ollama 확인 + qwen2.5:7b 다운로드 (4.7GB)
REM   4. Playwright Chromium 설치 (선택, ~200MB)
REM   5. .env.example -> .env 복사
REM   6. pytest로 검증
REM ============================================================

chcp 65001 >nul
setlocal
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

cd /d %~dp0\wp-auto

if not exist "pyproject.toml" (
    echo.
    echo [ERROR] wp-auto 폴더를 찾을 수 없습니다.
    echo 예상 위치: %~dp0wp-auto
    echo.
    pause
    exit /b 1
)

echo ============================================================
echo  Step 1/6: Python venv 확인
echo ============================================================
if not exist ".venv\Scripts\python.exe" (
    echo venv 생성 중...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] venv 생성 실패
        pause
        exit /b 1
    )
    echo [OK] venv 생성 완료
) else (
    echo [OK] venv 이미 존재
)

echo.
echo ============================================================
echo  Step 2/6: 의존성 설치
echo ============================================================
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip --quiet
pip install -e ".[dev]" --quiet
if errorlevel 1 (
    echo [ERROR] 기본 의존성 설치 실패
    pause
    exit /b 1
)
echo [OK] 기본 의존성 설치 완료

echo 추가 의존성 (Ollama, FastAPI, Playwright, Pillow)...
pip install ollama httpx pillow playwright python-frontmatter fastapi "uvicorn[standard]" jinja2 python-multipart --quiet
if errorlevel 1 (
    echo [ERROR] 추가 의존성 설치 실패
    pause
    exit /b 1
)
echo [OK] 추가 의존성 설치 완료

echo.
echo ============================================================
echo  Step 3/6: Ollama 확인
echo ============================================================
where ollama >nul 2>&1
if errorlevel 1 (
    echo [WARN] Ollama 미설치.
    echo        설치: https://ollama.com/download
    echo        또는: winget install Ollama.Ollama
    set OLLAMA_MISSING=1
) else (
    echo [OK] Ollama 설치됨
    ollama --version
)

if not "%OLLAMA_MISSING%"=="1" (
    echo.
    echo qwen2.5:7b 다운로드 (4.7GB)...
    ollama pull qwen2.5:7b
    if errorlevel 1 (
        echo [WARN] pull 실패. 나중에: ollama pull qwen2.5:7b
    ) else (
        echo [OK] qwen2.5:7b 준비 완료
    )
)

echo.
echo ============================================================
echo  Step 4/6: Playwright Chromium
echo ============================================================
playwright install chromium
if errorlevel 1 (
    echo [WARN] Chromium 다운로드 실패. CWV 측정 시 수동 재시도.
) else (
    echo [OK] Chromium 설치 완료
)

echo.
echo ============================================================
echo  Step 5/6: .env 설정
echo ============================================================
if not exist ".env" (
    if exist ".env.example" (
        copy /Y ".env.example" ".env" >nul
        echo [OK] .env.example -> .env 복사
    )
) else (
    echo [OK] .env 이미 존재
)

echo.
echo ============================================================
echo  Step 6/6: 테스트 실행
echo ============================================================
python -m pytest -q
if errorlevel 1 (
    echo [WARN] 일부 테스트 실패 (코드 참고)
)

echo.
echo ============================================================
echo  SETUP 완료
echo ============================================================
echo.
echo  다음: D:\Google_blog\wp-auto\wp-auto.cmd 더블클릭
echo        또는 어디서든 'wpu' (PowerShell)
echo.
pause
exit /b 0
