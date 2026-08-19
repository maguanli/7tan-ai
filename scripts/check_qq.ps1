# 检查QQ相关进程和窗口
Write-Host "===== 所有 QQ 相关进程 ====="
Get-Process | Where-Object { $_.ProcessName -match 'QQ|TIM' } | Select-Object ProcessName, Id, MainWindowTitle, Responding, StartTime | Format-Table -AutoSize | Out-String -Width 200

Write-Host "===== 所有有窗口的进程 ====="
Get-Process | Where-Object { $_.MainWindowTitle -ne '' } | Select-Object ProcessName, Id, MainWindowTitle, Responding | Format-Table -AutoSize | Out-String -Width 200

Write-Host "===== QQ 安装目录探测 ====="
$paths = @(
  "$env:ProgramFiles\Tencent\QQNT",
  "${env:ProgramFiles(x86)}\Tencent\QQNT",
  "$env:LOCALAPPDATA\Programs\QQ",
  "$env:ProgramFiles\Tencent\QQ",
  "${env:ProgramFiles(x86)}\Tencent\QQ"
)
foreach ($p in $paths) {
  if (Test-Path $p) { Write-Host "FOUND: $p" }
}
