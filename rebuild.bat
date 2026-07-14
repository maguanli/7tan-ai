@echo off
echo ============================================
echo   7tanAI 构建脚本 v17
echo ============================================
cd /d D:\7tan\7tanAI

REM ========== 步骤 1: Git 备份 ==========
echo.
echo [1/3] Git 自动备份...
if not exist ".git" (
    echo   - 初始化 git 仓库...
    git init
    git add .gitignore requirements.txt main.py src/ data/prompts/ *.spec rebuild.bat start.bat
    git commit -m "初始提交: 7tanAI 源码"
) else (
    git add -A
    git commit -m "auto-save: %date% %time%"
)
if %errorlevel% neq 0 (
    echo   (git 提交跳过或无变更)
)

REM ========== 步骤 2: 构建 ==========
echo.
echo [2/3] PyInstaller 打包...

REM 备份已有的 dist config（放到 dist 外面防止被清掉）
if exist "dist\7tan-updater\config\config.yaml" (
    echo   [备份] 保留已有配置...
    copy /Y "dist\7tan-updater\config\config.yaml" "%TEMP%\7tan-config.yaml.bak" >nul
)

call .venv\Scripts\python.exe -m PyInstaller 7tan-updater.spec --noconfirm

REM 恢复备份的配置
if exist "%TEMP%\7tan-config.yaml.bak" (
    echo   [恢复] 还原用户配置...
    if not exist "dist\7tan-updater\config" mkdir "dist\7tan-updater\config"
    copy /Y "%TEMP%\7tan-config.yaml.bak" "dist\7tan-updater\config\config.yaml" >nul
    del "%TEMP%\7tan-config.yaml.bak"
)
if not exist "dist\7tan-updater\data\prompts" mkdir "dist\7tan-updater\data\prompts"
if exist "data\prompts\system.txt" copy /Y "data\prompts\system.txt" "dist\7tan-updater\data\prompts\system.txt" >nul

REM ========== 步骤 3: 完成 ==========
echo.
echo [3/3] 完成!
dir dist\7tan-updater\7tan-updater.exe 2>&1
echo ============================================
echo === EXE Info ===
dir dist\7tan-updater\7tan-updater.exe 2>&1
echo === DONE ===
