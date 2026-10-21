$ErrorActionPreference = 'Continue'
$f = 'D:\7tan\7tanAI\webmirror\downloads\_tasks.json'
Copy-Item -LiteralPath $f -Destination ($f + '.bak_before_unmap') -Force
Write-Output 'backup done'

# stop webmirror service so it cannot overwrite the edit
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like '*run.py*8000*' } |
    ForEach-Object { Write-Output ('stopping service pid ' + $_.ProcessId); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 3

# remove the host_dir_map entry that redirected youbian.293.net -> youbian.293.net2
$raw = Get-Content -LiteralPath $f -Raw
$new = $raw -replace '\s*"youbian\.293\.net"\s*:\s*"youbian\.293\.net2"\s*,?', ''
if ($new -eq $raw) { Write-Output 'WARN: pattern not found, file unchanged' }
[System.IO.File]::WriteAllText($f, $new, (New-Object System.Text.UTF8Encoding($false)))

try {
    $j = Get-Content -LiteralPath $f -Raw | ConvertFrom-Json
    $t = $j | Where-Object { $_.id -eq '20261011-063926-4ba5eb' }
    Write-Output ('JSON OK.  host_dir_map=' + ($t.config.host_dir_map | ConvertTo-Json -Compress) + '  status=' + $t.status + '  files=' + $t.stats.files)
} catch { Write-Output ('JSON ERROR: ' + $_.Exception.Message) }

# delete the now-empty net2 directory
$net2 = 'D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb\youbian.293.net2'
$cnt = (Get-ChildItem -LiteralPath $net2 -File -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object).Count
Write-Output ('net2 files = ' + $cnt)
if ($cnt -eq 0) {
    Remove-Item -LiteralPath $net2 -Recurse -Force -ErrorAction SilentlyContinue
    Write-Output ('net2 still exists = ' + (Test-Path -LiteralPath $net2))
}

# restart service
Start-Process -FilePath 'C:\Program Files\Python312\python.exe' -ArgumentList 'run.py', '--port', '8000' -WorkingDirectory 'D:\7tan\7tanAI\webmirror' -WindowStyle Hidden
Start-Sleep -Seconds 6
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*run.py*8000*' } | ForEach-Object { Write-Output ('service restarted pid=' + $_.ProcessId) }
