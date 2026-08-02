Get-CimInstance Win32_Process | Where-Object { $_.Name -match '7tan' -or $_.CommandLine -match '7tan' } | Select-Object ProcessId, Name, ExecutablePath, CommandLine | Format-List
