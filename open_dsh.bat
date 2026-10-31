@echo off
rem ============================================================
rem  DeepSeek Harness - open the Web UI in the default browser
rem  1) if nothing listens on 127.0.0.1:3080, start it first
rem  2) open the token URL (plain http://127.0.0.1:3080 -> 401 by design)
rem ============================================================
setlocal enabledelayedexpansion

set "LOG=D:\7tan\7tanAI\logs\dsh_web.log"
set "ERRLOG=D:\7tan\7tanAI\logs\dsh_web_err.log"
set "BAT=D:\7tan\7tanAI\start_dsh.bat"

netstat -ano | findstr ":3080" | findstr "LISTENING" >nul 2>nul
if "%errorlevel%"=="0" goto ready

echo [dsh] not running - starting...
call "%BAT%"

set /a tries=0
:waitloop
timeout /t 2 /nobreak >nul
set /a tries+=1
netstat -ano | findstr ":3080" | findstr "LISTENING" >nul 2>nul
if "%errorlevel%"=="0" goto ready
if !tries! GEQ 45 goto failed
goto waitloop

:failed
echo [dsh] still not listening after 90s.
echo [dsh] log: %LOG%
echo [dsh] err: %ERRLOG%
pause
exit /b 1

:ready
rem the log is truncated on every start - wait until the token url appears
set /a w=0
:waiturl
set "URL="
if not exist "%LOG%" goto waitmore
for /f "usebackq tokens=3" %%u in (`findstr /c:"token=" "%LOG%"`) do set "URL=%%u"
if defined URL goto openurl
:waitmore
set /a w+=1
if !w! GEQ 30 goto nolog
timeout /t 2 /nobreak >nul
goto waiturl

:openurl
echo [dsh] opening !URL!
start "" "!URL!"
exit /b 0

:nolog
echo [dsh] token url not found in log, opening base url
echo [dsh] (base url may answer 401 - use the URL printed by dsh web)
start "" "http://127.0.0.1:3080/"
exit /b 0
