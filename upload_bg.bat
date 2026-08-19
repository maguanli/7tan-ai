@echo off
chcp 65001 >nul
REM ??????????????tart /b ????????
set TOKEN=%%GITHUB_TOKEN%%
set RID=372578963
set DIR=D:\7tan\7tanAI\dist\release\github
set FILE=%~1

echo ?????????: %FILE%
start "upload_%FILE%" /b cmd /c "curl.exe -sS -L -X POST -H "Authorization: Bearer %TOKEN%" -H "Content-Type: application/zip" --data-binary "@%DIR%\%FILE%" "https://uploads.github.com/repos/maguanli/7tan-ai/releases/%RID%/assets?name=%FILE%" -o "%DIR%\resp_%FILE%.json" -w "HTTP %%{http_code} | uploaded %%{size_upload} | time %%{time_total}s" > "%DIR%\upload_%FILE%.log" 2>&1"
echo ???????????ID ?????????????? %DIR%\upload_%FILE%.log

