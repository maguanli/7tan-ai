$ErrorActionPreference = 'Continue'
Write-Output "===== 进程详情 13248 / 11948 ====="
Get-CimInstance Win32_Process -Filter "ProcessId=13248 or ProcessId=11948" | ForEach-Object {
    Write-Output ("PID={0} PPID={1} Name={2}" -f $_.ProcessId, $_.ParentProcessId, $_.Name)
    Write-Output ("  Exe={0}" -f $_.ExecutablePath)
    Write-Output ("  Cmd={0}" -f $_.CommandLine)
    Write-Output ""
}

Write-Output "===== 所有带主窗口的进程 ====="
Get-Process | Where-Object { $_.MainWindowHandle -ne 0 } | ForEach-Object {
    Write-Output ("PID={0} Title=[{1}] Exe={2}" -f $_.Id, $_.MainWindowTitle, $_.Path)
}

Write-Output "===== 13248 / 11948 的主窗口 ====="
Get-Process -Id 13248,11948 -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Output ("PID={0} MainWindowHandle={1} Title=[{2}]" -f $_.Id, $_.MainWindowHandle, $_.MainWindowTitle)
}

Write-Output "===== 父进程信息 ====="
Get-CimInstance Win32_Process -Filter "ProcessId=13248 or ProcessId=11948" | ForEach-Object {
    $ppid = $_.ParentProcessId
    $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$ppid" -ErrorAction SilentlyContinue
    if ($parent) {
        Write-Output ("PID={0} 的父进程 PID={1} Name={2} Cmd={3}" -f $_.ProcessId, $parent.ProcessId, $parent.Name, $parent.CommandLine)
    } else {
        Write-Output ("PID={0} 的父进程 PID={1} 已不存在" -f $_.ProcessId, $ppid)
    }
}
