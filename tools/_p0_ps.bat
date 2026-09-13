@echo off
chcp 65001 >nul
powershell -NoProfile -Command "Get-Process | Where-Object { $_.ProcessName -match '7tan|python' } | Select-Object Id, ProcessName, Path | Format-Table -AutoSize"
