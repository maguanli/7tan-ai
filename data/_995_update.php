<?php
require 'D:/workspace/7tan/db.php';
$db = getDB();
$body = file_get_contents('D:/workspace/7tan/updates/_995_new_body.txt');
if ($body === false || strlen($body) < 1000) { echo "BODY_READ_FAIL\n"; exit(1); }
$gxts = 'v1.0.23 更新：上线全新 Agent 架构，AI 开始指挥 AI 干活——新增子 Agent 派工（独立会话、独立预算、代码类任务自动分配 git worktree）；多任务并发与资源隔离（中止信号按作用域隔离、资源租约、每 Worker 独立浏览器视图）；发布验收断言闸门（故障即判失败）；命令作用域围栏与全量审计。修复超长历史消息导致调用失败。';
$lead = '1.0.23 官方词条：软件与插件完全免费，Windows 10／11 解压即用；AI 能力需自备 API 密钥。';
$sql = "UPDATE ll_wadyx SET ll_banben=?, ll_daxiao=?, ll_text=?, ll_gxts=?, ll_baike_ver=?, ll_baike_lead=?, ll_baike_body=?, ll_baike_time=?, ll_retime=? WHERE id=995";
$st = $db->prepare($sql);
$st->execute(array('1.0.23', 419870967, 'https://www.7tan.com/updates/7tan-editor-free-v1.0.23.zip', $gxts, '1.0.23', $lead, $body, date('Y-m-d H:i:s'), date('Y-m-d H:i:s')));
echo "AFFECTED=" . $st->rowCount() . "\n";
$r = $db->query("SELECT ll_banben,ll_daxiao,ll_text,ll_gxts,ll_baike_ver,LEFT(ll_baike_lead,30) lead, LENGTH(ll_baike_body) blen FROM ll_wadyx WHERE id=995")->fetch(PDO::FETCH_ASSOC);
foreach ($r as $k=>$v) { echo "$k = $v\n"; }
