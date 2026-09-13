@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title 7Tan Build Tool v13 (dual package: Windows full + other-OS web)

set ROOT=%~dp0
cd /d "%ROOT%"

set "SKIP_PAUSE="
set "SKIP_BUILD="
set "WM_UID="
set "WM_VER="
set "WM_VER_SET="

:parse_args
if "%~1"=="" goto args_done
if /i "%~1"=="-y" ( set "SKIP_PAUSE=1" & shift & goto parse_args )
if /i "%~1"=="--no-build" ( set "SKIP_BUILD=1" & shift & goto parse_args )
if /i "%~1"=="-w" ( set "WM_UID=%~2" & shift & shift & goto parse_args )
if /i "%~1"=="-v" ( set "WM_VER=%~2" & set "WM_VER_SET=1" & shift & shift & goto parse_args )
shift
goto parse_args
:args_done

REM ===== Auto-detect version from src\config\version.py if -v not given =====
if not defined WM_VER_SET (
    if exist "src\config\version.py" (
        for /f "tokens=2 delims== " %%V in ('findstr /b /c:"APP_VERSION" "src\config\version.py"') do set "WM_VER=%%~V"
        set "WM_VER=!WM_VER: =!"
        echo [INFO] Version auto-detected from version.py: !WM_VER!
    )
)
if not defined WM_VER (
    echo [ERROR] Cannot determine version. Pass -v x.y.z or fix src\config\version.py
    if not defined SKIP_PAUSE pause
    exit /b 1
)

echo [INFO] Build version: %WM_VER%
echo ==========================================
echo   7Tan Build Tool v13 (dual package)
echo   [1] Windows full zip (exe + src)   [2] Other-OS web-only zip
echo ==========================================
echo.

REM ===== Step 0: Git auto backup =====
echo [0/4] Git auto backup...
if exist ".git" (
    git add -A
    git commit -m "auto-save: %date% %time%" >nul 2>&1
    echo   [OK] committed or nothing to commit
) else (
    echo   [SKIP] no git repo found
)
echo.

REM ===== Step 0.5: (removed 2026-09-13) plugin hash whitelist no longer used =====
REM Removed together with the whitelist check in src/plugins/manager.py.
echo.

REM ===== Step 0.9: Sanitize config (发布前脱敏，防 API Key 泄露) =====
echo [0.9/4] Sanitizing config secrets before build...
"%ROOT%.venv\Scripts\python.exe" tools\sanitize_config_for_build.py --apply
if errorlevel 1 (
    echo [ERROR] Sanitize failed! Abort to avoid leaking secrets.
    if not defined SKIP_PAUSE pause
    exit /b 1
)
echo [0.9/4] Sanitize OK
echo.

REM ===== Step 0.75: Clean old dist output (fix COLLECT not-empty failure) =====
echo [0.75/4] Cleaning old dist\7tan-editor...
if not defined SKIP_BUILD (
    if exist "dist\7tan-editor" (
        rmdir /s /q "dist\7tan-editor"
        if exist "dist\7tan-editor" (
            echo [WARN] dist\7tan-editor is still locked, retry in 3s...
            timeout /t 3 /nobreak >nul
            rmdir /s /q "dist\7tan-editor"
        )
        if exist "dist\7tan-editor" (
            echo [ERROR] dist\7tan-editor still locked. Close 7Tan / explorer, or whitelist project dir in antivirus.
            if not defined SKIP_PAUSE pause
            exit /b 1
        )
    )
    echo [0.75/4] Clean OK
) else (
    echo [0.75/4] SKIP clean (--no-build mode)
)
echo.

REM ===== Step 1: Build exe =====
if defined SKIP_BUILD (
    echo [1/4] SKIP build --no-build mode
) else (
    echo [1/4] Building exe with PyInstaller...
    call "%ROOT%.venv\Scripts\python.exe" -m PyInstaller build.spec --clean -y
    if errorlevel 1 (
        echo.
        echo [ERROR] Build failed. Check output above.
        "%ROOT%.venv\Scripts\python.exe" tools\sanitize_config_for_build.py --restore >nul 2>&1
        if not defined SKIP_PAUSE pause
        exit /b 1
    )
    echo [1/4] Build OK
)
echo.

