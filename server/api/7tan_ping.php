<?php
/**
 * 7Tan 客户端流量统计 API
 * 
 * 客户端启动时 GET 请求本接口，上报匿名设备标识 + 版本号。
 * 不收集任何个人信息，仅用于日活/留存/版本分布统计。
 * 
 * 请求参数:
 *   id   - 16位匿名设备标识 (必填)
 *   ver  - 客户端版本号 (可选)
 *   user - 用户名 (可选，用于关联)
 * 
 * 返回:
 *   {"ok": true}  成功
 *   {"ok": false, "error": "..."}  失败
 */

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Cache-Control: no-store, no-cache, must-revalidate');

// ── 参数验证 ──
$id  = trim($_GET['id']  ?? '');
$ver = trim($_GET['ver'] ?? '');
$user = trim($_GET['user'] ?? '');

if (strlen($id) < 16) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'invalid id'], JSON_UNESCAPED_UNICODE);
    exit;
}

if ($ver === '') {
    $ver = 'unknown';
}

// ── 加载管理后台配置（使用 getDB() PDO 连接）──
$config_file = __DIR__ . '/../config.php';
if (!file_exists($config_file)) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'config.php not found'], JSON_UNESCAPED_UNICODE);
    exit;
}
require_once $config_file;

// 使用 config.php 提供的 getDB() 获取 PDO 连接
if (!function_exists('getDB')) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'getDB() not found in config.php'], JSON_UNESCAPED_UNICODE);
    exit;
}

try {
    $db = getDB();
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'db connection failed'], JSON_UNESCAPED_UNICODE);
    exit;
}

// ── 确保表存在 ──
$db->exec("
    CREATE TABLE IF NOT EXISTS `7tan_client_sessions` (
        `id` INT AUTO_INCREMENT PRIMARY KEY,
        `device_id` VARCHAR(32) NOT NULL,
        `version` VARCHAR(16) DEFAULT 'unknown',
        `username` VARCHAR(64) DEFAULT '',
        `first_date` DATE NOT NULL,
        `last_active` DATETIME NOT NULL,
        `type` VARCHAR(10) DEFAULT '新设备',
        `ip_address` VARCHAR(45) DEFAULT '',
        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX `idx_device` (`device_id`),
        INDEX `idx_last_active` (`last_active`),
        INDEX `idx_first_date` (`first_date`),
        INDEX `idx_type` (`type`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
");

// ── 获取客户端 IP ──
$ip = $_SERVER['HTTP_X_FORWARDED_FOR'] ?? $_SERVER['HTTP_X_REAL_IP'] ?? $_SERVER['REMOTE_ADDR'] ?? '';
$ip = explode(',', $ip)[0];
$ip = trim($ip);

// ── 当前时间 ──
$today = date('Y-m-d');
$now   = date('Y-m-d H:i:s');

// ── 检查设备是否已存在 ──
$stmt = $db->prepare("SELECT id, first_date FROM 7tan_client_sessions WHERE device_id = ? LIMIT 1");
$stmt->execute([$id]);
$row = $stmt->fetch();

if ($row) {
    // ── 回头客：更新最后活跃时间 ──
    $stmt = $db->prepare("
        UPDATE 7tan_client_sessions 
        SET version = :ver, 
            last_active = :now, 
            ip_address = :ip,
            username = IF(:user != '', :user2, username),
            type = IF(first_date < :today, '回头客', type)
        WHERE device_id = :id
    ");
    $stmt->execute([
        ':ver' => $ver,
        ':now' => $now,
        ':ip' => $ip,
        ':user' => $user,
        ':user2' => $user,
        ':today' => $today,
        ':id' => $id,
    ]);
} else {
    // ── 新设备 ──
    $stmt = $db->prepare("
        INSERT INTO 7tan_client_sessions 
            (device_id, version, username, first_date, last_active, type, ip_address) 
        VALUES (:id, :ver, :user, :today, :now, '新设备', :ip)
    ");
    $stmt->execute([
        ':id' => $id,
        ':ver' => $ver,
        ':user' => $user,
        ':today' => $today,
        ':now' => $now,
        ':ip' => $ip,
    ]);
}

// ── 返回成功 ──
echo json_encode(['ok' => true], JSON_UNESCAPED_UNICODE);
