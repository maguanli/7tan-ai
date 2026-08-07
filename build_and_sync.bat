@echo off
setlocal enabledelayedexpansion
title 7Tan Build-Sync Tool v10

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
echo   7Tan Build + Sync Tool (v11)
echo   Full pipeline: build + sync portable dist
echo ==========================================
echo.

REM ===== Step 0: Git auto backup =====
echo [0/6] Git auto backup...
if exist ".git" (
    git add -A
    git commit -m "auto-save: %date% %time%" >nul 2>&1
    echo   [OK] committed or nothing to commit
) else (
    echo   [SKIP] no git repo found
)
echo.

REM ===== Step 0.5: Regenerate plugin SHA-256 whitelist =====
echo [0.5/6] Regenerating plugin whitelist (SHA-256 + HMAC)...
if exist "tools\gen_plugin_hashes.py" (
    ".venv\Scripts\python.exe" tools\gen_plugin_hashes.py
    if errorlevel 1 (
        echo [WARN] Plugin whitelist regeneration failed, continuing with existing hashes.json
    ) else (
        echo [0.5/6] Plugin whitelist OK
    )
) else (
    echo [SKIP] gen_plugin_hashes.py not found
)
echo.

REM ===== Step 1: Build exe =====
if defined SKIP_BUILD (
    echo [1/6] SKIP build --no-build mode
) else (
    echo [1/6] Building exe with PyInstaller...
    call "%ROOT%.venv\Scripts\python.exe" -m PyInstaller build.spec --clean -y
    if errorlevel 1 (
        echo.
        echo [ERROR] Build failed. Check output above.
        if not defined SKIP_PAUSE pause
        exit /b 1
    )
    echo [1/6] Build OK
)
echo.

REM ===== Step 2: Sync source to dist\_build\src =====
echo [2/6] Syncing source to dist\_build\src...
if not exist "dist\_build\src" mkdir "dist\_build\src"
robocopy "src" "dist\_build\src" /E /XD _source_backup __pycache__ .pytest_cache /XF *.pyc /NFL /NDL /NJH /NJS /NP /R:2 /W:2
set ROBO_CODE=%ERRORLEVEL%
if %ROBO_CODE% GEQ 8 (
    echo [WARN] Source sync returned code %ROBO_CODE%, continuing...
) else (
    echo [2/6] Source synced OK
)
echo.

REM ===== Step 2.5: Sync main.py + config + data to _build =====
copy /Y main.py dist\_build\main.py >nul
robocopy "config" "dist\_build\config" /E /XD __pycache__ /XF *.pyc /NFL /NDL /NJH /NJS /NP /R:2 /W:2 >nul
robocopy "data" "dist\_build\data" /E /XD __pycache__ /XF *.pyc /NFL /NDL /NJH /NJS /NP /R:2 /W:2 >nul
echo [2.5/6] main.py + config + data synced
echo.

REM ===== Step 3: Sync build config files =====
echo [3/6] Syncing build config...
copy /Y build.spec dist\_build\build.spec >nul
copy /Y requirements.txt dist\_build\requirements.txt >nul
echo [3/6] Config synced
echo.

REM ===== Step 4: Sync / create portable python (dist\_python) =====
echo [4/6] Syncing portable python to dist\_python...
set "BASE_PY=C:\Program Files\Python312"
if exist "dist\_python\python.exe" (
    echo   _python exists - incremental sync site-packages + Scripts...
    robocopy ".venv\Lib\site-packages" "dist\_python\Lib\site-packages" /MIR /XD __pycache__ /XF *.pyc /NFL /NDL /NJH /NJS /NP /R:2 /W:2 >nul
    robocopy ".venv\Scripts" "dist\_python\Scripts" /MIR /XD __pycache__ /NFL /NDL /NJH /NJS /NP /R:2 /W:2 >nul
    echo   [OK] _python updated
) else (
    echo   _python missing - creating full portable python from %BASE_PY%...
    if not exist "%BASE_PY%\python.exe" (
        echo.
        echo [ERROR] Base python not found: %BASE_PY%
        echo         Cannot create _python automatically.
        echo         Options: install Python 3.12 64-bit, or copy
        echo         dist\_python from another machine.
        if not defined SKIP_PAUSE pause
        exit /b 1
    )
    robocopy "%BASE_PY%" "dist\_python" /E /XD Doc /XF *.pyc /NFL /NDL /NJH /NJS /NP /R:2 /W:2 >nul
    robocopy ".venv\Lib\site-packages" "dist\_python\Lib\site-packages" /MIR /XD __pycache__ /XF *.pyc /NFL /NDL /NJH /NJS /NP /R:2 /W:2 >nul
    robocopy ".venv\Scripts" "dist\_python\Scripts" /MIR /XD __pycache__ /NFL /NDL /NJH /NJS /NP /R:2 /W:2 >nul
    if exist "dist\_python\pyvenv.cfg" del /q "dist\_python\pyvenv.cfg"
    echo   [OK] _python created
)
REM ===== Step 4.5: Slim _python (remove heavy unused libs) =====
echo [4.5/6] Slimming _python (removing unused heavy libs)...
if exist "dist\_python\Lib\site-packages" (
    for %%P in (torch torchvision torchaudio torchtext playwright cv2 ddddocr ctranslate2 winsdk winrt moviepy pydub av speech_recognition selenium faster_whisper whisper) do (
        if exist "dist\_python\Lib\site-packages\%%P" (
            echo   [DEL] %%P
            rmdir /S /Q "dist\_python\Lib\site-packages\%%P"
        )
        if exist "dist\_python\Lib\site-packages\%%P-*.dist-info" (
            for /D %%D in ("dist\_python\Lib\site-packages\%%P-*.dist-info") do (
                echo   [DEL] %%~nxD
                rmdir /S /Q "%%D"
            )
        )
    )
    echo   [OK] _python slimmed
) else (
    echo   [SKIP] site-packages not found
)
echo.

