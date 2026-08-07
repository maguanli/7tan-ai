$c = Get-Clipboard -Raw
if ($c) {
    Write-Host ("CLIP_LEN=" + $c.Length)
    Write-Host $c.Substring(0, [Math]::Min(100, $c.Length))
} else {
    Write-Host "CLIP_EMPTY"
}
