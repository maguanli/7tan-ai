@echo off
rem 注册 DeepSeek Harness 开机自启任务（用户登录时触发，隐藏窗口）
schtasks /create /tn "DSH-AutoStart" /tr "wscript.exe D:\7tan\7tanAI\run_dsh_hidden.vbs" /sc onlogon /f
echo EXITCODE=%errorlevel%
