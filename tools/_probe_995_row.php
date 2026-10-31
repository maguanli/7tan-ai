<?php
// 只读：输出 ll_wadyx.id=995 的全部字段
require 'D:/workspace/7tan/db.php';
$db = getDB();

$row = $db->query("SELECT * FROM ll_wadyx WHERE id=995")->fetch(PDO::FETCH_ASSOC);
if (!$row) { echo "NOT FOUND\n"; exit; }

foreach ($row as $k => $v) {
    if ($v === null) { echo "$k = NULL\n"; continue; }
    $s = (string)$v;
    $len = strlen($s);
    if ($len > 300) {
        $s = substr($s, 0, 300) . "...[len=$len]";
    }
    echo "$k = $s\n";
}

echo "\n---- 分类 ----\n";
$c = $db->query("SELECT * FROM ll_class WHERE id=" . (int)$row['ll_or'])->fetch(PDO::FETCH_ASSOC);
if ($c) { foreach ($c as $k=>$v) { echo "  $k = $v\n"; } }