"dist\_python\python.exe" -c "import sys, PyInstaller, PyQt6; print('   _python OK:', sys.version.split()[0], '| PyInstaller', PyInstaller.__version__)"
if errorlevel 1 (
    echo [ERROR] _python verification failed.
    if not defined SKIP_PAUSE pause
    exit /b 1
)
echo.

REM ===== Step 5: Generate dist\rebuild.bat =====
echo [5/6] Generating dist\rebuild.bat...
if exist "templates\rebuild.bat" (
    copy /Y "templates\rebuild.bat" "dist\rebuild.bat" >nul
    echo   [OK] dist\rebuild.bat generated from template
) else (
    echo   [WARN] templates\rebuild.bat not found - keeping existing dist\rebuild.bat
)
echo.

REM ===== Step 6: Verify build output + self-contained dist =====
echo [6/6] Verifying artifacts...
set PYD_OK=1
for %%A in ("dist\7tan-editor\7tan-editor.exe") do set EXE_SIZE=%%~zA
if not defined EXE_SIZE set EXE_SIZE=0
if %EXE_SIZE% LSS 15000000 (
    echo [ERROR] exe size abnormal %EXE_SIZE% bytes, build incomplete!
    if not defined SKIP_PAUSE pause
    exit /b 1
)
echo [OK] exe size check passed %EXE_SIZE% bytes
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
if errorlevel 1 (
    echo [ERROR] base_library.zip corrupted! exe will not start.
    if not defined SKIP_PAUSE pause
    exit /b 1
) else (
    echo [OK] base_library.zip integrity passed
)

REM Self-contained check
echo.
echo   Self-contained check...
set MISSING=0
if not exist "dist\_python\python.exe" (
    echo   [MISS] _python\python.exe
    set MISSING=1
)
if not exist "dist\_python\Scripts\pyinstaller.exe" (
    echo   [MISS] _python\Scripts\pyinstaller.exe
    set MISSING=1
)
if not exist "dist\_build\main.py" (
    echo   [MISS] _build\main.py
    set MISSING=1
)
if not exist "dist\_build\build.spec" (
    echo   [MISS] _build\build.spec
    set MISSING=1
)
if not exist "dist\rebuild.bat" (
    echo   [MISS] rebuild.bat
    set MISSING=1
)
if not exist "dist\7tan-editor\7tan-editor.exe" (
    echo   [MISS] 7tan-editor.exe
    set MISSING=1
)
if "!MISSING!"=="1" (
    echo [ERROR] dist is NOT self-contained. See missing items above.
    if not defined SKIP_PAUSE pause
    exit /b 1
)
echo [OK] dist is fully self-contained
echo [6/6] Verification done
echo.

REM ===== Step 7: Package release zips (free + pro + update) =====
echo [7/7] Packaging release zips (free + pro + update)...

if not exist "dist\release" mkdir "dist\release"

echo   [CLEAN] Removing old zips from dist\release...

del /Q "dist\release\*.zip" 2>nul
"%ROOT%.venv\Scripts\python.exe" "templates\package_release.py" --uid "%WM_UID%" --version "%WM_VER%" --out "dist\release" --free-dir "dist\7tan-editor" --pro-build "dist\_build" --pro-python "dist\_python" --rebuild "dist\rebuild.bat" --license "templates\LICENSE.txt"
if errorlevel 1 (
    echo.
    echo [ERROR] Release packaging failed.
    if not defined SKIP_PAUSE pause
    exit /b 1
)
echo [7/7] Release zips generated in dist\release
echo.

echo ==========================================
echo   DONE! dist is now fully self-contained:
echo   - 7tan-editor\7tan-editor.exe
echo   - _build\
echo   - _python\
echo   - rebuild.bat
echo.
echo   Copy the whole dist folder to any
echo   Win10/11 x64 PC and double-click
echo   rebuild.bat to rebuild offline.
echo ==========================================
if not defined SKIP_PAUSE pause
