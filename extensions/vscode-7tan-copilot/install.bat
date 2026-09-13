@echo off
echo ============================================
echo  7Tan VS Code 扩展 — 一键安装
echo ============================================
echo.

cd /d "%~dp0"

echo [1/3] 检查 Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 未找到 Node.js，请先安装 Node.js
    echo 下载: https://nodejs.org/
    pause
    exit /b 1
)
echo        Node.js OK

echo [2/3] 安装依赖 & 编译...
call npm install
call npm run compile
if %errorlevel% neq 0 (
    echo [ERROR] 编译失败
    pause
    exit /b 1
)
echo        OK

echo [3/3] 安装到 VS Code...
code --install-extension vscode-7tan-copilot-2.0.0.vsix 2>nul

if %errorlevel% neq 0 (
    echo        .vsix 不存在，使用开发模式安装...
    echo        → 请在 VS Code 中按 Ctrl+Shift+P
    echo        → 输入 Developer: Install Extension from Location...
    echo        → 选择: %cd%
)

echo.
echo ============================================
echo  安装完成！重启 VS Code 即可使用
echo ============================================
echo.
echo 快捷键:
echo   Ctrl+Shift+E — AI 解释选中代码
echo   Ctrl+Shift+F — AI 修复选中代码
echo.
echo 命令面板 (Ctrl+Shift+P):
echo   7Tan: AI 代码审查当前文件
echo   7Tan: 安全扫描当前文件
echo   7Tan: AI 生成 Commit 信息
echo   7Tan: Git 提交 (AI Commit Message)
echo   7Tan: 配置 API
echo.
pause
