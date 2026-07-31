$cim = Get-CimInstance Win32_Process -Filter "ProcessId = 13804"
if ($cim) {
    "PID: $($cim.ProcessId)"
    "NAME: $($cim.Name)"
    "CMDLINE: $($cim.CommandLine)"
    "START: $($cim.CreationDate)"
} else {
    "PID 13804 NOT FOUND"
}
