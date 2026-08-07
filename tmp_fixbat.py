import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

path = r'D:\7tan\7tanAI\build_and_sync.bat'
raw = open(path, 'rb').read()
txt = raw.decode('utf-8')

OLD = """REM ===== Step 0.75: Clean old dist output (fix COLLECT not-empty failure) =====
echo [0.75/4] Cleaning old dist\\7tan-editor...
set "CLEAN_OK=0"
for /l %%i in (1,1,10) do (
    if exist "dist\\7tan-editor" (
        rmdir /s /q "dist\\7tan-editor" 2>nul
        if not exist "dist\\7tan-editor" ( set "CLEAN_OK=1" & goto clean_done )
        echo   [WARN] dist\\7tan-editor 被占用(%%i/10)：可能是杀软实时扫描或 7Tan 正在使用，等待 2 秒重试...
        timeout /t 2 /nobreak >nul
    ) else (
        set "CLEAN_OK=1"
        goto clean_done
    )
)
:clean_done
if not defined SKIP_BUILD (
    if "!CLEAN_OK!"=="0" (
        echo.
        echo [ERROR] 无法清理 dist\\7tan-editor（文件被占用）。
        echo         请关闭 7Tan 软件、资源管理器窗口，或将 D:\\7tan\\7tanAI 加入杀软白名单后重试。
        if not defined SKIP_PAUSE pause
        exit /b 1
    )
    echo [0.75/4] Clean OK
) else (
    echo [0.75/4] SKIP clean (--no-build mode)
)
echo."""

NEW = """REM ===== Step 0.75: Clean old dist output (fix COLLECT not-empty failure) =====
echo [0.75/4] Cleaning old dist\\7tan-editor...
if not defined SKIP_BUILD (
    if exist "dist\\7tan-editor" (
        rmdir /s /q "dist\\7tan-editor"
        if exist "dist\\7tan-editor" (
            echo [WARN] dist\\7tan-editor is still locked, retry in 3s...
            timeout /t 3 /nobreak >nul
            rmdir /s /q "dist\\7tan-editor"
        )
        if exist "dist\\7tan-editor" (
            echo [ERROR] dist\\7tan-editor still locked. Close 7Tan / explorer, or whitelist project dir in antivirus.
            if not defined SKIP_PAUSE pause
            exit /b 1
        )
    )
    echo [0.75/4] Clean OK
) else (
    echo [0.75/4] SKIP clean (--no-build mode)
)
echo."""

# 处理 CRLF
old_crlf = OLD.replace('\n', '\r\n')
new_crlf = NEW.replace('\n', '\r\n')

if old_crlf in txt:
    txt = txt.replace(old_crlf, new_crlf)
    print('REPLACED_OK (crlf)')
elif OLD in txt:
    txt = txt.replace(OLD, NEW)
    print('REPLACED_OK (lf)')
else:
    print('NOT_FOUND')
    # 输出上下文帮助调试
    idx = txt.find('Step 0.75')
    print('CTX:', repr(txt[idx-100:idx+800]))

open(path, 'wb').write(txt.encode('utf-8'))
print('WRITTEN')
