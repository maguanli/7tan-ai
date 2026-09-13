@echo off
setlocal enabledelayedexpansion
echo.
echo ======================================
echo     Install Python 3.12.5
echo   7tanAI Runtime One-Click Setup
echo ======================================
echo.
echo About to install Python 3.12.5 (64-bit)
echo   [+] Auto add to system PATH
echo   [+] Install pip package manager
echo   [+] Available for all users
echo.
echo Press any key to start, or close this window to cancel...
pause >nul

cd /d "%~dp0"

if not exist "python-3.12.5-amd64.exe" (
    echo [ERROR] Installer python-3.12.5-amd64.exe not found
    echo Make sure this script is in the same folder as the installer
    pause
    exit /b 1
)

echo.
echo [INSTALL] Installing Python 3.12.5...
echo This may take 1-2 minutes, please wait...
echo.

python-3.12.5-amd64.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0

if !errorlevel! neq 0 (
    echo [WARN] Silent install failed, launching interactive installer...
    python-3.12.5-amd64.exe
)

echo.
echo [DONE] Please reopen command prompt or restart PC for PATH to take effect
echo Then double-click start.bat to launch 7tanAI
echo.
pause
