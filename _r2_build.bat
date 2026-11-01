@echo off
chcp 65001 >nul
cd /d D:\7tan\7tanAI
echo BUILD_START %date% %time% > data\logs\build_v1023_r2.log
call build_and_sync.bat -y >> data\logs\build_v1023_r2.log 2>&1
echo BUILD_EXITCODE=%errorlevel% >> data\logs\build_v1023_r2.log
echo BUILD_END %date% %time% >> data\logs\build_v1023_r2.log
