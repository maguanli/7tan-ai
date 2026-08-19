@echo off
chcp 65001 >nul
echo ========================================
echo G盘软件迁移到D盘 - 剩余软件安装脚本
echo ========================================
echo.

echo [1/7] 安装7-Zip...
echo 请手动运行: D:\ai_video_tools\7-Zip\7z2409-x64.exe
echo.

echo [2/7] 下载JDK 21...
echo 请从以下链接下载JDK 21:
echo https://adoptium.net/temurin/releases/?version=21
echo 下载后解压到: D:\Android\Java\jdk-21
echo.

echo [3/7] 下载FFmpeg...
echo 请从以下链接下载FFmpeg:
echo https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
echo 下载后解压到: D:\ffmpeg
echo.

echo [4/7] 下载Android Studio...
echo 请从以下链接下载Android Studio:
echo https://developer.android.com/studio
echo 安装时选择D:\Android\Android Studio
echo.

echo [5/7] 下载Unity Hub...
echo 请从以下链接下载Unity Hub:
echo https://unity.com/download
echo 安装时选择D:\Unity\UnityHub
echo.

echo [6/7] 下载Stable Diffusion WebUI...
echo 请从以下链接下载:
echo https://github.com/AUTOMATIC1111/stable-diffusion-webui
echo 解压到: D:\AI_Video\stable-diffusion-webui
echo.

echo [7/7] 下载ComfyUI...
echo 请从以下链接下载:
echo https://github.com/comfyanonymous/ComfyUI
echo 解压到: D:\AI_Video\comfyui\ComfyUI
echo.

echo ========================================
echo 安装完成后，请设置以下环境变量:
echo.
echo JAVA_HOME = D:\Android\Java\jdk-21
echo ANDROID_HOME = D:\Android\Sdk
echo GRADLE_HOME = D:\gradle_cache\gradle-8.10
echo ========================================
echo.
pause