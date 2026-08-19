@echo off
chcp 65001 >nul
setlocal
REM ?????? Release ???
set TOKEN=%%GITHUB_TOKEN%%
set RID=372578963
set DIR=D:\7tan\7tanAI\dist\release\github
set FILE=%~1

echo [???] %FILE% ...
curl.exe -sS -L -X POST -H "Authorization: Bearer %TOKEN%" -H "Content-Type: application/zip" --data-binary "@%DIR%\%FILE%" "https://uploads.github.com/repos/maguanli/7tan-ai/releases/%RID%/assets?name=%FILE%" -o "%DIR%\resp_%FILE%.json" -w "HTTP %%{http_code} | ??? %%{size_upload} bytes | ??? %%{time_total}s\n"
echo ??????: %DIR%\resp_%FILE%.json

