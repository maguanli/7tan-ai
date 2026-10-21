$ErrorActionPreference = 'Continue'
$b    = 'D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb'
$net  = Join-Path $b 'youbian.293.net'
$net2 = Join-Path $b 'youbian.293.net2'
$log  = 'D:\7tan\7tanAI\webmirror\_do_merge.log'
function L([string]$m) { ((Get-Date -Format 'HH:mm:ss') + ' ' + $m) | Out-File -Append -Encoding UTF8 $log }

L 'START2 merge'
$sw  = [Diagnostics.Stopwatch]::StartNew()
$set = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
foreach ($f in [System.IO.Directory]::EnumerateFiles($net)) { [void]$set.Add([System.IO.Path]::GetFileName($f)) }
L ("indexed net: {0} names ({1}s)" -f $set.Count, [int]$sw.Elapsed.TotalSeconds)

$i = 0; $moved = 0; $dup = 0; $fail = 0
$sw2 = [Diagnostics.Stopwatch]::StartNew()
foreach ($f in [System.IO.Directory]::EnumerateFiles($net2)) {
    $i++
    $n = [System.IO.Path]::GetFileName($f)
    if ($set.Contains($n)) {
        try { [System.IO.File]::Delete($f); $dup++ } catch { $fail++ }
    } else {
        try { [System.IO.File]::Move($f, (Join-Path $net $n)); [void]$set.Add($n); $moved++ } catch { $fail++ }
    }
    if (($i % 500) -eq 0) { L ("i={0} moved={1} dup={2} fail={3} {4}s" -f $i, $moved, $dup, $fail, [int]$sw2.Elapsed.TotalSeconds) }
}
L ("DONE i={0} moved={1} dup={2} fail={3} {4}s" -f $i, $moved, $dup, $fail, [int]$sw2.Elapsed.TotalSeconds)
