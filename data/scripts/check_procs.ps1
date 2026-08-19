Write-Output '=== PID 10964/13248/11948 ==='
Get-Process -Id 10964,13248,11948 -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,MainWindowTitle,Path | Format-List
Write-Output '=== all python.exe processes ==='
Get-CimInstance Win32_Process -Filter "name='python.exe'" | Select-Object ProcessId,ParentProcessId,CommandLine | Format-List
Write-Output '=== port 9800 ==='
Get-NetTCPConnection -LocalPort 9800 -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,State,OwningProcess | Format-Table
