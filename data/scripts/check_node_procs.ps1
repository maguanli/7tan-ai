Get-CimInstance Win32_Process -Filter "ProcessId=9520" | Select-Object ProcessId, ParentProcessId, CommandLine | Format-List
