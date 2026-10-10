@echo off
cd /d "D:\7tan\7tanAI\data\gzh_render"
start "gzhsrv" /min "C:\Program Files\Python312\python.exe" -m http.server 8899
exit