REM ===== Step 2: Verify build output =====
echo [2/4] Verifying artifacts...
set EXE_SIZE=0
if exist "dist\7tan-editor\7tan-editor.exe" for %%A in ("dist\7tan-editor\7tan-editor.exe") do set EXE_SIZE=%%~zA
if "%EXE_SIZE%"=="0" (
    echo [ERROR] dist\7tan-editor\7tan-editor.exe not found! Please build first or check --no-build precondition.
    if not defined SKIP_PAUSE pause
    exit /b 1
)
if %EXE_SIZE% LSS 15000000 (
    echo [ERROR] exe size abnormal %EXE_SIZE% bytes, build incomplete!
    if not defined SKIP_PAUSE pause
    exit /b 1
)
echo [OK] exe size check passed %EXE_SIZE% bytes
set PYD_OK=1
if not exist "dist\7tan-editor\_internal\src\security\rsa_verify.pyd" set PYD_OK=0
if not exist "dist\7tan-editor\_internal\src\security\license_verify.pyd" set PYD_OK=0
if not exist "dist\7tan-editor\_internal\src\security\safe_modify.pyd" set PYD_OK=0
if not exist "dist\7tan-editor\_internal\src\security\auth_client.pyd" set PYD_OK=0
if not exist "dist\7tan-editor\_internal\src\security\integrity.pyd" set PYD_OK=0
if not exist "dist\7tan-editor\_internal\src\security\token_store.pyd" set PYD_OK=0
if "!PYD_OK!"=="0" (
    echo [ERROR] Security .pyd modules missing in _internal!
    if not defined SKIP_PAUSE pause
    exit /b 1
)
echo [OK] security pyd modules present
echo [2/4] Verification done
echo.

REM ===== Step 3: Package release zip =====
REM 旧 zip 不再预先 del：package_release.py 用临时包+原子替换覆盖，天然防占用冲突
echo [3/4] Packaging Windows release zip (full exe package)...
if not exist "dist\release" mkdir "dist\release"
"%ROOT%.venv\Scripts\python.exe" "templates\package_release.py" --uid "%WM_UID%" --version "%WM_VER%" --out "dist\release" --free-dir "dist\7tan-editor"
if errorlevel 2 (
    echo.
    echo [ERROR] Release packaging failed: file locked / antivirus scanning.
    "%ROOT%.venv\Scripts\python.exe" tools\sanitize_config_for_build.py --restore >nul 2>&1
    echo         Close opened zip in dist\release, or whitelist dist in antivirus, then retry.
    if not defined SKIP_PAUSE pause
    exit /b 2
)
if errorlevel 1 (
    echo.
    echo [ERROR] Release packaging failed. Check log above for details.
    "%ROOT%.venv\Scripts\python.exe" tools\sanitize_config_for_build.py --restore >nul 2>&1
    if not defined SKIP_PAUSE pause
    exit /b 1
)
echo [3/4] Windows release zip generated in dist\release
echo.

REM ===== Step 4: Package other-OS web-only zip =====
echo [4/4] Packaging other-OS web-only zip (macOS/Linux/Harmony)...
"%ROOT%.venv\Scripts\python.exe" "templates\package_release.py" --web-only --uid "%WM_UID%" --version "%WM_VER%" --out "dist\release"
if errorlevel 2 (
    echo.
    echo [ERROR] Web-only packaging failed: file locked / antivirus scanning.
    "%ROOT%.venv\Scripts\python.exe" tools\sanitize_config_for_build.py --restore >nul 2>&1
    echo         Close opened zip in dist\release, or whitelist dist in antivirus, then retry.
    if not defined SKIP_PAUSE pause
    exit /b 2
)
if errorlevel 1 (
    echo.
    echo [ERROR] Web-only packaging failed. Check log above for details.
    "%ROOT%.venv\Scripts\python.exe" tools\sanitize_config_for_build.py --restore >nul 2>&1
    if not defined SKIP_PAUSE pause
    exit /b 1
)
echo [4/4] Other-OS web-only zip generated in dist\release
echo.

REM ===== Step 5: Restore local real config + scan release zip for secrets =====
echo [5/4] Restoring local real config...
"%ROOT%.venv\Scripts\python.exe" tools\sanitize_config_for_build.py --restore
echo [5/4] Scanning release zips for secrets...
"%ROOT%.venv\Scripts\python.exe" check_zip_secrets.py
if errorlevel 1 (
    echo [WARN] ⚠️ Release zip contains secrets! Do NOT distribute this build. Fix config and rebuild.
)
echo [5/4] Secret scan done (see output above)
echo.

echo ==========================================
echo   DONE! two packages ready:
echo   [1] Windows: dist\release\7tan-editor-v%WM_VER%.zip
echo   [2] Other-OS: dist\release\7tan-web-v%WM_VER%.zip
echo ==========================================
if not defined SKIP_PAUSE pause
