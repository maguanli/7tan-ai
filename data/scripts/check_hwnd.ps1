Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinInfo {
    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
}
"@
$targets = @(1114918, 1443948, 1442886, 5701804, 131556, 262600, 787646, 262376)
foreach ($h in $targets) {
    $procId = 0
    [WinInfo]::GetWindowThreadProcessId([IntPtr]$h, [ref]$procId) | Out-Null
    $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($p) {
        Write-Output ("hwnd={0} PID={1} Name={2} Title=[{3}] Path={4}" -f $h, $procId, $p.ProcessName, $p.MainWindowTitle, $p.Path)
    } else {
        Write-Output ("hwnd={0} PID={1} (进程不存在)" -f $h, $procId)
    }
}
