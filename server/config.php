<?php
/**
 * 7Tan 服务端配置文件
 * 
 * 部署时修改下面的数据库连接信息
 */

// ── 数据库连接 ──
$db_host = 'localhost';
$db_user = '7tan';
$db_pass = '';          // ★ 部署时填写实际密码
$db_name = '7tan';      // ★ 如需独立数据库，修改此处

$conn = new mysqli($db_host, $db_user, $db_pass, $db_name);

if ($conn->connect_error) {
    http_response_code(500);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['ok' => false, 'error' => 'db connection failed: ' . $conn->connect_error], JSON_UNESCAPED_UNICODE);
    exit;
}

$conn->set_charset('utf8mb4');
