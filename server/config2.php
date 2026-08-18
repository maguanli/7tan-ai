<?php
/**
 * 7Tan 服务端配置文件
 * 与管理后台共用同一个数据库 7tan_cn
 * 泼猴用 pc_client_sessions 表，7Tan 用 7tan_client_sessions 表，互不干扰
 */

// ── 数据库 ──
$db_host = 'localhost';
$db_user = 'root';
$db_pass = getenv('DB_PASS') ?: '修改为你的数据库密码';
$db_name = '7tan_cn';

$conn = new mysqli($db_host, $db_user, $db_pass, $db_name);

if ($conn->connect_error) {
    http_response_code(500);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['ok' => false, 'error' => 'db connection failed: ' . $conn->connect_error], JSON_UNESCAPED_UNICODE);
    exit;
}

$conn->set_charset('utf8mb4');

// ── 会话 ──
define('SESSION_TIMEOUT', 3600);  // 会话超时 1 小时
