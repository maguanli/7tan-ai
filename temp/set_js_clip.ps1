$code = Get-Content -Raw -Encoding UTF8 'D:\7tan\7tanAI\temp\js_select.js.txt'
Set-Clipboard -Value $code
Write-Host ("CLIP_LEN=" + $code.Length)
