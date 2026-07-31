@echo off
chcp 65001 >nul
cd /d "%~dp0"
setlocal enabledelayedexpansion

echo ============================================
echo   7Tan 专业版 - 自构建工具 v2 (支持 .pyd 防破解)
echo ============================================
echo.

set PYTHON=%~dp0_python\python.exe

REM === 检查 _python 是否存在 ===
if not exist "%PYTHON%" (
    echo [错误] 未找到内置 Python 环境 _python\python.exe
    echo 请重新下载专业版完整包。
    pause
    exit /b 1
)

REM === 检查 Python 版本 >= 3.12 (.pyd 为 cp312 编译) ===
"%PYTHON%" -c "import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [错误] _python 版本过低，需要 Python 3.12+（防破解模块 .pyd 基于 3.12 编译）
    echo 当前版本:
    "%PYTHON%" --version
    echo 请更新 _python 目录后重试。
    pause
    exit /b 1
)
echo   [OK] Python 环境: 
"%PYTHON%" --version

REM === 检查 _build 是否存在 ===
if not exist "_build\main.py" (
    echo [错误] 未找到源码 _build\main.py
    pause
    exit /b 1
)

REM === 检查防破解 .pyd 是否就绪（8/8）===
set PYD_OK=1
if not exist "_build\src\security\rsa_verify.pyd" set PYD_OK=0
if not exist "_build\src\security\license_verify.pyd" set PYD_OK=0
if not exist "_build\src\security\safe_modify.pyd" set PYD_OK=0
if not exist "_build\src\security\auth_client.pyd" set PYD_OK=0
if not exist "_build\src\security\integrity.pyd" set PYD_OK=0
if not exist "_build\src\security\token_store.pyd" set PYD_OK=0
if not exist "_build\src\security\strings.pyd" set PYD_OK=0
if not exist "_build\src\security\trial_store.pyd" set PYD_OK=0
if "!PYD_OK!"=="0" (
    echo [错误] 缺少预编译防破解模块 .pyd
    echo 需要 8 个: rsa_verify / license_verify / safe_modify / auth_client
    echo            integrity / token_store / strings / trial_store
    echo 这些是编译好的二进制模块，无法现场生成，请重新下载完整包。
    pause
    exit /b 1
)
echo   [OK] 防破解模块 .pyd 已就绪 (8/8)

REM === 步骤 1: 备份当前 exe ===
echo.
echo [1/4] 备份当前版本...
if exist "7tan-editor\7tan-editor.exe" (
    set BACKUP_NAME=7tan-editor_backup_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%.exe
    set BACKUP_NAME=!BACKUP_NAME: =0!
    echo   备份为: !BACKUP_NAME!
    copy /Y "7tan-editor\7tan-editor.exe" "!BACKUP_NAME!" >nul
)

REM === 步骤 2: 检查并同步依赖 ===
REM 说明：不能只检查少数核心包（曾因漏检 pygments 导致产物缺模块崩溃），
REM 改为每次构建前全量同步 requirements.txt，已安装的包秒级跳过。
echo.
echo [2/4] 检查并同步依赖...
echo   [同步] pip install -r _build\requirements.txt ...
"%PYTHON%" -m pip install -r _build\requirements.txt -q
if errorlevel 1 (
    echo   [警告] 依赖同步失败，继续构建（如产物功能缺失请重新运行本工具）
)

REM === 步骤 3: PyInstaller 打包 ===
echo.
echo [3/4] PyInstaller 打包（需要 5-15 分钟）...
echo.

REM 确保 PyInstaller 已安装
"%PYTHON%" -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo   [安装] PyInstaller...
    "%PYTHON%" -m pip install pyinstaller -q
)

REM 构建
"%PYTHON%" -m PyInstaller _build\build.spec --distpath "%~dp0." --workpath _build\temp --noconfirm

if errorlevel 1 (
    echo.
    echo [失败] 构建出错，请检查上方错误信息。
    pause
    exit /b 1
)

REM === 步骤 4: 验证产物 ===
echo.
echo [4/4] 验证产物...
set PYD_IN=1
if not exist "7tan-editor\_internal\src\security\rsa_verify.pyd" set PYD_IN=0
if not exist "7tan-editor\_internal\src\security\license_verify.pyd" set PYD_IN=0
if not exist "7tan-editor\_internal\src\security\safe_modify.pyd" set PYD_IN=0
if not exist "7tan-editor\_internal\src\security\auth_client.pyd" set PYD_IN=0
if not exist "7tan-editor\_internal\src\security\integrity.pyd" set PYD_IN=0
if not exist "7tan-editor\_internal\src\security\token_store.pyd" set PYD_IN=0
if not exist "7tan-editor\_internal\src\security\strings.pyd" set PYD_IN=0
if not exist "7tan-editor\_internal\src\security\trial_store.pyd" set PYD_IN=0
if "!PYD_IN!"=="1" (
    echo   [OK] 防破解模块已打包进产物 (8/8)
) else (
    echo   [警告] 产物中未检测到全部防破解 .pyd，请检查 _build\build.spec 的 hiddenimports
)

echo.
echo ============================================
echo   新 exe 位置: 7tan-editor\7tan-editor.exe
echo   备份文件: 7tan-editor_backup_*.exe
echo ============================================
echo.
dir "%~dp07tan-editor\7tan-editor.exe" 2>&1
echo.
echo 按任意键退出...
pause >nul
