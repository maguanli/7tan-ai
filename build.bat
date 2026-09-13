@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ================================================
echo   7Tan - PyInstaller Build
echo ================================================
echo.

:: Activate venv
echo [1/4] Activating virtual env...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Virtual env not found!
    pause
    exit /b 1
)
echo OK
echo.

:: PyInstaller
echo [2/4] Checking PyInstaller...
python -m pip install pyinstaller --upgrade --quiet
echo OK
echo.

:: Clean
echo [3/4] Cleaning old build...
if exist build rmdir /s /q build
if exist dist\7tan-editor rmdir /s /q dist\7tan-editor
echo OK
echo.

:: Build using spec file
echo [4/4] Building with PyInstaller (5-15 min)...
echo.
python -m PyInstaller build.spec --noconfirm --distpath dist --workpath build

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo ================================================
echo   BUILD SUCCESS!
echo   Output: dist\7tan-editor\7tan-editor.exe
echo ================================================
echo.
start "" "dist\7tan-editor"
pause
exit /b 0
