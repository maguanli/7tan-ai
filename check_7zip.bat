@echo off
echo 检查 7-Zip 安装状态...

if exist "C:\Program Files\7-Zip\7z.exe" (
    echo ✅ 7-Zip 已安装
    echo 路径: C:\Program Files\7-Zip\
    "C:\Program Files\7-Zip\7z.exe" i
) else (
    echo ❌ 7-Zip 未安装
    echo 请手动安装: D:\ai_video_tools\7-Zip\7z2409-x64.exe
)

pause
