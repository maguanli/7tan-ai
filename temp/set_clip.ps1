$text = "7Tan Editor is a legitimate AI desktop assistant application developed by an individual developer. It has been incorrectly detected as PUA (potentially unwanted application). The application is a normal GUI desktop tool for AI chat and automation. It does not perform any unwanted behaviors, no hidden installation, no adware, no data collection without consent. Please re-analyze the attached file and remove the false positive detection. Thank you."
Set-Clipboard -Value $text
$c = Get-Clipboard -Raw
if ($c) { Write-Host ("OK LEN=" + $c.Length) } else { Write-Host "FAIL" }
