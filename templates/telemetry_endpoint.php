<?php
/**
 * 7Tan 专业版水印回传接收端点（运行时上报 第③层）
 *
 * 部署位置：网站 api/telemetry/build.php
 * 数据落盘：同目录 telemetry.log（jsonl 格式，每行一条）
 *
 * 客户端上报内容（POST JSON）：
 *   build_id   : 水印标识 PRO-YYYYMMDD-HHMMSS-XXXX
 *   build_user : 购买者 UID
 *   version    : 构建时间
 *   platform   : 操作系统
 *   ts         : 上报时间戳
 *
 * 安全：只记录来源 IP + 水印，不含用户隐私数据。
 * 用途：追踪专业包活跃情况；泄露时凭 build_id 反查购买者 → 封号。
 */
header('Content-Type: application/json; charset=utf-8');

$raw = file_get_contents('php://input');
$d = json_decode($raw, true);
if (!is_array($d)) {
    $d = [];
}

$line = json_encode([
    't'         => date('c'),
    'ip'        => $_SERVER['REMOTE_ADDR'] ?? '',
    'build_id'  => $d['build_id'] ?? '',
    'build_user'=> $d['build_user'] ?? '',
    'version'   => $d['version'] ?? '',
    'platform'  => $d['platform'] ?? '',
    'ts'        => $d['ts'] ?? 0,
], JSON_UNESCAPED_UNICODE) . "\n";

$log = __DIR__ . '/telemetry.log';
@file_put_contents($log, $line, FILE_APPEND | LOCK_EX);

echo json_encode(['ok' => 1]);
