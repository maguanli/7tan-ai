$p = 'D:\7tan\7tanAI\dist\release\7tan-editor-v1.0.6.zip'
Set-Clipboard -Value $p
$c = Get-Clipboard -Raw
Write-Host ("CLIP=" + $c)
