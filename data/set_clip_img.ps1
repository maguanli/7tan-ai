Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$imgPath = $args[0]
$img = [System.Drawing.Image]::FromFile($imgPath)
[System.Windows.Forms.Clipboard]::SetImage($img)
Start-Sleep -Milliseconds 300
Write-Output ('clipboard set ok: ' + $imgPath)
