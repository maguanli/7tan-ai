@echo off
chcp 65001 >nul
echo ========================================
echo 验证软件安装
echo ========================================
echo.

echo [1/14] Node.js...
if exist "D:\nodejs\node-v22.16.0-win-x64\node.exe" (
    echo ✅ Node.js 已安装
    D:\nodejs\node-v22.16.0-win-x64\node.exe --version
) else (
    echo ❌ Node.js 未安装
)
echo.

echo [2/14] Gradle...
if exist "D:\gradle_cache\gradle-8.10\bin\gradle.bat" (
    echo ✅ Gradle 已安装
) else (
    echo ❌ Gradle 未安装
)
echo.

echo [3/14] Godot...
if exist "D:\godot\Godot_v4.7.1-stable_win64.exe" (
    echo ✅ Godot 已安装
) else (
    echo ❌ Godot 未安装
)
echo.

echo [4/14] 7-Zip...
if exist "C:\Program Files\7-Zip\7z.exe" (
    echo ✅ 7-Zip 已安装
) else (
    echo ❌ 7-Zip 未安装
)
echo.

echo [5/14] FFmpeg...
if exist "D:\ffmpeg\bin\ffmpeg.exe" (
    echo ✅ FFmpeg 已安装
) else (
    echo ❌ FFmpeg 未安装
)
echo.

echo [6/14] JDK 21...
if exist "D:\Android\Java\jdk-21\bin\java.exe" (
    echo ✅ JDK 21 已安装
) else (
    echo ❌ JDK 21 未安装
)
echo.

echo [7/14] Android SDK...
if exist "D:\Android\Sdk\platform-tools\adb.exe" (
    echo ✅ Android SDK 已安装
) else (
    echo ❌ Android SDK 未安装
)
echo.

echo [8/14] Android Studio...
if exist "D:\Android\Android Studio\bin\studio64.exe" (
    echo ✅ Android Studio 已安装
) else (
    echo ❌ Android Studio 未安装
)
echo.

echo [9/14] Unity Editor...
if exist "D:\Unity\Editor\2022.3\Editor\Unity.exe" (
    echo ✅ Unity Editor 已安装
) else (
    echo ❌ Unity Editor 未安装
)
echo.

echo [10/14] Unity Hub...
if exist "D:\Unity\UnityHub\Unity Hub.exe" (
    echo ✅ Unity Hub 已安装
) else (
    echo ❌ Unity Hub 未安装
)
echo.

echo [11/14] Stable Diffusion WebUI...
if exist "D:\AI_Video\stable-diffusion-webui\webui.bat" (
    echo ✅ Stable Diffusion WebUI 已安装
) else (
    echo ❌ Stable Diffusion WebUI 未安装
)
echo.

echo [12/14] ComfyUI...
if exist "D:\AI_Video\comfyui\ComfyUI\main.py" (
    echo ✅ ComfyUI 已安装
) else (
    echo ❌ ComfyUI 未安装
)
echo.

echo [13/14] Whisper.cpp...
if exist "D:\whisper_cpp\Release\main.exe" (
    echo ✅ Whisper.cpp 已安装
) else (
    echo ❌ Whisper.cpp 未安装
)
echo.

echo [14/14] Anything V5 动漫模型...
if exist "D:\AI_Video\stable-diffusion-webui\models\Stable-diffusion\anything-v5.safetensors" (
    echo ✅ Anything V5 动漫模型 已安装
) else (
    echo ❌ Anything V5 动漫模型 未安装
)
echo.

echo ========================================
echo 验证完成！
echo ========================================
echo.
pause