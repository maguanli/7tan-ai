@echo off
cd /d "%~dp0"

echo ===== 1. START =====

python -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>&1
if errorlevel 1 (
    echo ===== 2. NO PYTHON =====
    pause
    exit /b 1
)
echo ===== 2. PYTHON OK =====
python --version

if not exist ".venv\Scripts\python.exe" (
    echo ===== 3. CREATING VENV =====
    python -m venv .venv
    if errorlevel 1 (
        echo VENV FAILED
        pause
        exit /b 1
    )
) else (
    echo ===== 3. VENV EXISTS =====
)

echo ===== 4. ACTIVATING =====
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ACTIVATE FAILED
    pause
    exit /b 1
)

echo ===== 5. PIP INSTALL =====
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo PIP FAILED
    pause
    exit /b 1
)

echo ===== 6. PLAYWRIGHT =====
python -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(); b.close(); p.stop()" >nul 2>&1
if errorlevel 1 (
    echo Installing Chromium...
    python -m playwright install chromium
)

echo ===== 7. LAUNCH =====
echo 按 Ctrl+C 停止服务
python main.py
exit /b 0
