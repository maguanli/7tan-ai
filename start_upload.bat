@echo off
chcp 65001 >nul
REM 后台启动 python 上传脚本
start "" /b cmd /c "python D:\7tan\7tanAI\upload_asset.py %1 > D:\7tan\7tanAI\dist\release\github\upload_%1.log 2>&1"
echo 后台启动完成: %1
