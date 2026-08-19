@echo off
chcp 65001 >nul
echo ========================================
echo 设置环境变量
echo ========================================
echo.

echo [1/3] 设置JAVA_HOME...
setx JAVA_HOME "D:\Android\Java\jdk-21"
echo.

echo [2/3] 设置ANDROID_HOME...
setx ANDROID_HOME "D:\Android\Sdk"
echo.

echo [3/3] 设置GRADLE_HOME...
setx GRADLE_HOME "D:\gradle_cache\gradle-8.10"
echo.

echo ========================================
echo 环境变量设置完成！
echo 请重启命令行或计算机使环境变量生效。
echo ========================================
echo.
pause