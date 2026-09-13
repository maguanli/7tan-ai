@echo off
setlocal enabledelayedexpansion
title 7Tan-Pro Self Build Tool v11

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "PY=%ROOT%\_python\python.exe"
set "SPEC=%ROOT%\_build\build.spec"
set "OUT=%ROOT%\7tan-editor"
set "BACKUP=%ROOT%\7tan-editor_backup_latest"
set "TMPW=%ROOT%\_build_tmp"

echo ============================================
echo   7Tan Pro - Self Build Tool v11
echo   Portable: Python + deps + source all inside
echo   Root: %ROOT%
echo ============================================
echo.

if not exist "%PY%" (
  echo [ERROR] Portable python not found: %PY%
  echo         dist folder is incomplete.
  exit /b 1
)
if not exist "%ROOT%\_python\Scripts\pyinstaller.exe" (
  echo [ERROR] PyInstaller not found in portable python.
  echo         Run build_and_sync.bat on the dev machine first.
  exit /b 1
)
if not exist "%SPEC%" (
  echo [ERROR] build.spec not found: %SPEC%
  exit /b 1
)
if not exist "%ROOT%\_build\main.py" (
  echo [ERROR] main.py not found in _build. Source incomplete.
  exit /b 1
)

REM ===== Step 0.5: Verify Pro watermark (dev mode allows FREE build) =====
set "BI=%ROOT%\_build\src\config\build_info.py"
if not exist "%BI%" (
  echo [ERROR] build_info.py not found. Not a valid Pro source package.
  exit /b 1
)
set "DEV_ALLOW=0"
if /i "%~1"=="--dev" set "DEV_ALLOW=1"
if exist "%ROOT%\_build\.DEV_BUILD" set "DEV_ALLOW=1"
findstr /C:"PRO-" "%BI%" >nul
if errorlevel 1 (
  if "!DEV_ALLOW!"=="1" (
    echo [WARN] FREE watermark detected. Dev mode ON - building FREE version.
  ) else (
    echo [ERROR] Watermark missing or invalid. This is a FREE package, Pro license required.
    echo         Developer? Run:  rebuild.bat --dev
    echo         Or create file: _build\.DEV_BUILD
    exit /b 1
  )
) else (
  echo   [OK] Pro watermark verified
)
echo.

echo [1/5] Backup current build...
if exist "%OUT%" (
  if exist "%BACKUP%" rmdir /s /q "%BACKUP%"
  robocopy "%OUT%" "%BACKUP%" /E /NFL /NDL /NJH /NJS /R:2 /W:2 >nul
  echo   backed up to %BACKUP%
) else (
  echo   no existing build, skip backup
)
echo.

echo [2/5] Verify portable python...
"%PY%" -c "import sys, PyInstaller, PyQt6; print('  Python', sys.version.split()[0], '| PyInstaller', PyInstaller.__version__)"
if errorlevel 1 (
  echo [ERROR] Portable python is broken.
  exit /b 1
)
echo.

echo [3/5] PyInstaller build (5-15 min)...
"%PY%" -m PyInstaller --noconfirm --distpath "%ROOT%" --workpath "%TMPW%" "%SPEC%"
if errorlevel 1 (
  echo [ERROR] Build failed. Restoring previous build...
  if exist "%BACKUP%" (
    if exist "%OUT%" rmdir /s /q "%OUT%"
    robocopy "%BACKUP%" "%OUT%" /E /NFL /NDL /NJH /NJS /R:2 /W:2 >nul
    echo   previous build restored.
  )
  exit /b 1
)
echo.

echo [4/5] Verify output...
set "EXE=%OUT%\7tan-editor.exe"
if not exist "%EXE%" (
  echo [ERROR] exe not found after build: %EXE%
  exit /b 1
)
for %%F in ("%EXE%") do set "SIZE=%%~zF"
echo   exe size: %SIZE% bytes
if %SIZE% LSS 15000000 (
  echo [ERROR] exe too small, build is suspicious.
  exit /b 1
)
echo.

echo [5/5] Cleanup temp work dir...
if exist "%TMPW%" rmdir /s /q "%TMPW%"

echo.
echo ============================================
echo   BUILD SUCCESS
echo   Output: %EXE%
echo ============================================
exit /b 0
