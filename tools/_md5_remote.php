<?php
foreach ($argv as $i => $f) { if ($i == 0) continue; echo basename($f), " ", (file_exists($f) ? md5_file($f) : "MISSING"), " ", (file_exists($f) ? filesize($f) : 0), "\n"; }
