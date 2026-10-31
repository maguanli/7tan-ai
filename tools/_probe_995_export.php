<?php
// 导出 995 需要修改的字段全文到服务器文件
require 'D:/workspace/7tan/db.php';
$db = getDB();
$row = $db->query("SELECT id,ll_biaoti,ll_banben,ll_daxiao,ll_text,ll_url,ll_wxts,ll_gxts,ll_baike_ver,ll_baike_lead,ll_baike_body FROM ll_wadyx WHERE id=995")->fetch(PDO::FETCH_ASSOC);
$json = json_encode($row, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
$p = 'D:/workspace/7tan/updates/_995_export.json';
file_put_contents($p, $json);
echo "WROTE " . strlen($json) . " bytes to $p\n";
