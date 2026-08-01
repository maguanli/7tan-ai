@echo off
call build_and_sync.bat -y > build_log.txt 2>&1
echo WRAPPER_DONE exit=%ERRORLEVEL%
