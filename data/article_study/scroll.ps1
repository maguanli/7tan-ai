Add-Type -AssemblyName System.Windows.Forms
$sig = '[DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, int dwData, int dwExtraInfo);'
Add-Type -MemberDefinition $sig -Name M -Namespace W
[System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point(1500,500)
Start-Sleep -m 300
for($i=0;$i -lt 80;$i++){ [W.M]::mouse_event(0x0800,0,0,120,0); Start-Sleep -m 12 }
Write-Output "scrolled up done"
