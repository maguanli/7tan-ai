Add-Type -AssemblyName System.Windows.Forms
$text = Get-Content -Path 'D:\7tan\7tanAI\data\find_text.txt' -Encoding UTF8 -Raw
[System.Windows.Forms.Clipboard]::SetText($text)
Write-Output 'clipboard text ok'
