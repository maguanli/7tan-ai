@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ╔══════════════════════════════════════╗
echo ║       🤖 七坛 QQ 机器人              ║
echo ║      启动中...                       ║
echo ╚══════════════════════════════════════╝
echo.

REM 检查 .env 是否存在
if not exist ".env" (
    echo [错误] 未找到 .env 配置文件！
    echo 请复制 .env.example 为 .env 并修改配置
    pause
    exit /b 1
)

REM 安装依赖 (首次运行)
if not exist ".deps_installed" (
    echo [1/2] 安装依赖...
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败！
        pause
        exit /b 1
    )
    type nul > .deps_installed
    echo 依赖安装完成！
)

echo [2/2] 启动机器人...
echo.
python bot.py

pause
