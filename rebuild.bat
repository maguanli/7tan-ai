@echo off
chcp 65001 >nul
setlocal
REM ============================================
REM   7Tan Pro - Root rebuild.bat (redirect)
REM   Build chain lives in dist\ (embedded python + sources)
REM ============================================

cd /d "%~dp0"

REM Locate the Pro build package (dist directory contains _python & _build)
set "DIST_DIR=%~dp0dist"
if not exist "%DIST_DIR%\_python\python.exe" (
    echo [ERROR] dist\_python\python.exe not found under %DIST_DIR%
    echo Please make sure the full Pro package exists at: %DIST_DIR%
    pause
    exit /b 1
)
if not exist "%DIST_DIR%\_build\main.py" (
    echo [ERROR] dist\_build\main.py not found. Build source missing.
    pause
    exit /b 1
)

echo [OK] Found Pro build package: %DIST_DIR%
echo [OK] Handing over to dist\rebuild.bat ...
echo.

cd /d "%DIST_DIR%"
call rebuild.bat
exit /b %errorlevel%
