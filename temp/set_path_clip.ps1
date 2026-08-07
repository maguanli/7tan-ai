$p = 'D:\7tan\7tanAI\dist\release\7tan-editor-v1.0.6.zip'
if (Test-Path $p) { Write-Host ("FILE_EXISTS size=" + (Get-Item $p).Length) } else { Write-Host "FILE_MISSING" }
Set-Clipboard -Value $p
$c = Get-Clipboard -Raw
Write-Host ("CLIP=" + $c)
