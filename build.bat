@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ╔══════════════════════════════════════════════╗
echo ║   7Tan — PyInstaller 一键打包脚本            ║
echo ║   输出: dist\7tan-editor\7tan-editor.exe      ║
echo ╚══════════════════════════════════════════════╝
echo.

:: ── 1. 检查 Python ──
echo [1/5] 检查 Python...
call .venv\Scripts\activate.bat 2>nul
if errorlevel 1 (
    echo [错误] 请先运行 start.bat 创建虚拟环境！
    pause
    exit /b 1
)
python --version
echo.

:: ── 2. 安装/升级 PyInstaller ──
echo [2/5] 安装 PyInstaller...
python -m pip install pyinstaller --upgrade
if errorlevel 1 (
    echo [错误] PyInstaller 安装失败！
    pause
    exit /b 1
)
echo.

:: ── 3. 确认 PyQt6（必需！） ──
echo [3/5] 确认 PyQt6 + QWebEngineView...
python -c "from PyQt6.QtWebEngineWidgets import QWebEngineView; print('PyQt6 OK')" >nul 2>&1
if errorlevel 1 (
    echo [信息] PyQt6 未安装，正在安装（约150MB，请耐心等待）...
    set PYTHONUTF8=1
    python -m pip install PyQt6 PyQt6-WebEngine
    if errorlevel 1 (
        echo [错误] PyQt6 安装失败！请手动运行:
        echo   .venv\Scripts\activate
        echo   pip install PyQt6 PyQt6-WebEngine
        pause
        exit /b 1
    )
)
echo PyQt6 OK
echo.

:: ── 4. PyInstaller 打包 ──
echo [4/5] PyInstaller 打包中（需要5-15分钟，请耐心等待）...
echo.
:: 清理旧构建 — 先强制删除文件再用 rmdir，避免 PyInstaller 弹确认
if exist "dist\7tan-editor" (
    taskkill /F /IM 7tan-editor.exe >nul 2>&1
    del /f /s /q "dist\7tan-editor\*" >nul 2>&1
    rmdir /s /q "dist\7tan-editor" >nul 2>&1
)
if exist "build" (
    del /f /s /q "build\*" >nul 2>&1
    rmdir /s /q "build" >nul 2>&1
)

pyinstaller build.spec --noconfirm
if errorlevel 1 (
    echo.
    echo [错误] PyInstaller 打包失败！
    echo 请检查上方错误信息。
    pause
    exit /b 1
)
echo.

:: ── 5. 复制额外文件到 dist ──
echo [5/5] 复制运行文件到 dist\7tan-editor\...
:: 复制配置文件模板
if not exist "dist\7tan-editor\config" mkdir "dist\7tan-editor\config"
copy /y "config\config.yaml" "dist\7tan-editor\config\config.yaml" >nul
copy /y "config\sensitive_words.txt" "dist\7tan-editor\config\sensitive_words.txt" >nul
:: 复制 .env 模板
copy /y ".env.example" "dist\7tan-editor\.env.example" >nul
:: 复制数据目录结构（build.spec已打包prompts和plugins，这里补充运行时数据目录）
if not exist "dist\7tan-editor\data" mkdir "dist\7tan-editor\data"
if not exist "dist\7tan-editor\logs" mkdir "dist\7tan-editor\logs"
if not exist "dist\7tan-editor\downloads" mkdir "dist\7tan-editor\downloads"

echo.
echo ╔══════════════════════════════════════════════╗
echo ║  打包完成！  ^^_^                            ║
echo ║                                            ║
echo ║  输出位置: dist\7tan-editor\                ║
echo ║  启动文件: 7tan-editor.exe                  ║
echo ║  预计大小: 300-500MB (含 Chromium)           ║
echo ║                                            ║
echo ║  首次使用请在 exe 同级目录:                   ║
echo ║  1. 复制 .env.example 重命名为 .env          ║
echo ║  2. 填写 API Key                             ║
echo ║  3. 双击运行 7tan-editor.exe                 ║
echo ╚══════════════════════════════════════════════╝
echo.

:: 打开输出文件夹
start "" "dist\7tan-editor"

pause
exit /b 0
