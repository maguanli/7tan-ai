@echo off
echo ====================================
echo 安装 7-Zip v24.09
echo ====================================

echo [1/3] 启动安装程序...
start /wait "" "D:\ai_video_tools\7-Zip\7z2409-x64.exe" /S

echo [2/3] 等待安装完成...
timeout /t 5 >nul

echo [3/3] 验证安装...
if exist "C:\Program Files\7-Zip\7z.exe" (
    echo ✅ 7-Zip 安装成功！
    echo 安装路径: C:\Program Files\7-Zip\
    "C:\Program Files\7-Zip\7z.exe" --help
) else (
    echo ❌ 7-Zip 安装可能未完成
    echo 请手动运行: D:\ai_video_tools\7-Zip\7z2409-x64.exe
)

pause
