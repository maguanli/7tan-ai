<?php
// 只读探测：定位 995 记录所在表与字段
require 'D:/workspace/7tan/db.php';
header('Content-Type: text/plain; charset=utf-8');

$db = getDB();
$tables = $db->query("SHOW TABLES")->fetchAll(PDO::FETCH_COLUMN);
echo "TABLE_COUNT=" . count($tables) . "\n";
echo "TABLES=" . implode(',', $tables) . "\n\n";

$hits = array();
foreach ($tables as $t) {
    try {
        $cols = $db->query("SHOW COLUMNS FROM `$t`")->fetchAll(PDO::FETCH_ASSOC);
    } catch (Exception $e) { continue; }
    $names = array_map(function($c){ return $c['Field']; }, $cols);
    $idcol = in_array('id', $names) ? 'id' : (in_array('idd', $names) ? 'idd' : null);
    if (!$idcol) { continue; }
    try {
        $n = $db->query("SELECT COUNT(*) FROM `$t` WHERE `$idcol`=995")->fetchColumn();
    } catch (Exception $e) { continue; }
    if ($n > 0) {
        $hits[] = array('table' => $t, 'idcol' => $idcol, 'cols' => $names);
        echo "HIT table=$t idcol=$idcol\n";
        echo "  COLS=" . implode(',', $names) . "\n";
    }
}

echo "\nHIT_COUNT=" . count($hits) . "\n";

// 对命中表输出 995 行的关键字段（截断长文本）
foreach ($hits as $h) {
    $t = $h['table']; $idcol = $h['idcol'];
    echo "\n===== ROW $t.$idcol=995 =====\n";
    try {
        $row = $db->query("SELECT * FROM `$t` WHERE `$idcol`=995")->fetch(PDO::FETCH_ASSOC);
        foreach ($row as $k => $v) {
            if ($v === null) { echo "  $k = NULL\n"; continue; }
            $s = (string)$v;
            if (strlen($s) > 160) { $s = substr($s, 0, 160) . '...[len=' . strlen($s) . ']'; }
            echo "  $k = $s\n";
        }
    } catch (Exception $e) {
        echo "  ROW FAIL: " . $e->getMessage() . "\n";
    }
}
