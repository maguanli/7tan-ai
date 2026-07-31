@echo off
chcp 65001 >nul
title 7Tan 构建+同步工具
echo ==========================================
echo   7Tan 一键构建 + 同步到 dist
echo ==========================================
echo.

set ROOT=%~dp0
cd /d "%ROOT%"

REM ========== 步骤 0: Git 自动备份 ==========
echo [0/4] Git 自动备份...
if exist ".git" (
    git add -A
    git commit -m "auto-save: %date% %time%" >nul 2>&1
    echo   [OK] 已提交（或无变更）
) else (
    echo   [跳过] 未初始化 git
)

echo [1/4] 构建 exe...
call "%ROOT%.venv\Scripts\python.exe" -m PyInstaller build.spec --clean
if %ERRORLEVEL% neq 0 (
    echo.
    echo [错误] 构建失败，请检查上方输出
    pause
    exit /b 1
)
echo [1/4] 构建成功
echo.

REM ========== 步骤 2: 同步源码到 dist\_build\src\ ==========
REM 用 robocopy 替代 xcopy，排除敏感目录：
REM   _source_backup  = 安全模块明文 .py 备份（绝不能给专业版用户）
REM   __pycache__     = 字节码缓存
echo [2/4] 同步源码到 dist\_build\src\...
if not exist "dist\_build\src" mkdir "dist\_build\src"
robocopy "src" "dist\_build\src" /E /XD _source_backup __pycache__ .pytest_cache /XF *.pyc /NFL /NDL /NJH /NJS /NP
if %ERRORLEVEL% GEQ 8 (
    echo [错误] 源码同步失败 (robocopy 错误码 %ERRORLEVEL%)
    pause
    exit /b 1
)
echo [2/4] 源码已同步（已排除 _source_backup / __pycache__ / *.pyc）
echo.

REM ========== 步骤 3: 同步构建配置文件 ==========
echo [3/4] 同步构建配置...
copy /Y build.spec dist\_build\build.spec >nul
copy /Y requirements.txt dist\_build\requirements.txt >nul
echo [3/4] 配置已同步
echo.

REM ========== 步骤 4: 校验产物 ==========
echo [4/4] 校验产物...
set PYD_OK=1
if not exist "dist\7tan-editor\_internal\PYZ.pyz" (
    echo [错误] 产物缺少 PYZ.pyz，构建不完整！可能被杀毒软件拦截
    echo 请将 dist 目录加入杀毒白名单后重新构建
    pause
    exit /b 1
)
echo [OK] PYZ.pyz 已生成
if not exist "dist\7tan-editor\_internal\src\security\rsa_verify.pyd" set PYD_OK=0
if not exist "dist\7tan-editor\_internal\src\security\license_verify.pyd" set PYD_OK=0
if not exist "dist\7tan-editor\_internal\src\security\safe_modify.pyd" set PYD_OK=0
if not exist "dist\7tan-editor\_internal\src\security\auth_client.pyd" set PYD_OK=0
if not exist "dist\7tan-editor\_internal\src\security\integrity.pyd" set PYD_OK=0
if not exist "dist\7tan-editor\_internal\src\security\token_store.pyd" set PYD_OK=0
if not exist "dist\7tan-editor\_internal\src\security\strings.pyd" set PYD_OK=0
if not exist "dist\7tan-editor\_internal\src\security\trial_store.pyd" set PYD_OK=0
if "!PYD_OK!"=="0" (
    echo [警告] 产物中缺少部分防破解 .pyd，请检查 build.spec hiddenimports
) else (
    echo [OK] 防破解模块 8/8 已打包进产物
)

REM 检查 _build 是否混入明文备份
if exist "dist\_build\src\security\_source_backup" (
    echo [警告] _build 中发现明文安全源码备份，正在清除...
    rmdir /S /Q "dist\_build\src\security\_source_backup"
)
if exist "dist\_build\src\security\__pycache__" (
    rmdir /S /Q "dist\_build\src\security\__pycache__"
)
echo [4/4] 校验完成
echo.

echo ==========================================
echo   完成！
echo   新 exe: dist\7tan-editor\7tan-editor.exe
echo   源码:   dist\_build\src\
echo ==========================================
echo   免费版/专业版共用 dist，专业版内置构建环境
echo ==========================================
pause
