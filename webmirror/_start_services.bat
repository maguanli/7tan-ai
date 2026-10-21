@echo off
rem 启动本地联调环境：测试站点(8801) + WebMirror(8000)
set BASE=%~dp0
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'python' -ArgumentList '-m','http.server','8801','--directory','%BASE%tests\testsite' -WorkingDirectory '%BASE%' -WindowStyle Hidden -RedirectStandardOutput '%BASE%_testsite.log' -RedirectStandardError '%BASE%_testsite.err'"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'python' -ArgumentList 'run.py','--port','8000' -WorkingDirectory '%BASE%' -WindowStyle Hidden -RedirectStandardOutput '%BASE%_server.log' -RedirectStandardError '%BASE%_server.err'"
echo 已提交启动请求
