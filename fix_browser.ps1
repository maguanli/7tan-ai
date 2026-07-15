$file = "src/tools/browser_tools.py"
$content = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
Write-Host "替换前 _web_view 出现次数:" ($content -split "_web_view" | Measure-Object).Count
$content = $content.Replace("if _web_view is not None:", "if _get_active_view() is not None:")
$content = $content.Replace("if _web_view is None:", "if _get_active_view() is None:")
Write-Host "替换后 _web_view 出现次数:" ($content -split "_web_view" | Measure-Object).Count
[System.IO.File]::WriteAllText($file, $content, [System.Text.Encoding]::UTF8)
Write-Host "✅ 修复完成！"
