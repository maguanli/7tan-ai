param([string]$Text)
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$tb = New-Object System.Windows.Forms.TextBox
$tb.Multiline = $true
$tb.Text = $Text
[System.Windows.Forms.Clipboard]::SetText($tb.Text)
Write-Output "CLIPBOARD_OK"
