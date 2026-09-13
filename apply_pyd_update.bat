@echo off
chcp 65001 >nul
REM ============================================================
REM 7Tan 安全更新：替换 auth_client.pyd（含 online_verify 修复）
REM 用法：关闭 7Tan 软件后，双击运行本脚本
REM ============================================================
cd /d D:\7tan\7tanAI

if not exist src\security\auth_client_new.pyd (
    echo [错误] 找不到 auth_client_new.pyd，可能已替换过
    pause
    exit /b 1
)

echo 正在替换 auth_client.pyd ...
copy /y src\security\auth_client_new.pyd src\security\auth_client.pyd >nul
if errorlevel 1 (
    echo [错误] 替换失败！请确认 7Tan 软件已完全关闭（包括后台进程）
    pause
    exit /b 1
)

del /q src\security\auth_client_new.pyd
echo [OK] 替换完成，新版本 pyd 已生效（256KB，含 online_verify 修复）
pause
