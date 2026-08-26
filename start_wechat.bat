@echo off
setlocal enabledelayedexpansion
set FOUND=
if exist "C:\Program Files\Tencent\WeChat\WeChat.exe" set FOUND=C:\Program Files\Tencent\WeChat\WeChat.exe
if not defined FOUND if exist "C:\Program Files (x86)\Tencent\WeChat\WeChat.exe" set FOUND=C:\Program Files (x86)\Tencent\WeChat\WeChat.exe
if not defined FOUND if exist "%LOCALAPPDATA%\Tencent\WeChat\WeChat.exe" set FOUND=%LOCALAPPDATA%\Tencent\WeChat\WeChat.exe
if not defined FOUND if exist "C:\Program Files\Tencent\Weixin\Weixin.exe" set FOUND=C:\Program Files\Tencent\Weixin\Weixin.exe
if not defined FOUND if exist "C:\Program Files (x86)\Tencent\Weixin\Weixin.exe" set FOUND=C:\Program Files (x86)\Tencent\Weixin\Weixin.exe
if not defined FOUND if exist "%LOCALAPPDATA%\Programs\Tencent\Weixin\Weixin.exe" set FOUND=%LOCALAPPDATA%\Programs\Tencent\Weixin\Weixin.exe
if defined FOUND (
  echo FOUND: !FOUND!
  start "" "!FOUND!"
) else (
  echo NOT_FOUND
)
