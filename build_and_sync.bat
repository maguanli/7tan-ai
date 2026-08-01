@echo off
setlocal enabledelayedexpansion
title 7Tan Build-Sync Tool

set ROOT=%~dp0
cd /d "%ROOT%"

echo ==========================================
echo   7Tan Build + Sync Tool (ASCII-safe v9)
echo ==========================================
echo.

REM ===== Step 0: Git auto backup =====
echo [0/4] Git auto backup...
if exist ".git" (
    git add -A
    git commit -m "auto-save: %date% %time%" >nul 2>&1
    echo   [OK] committed (or nothing to commit)
) else (
    echo   [SKIP] no git repo found
)
echo.

REM ===== Step 1: Build exe =====
echo [1/4] Building exe with PyInstaller...
call "%ROOT%.venv\Scripts\python.exe" -m PyInstaller build.spec --clean -y
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Build failed. Check output above.
    if /i not "%1"=="-y" pause
    exit /b 1
)
echo [1/4] Build OK
echo.

REM ===== Step 2: Sync source to dist\_build\src =====
REM Exclude: _source_backup (plaintext security src), __pycache__, .pytest_cache, *.pyc
echo [2/4] Syncing source to dist\_build\src...
if not exist "dist\_build\src" mkdir "dist\_build\src"
robocopy "src" "dist\_build\src" /E /XD _source_backup __pycache__ .pytest_cache /XF *.pyc /NFL /NDL /NJH /NJS /NP /R:2 /W:2
set ROBO_CODE=%ERRORLEVEL%
if %ROBO_CODE% GEQ 8 (
    echo [WARN] Source sync returned code %ROBO_CODE%, continuing...
) else (
    echo [2/4] Source synced OK
)
echo.

REM ===== Step 3: Sync build config files =====
echo [3/4] Syncing build config...
copy /Y build.spec dist\_build\build.spec >nul
copy /Y requirements.txt dist\_build\requirements.txt >nul
echo [3/4] Config synced
echo.

REM ===== Step 4: Verify artifacts =====
echo [4/4] Verifying artifacts...
set PYD_OK=1
for %%A in ("dist\7tan-editor\7tan-editor.exe") do set EXE_SIZE=%%~zA
if !EXE_SIZE! LSS 15000000 (
    echo [ERROR] exe size abnormal !EXE_SIZE! bytes, build incomplete!
    if /i not "%1"=="-y" pause
    exit /b 1
)
echo [OK] exe size check passed !EXE_SIZE! bytes
if not exist "dist\7tan-editor\_internal\src\security\rsa_verify.pyd" set PYD_OK=0
if not exist "dist\7tan-editor\_internal\src\security\license_verify.pyd" set PYD_OK=0
if not exist "dist\7tan-editor\_internal\src\security\safe_modify.pyd" set PYD_OK=0
if not exist "dist\7tan-editor\_internal\src\security\auth_client.pyd" set PYD_OK=0
if not exist "dist\7tan-editor\_internal\src\security\integrity.pyd" set PYD_OK=0
if not exist "dist\7tan-editor\_internal\src\security\token_store.pyd" set PYD_OK=0
if not exist "dist\7tan-editor\_internal\src\security\strings.pyd" set PYD_OK=0
if not exist "dist\7tan-editor\_internal\src\security\trial_store.pyd" set PYD_OK=0
if "!PYD_OK!"=="0" (
    echo [WARN] Missing some security .pyd in output, check build.spec hiddenimports
) else (
    echo [OK] Security modules 8/8 packaged
)

REM Remove plaintext backups accidentally synced into _build
if exist "dist\_build\src\security\_source_backup" (
    echo [WARN] Plaintext security source found in _build, removing...
    rmdir /S /Q "dist\_build\src\security\_source_backup"
)
if exist "dist\_build\src\security\__pycache__" (
    rmdir /S /Q "dist\_build\src\security\__pycache__"
)

REM Verify base_library.zip integrity
"%ROOT%.venv\Scripts\python.exe" -c "import zipfile,sys;z=zipfile.ZipFile(r'dist\7tan-editor\_internal\base_library.zip');sys.exit(0 if z.testzip() is None else 1)"
if %ERRORLEVEL% neq 0 (
    echo [ERROR] base_library.zip corrupted! exe will not start.
    if /i not "%1"=="-y" pause
    exit /b 1
) else (
    echo [OK] base_library.zip integrity passed
)
echo [4/4] Verification done
echo.

echo ==========================================
echo   DONE!
echo   exe:   dist\7tan-editor\7tan-editor.exe
echo   src:   dist\_build\src\
echo   spec:  dist\_build\build.spec
echo   reqs:  dist\_build\requirements.txt
echo ==========================================
if /i not "%1"=="-y" pause
