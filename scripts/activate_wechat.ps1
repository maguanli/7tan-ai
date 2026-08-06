Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
}
"@
$h = [IntPtr]329388
Write-Output ("IsIconic: " + [Win32]::IsIconic($h))
Write-Output ("IsVisible: " + [Win32]::IsWindowVisible($h))
$r = New-Object Win32+RECT
[Win32]::GetWindowRect($h, [ref]$r) | Out-Null
Write-Output ("Rect: L=" + $r.Left + " T=" + $r.Top + " R=" + $r.Right + " B=" + $r.Bottom)
[Win32]::ShowWindow($h, 9) | Out-Null
Start-Sleep -Milliseconds 500
[Win32]::SetForegroundWindow($h) | Out-Null
Start-Sleep -Milliseconds 300
Write-Output ("ForegroundAfter: " + [Win32]::SetForegroundWindow($h))
Write-Output "DONE"
