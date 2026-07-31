<?php
/**
 * 7Tan 客户端流量统计 API
 * 
 * 客户端启动时 GET 请求本接口，上报匿名设备标识 + 版本号。
 * 不收集任何个人信息，仅用于日活/留存/版本分布统计。
 * 
 * 请求参数:
 *   id  - 16位匿名设备标识 (必填)
 *   ver - 客户端版本号 (可选)
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

// 版本号默认值
if ($ver === '') {
    $ver = 'unknown';
}

// ── 数据库连接 ──
// 尝试加载现有系统配置
$config_paths = [
    __DIR__ . '/../config.php',
    __DIR__ . '/../include/config.php',
    __DIR__ . '/../db.php',
];

$conn = null;
foreach ($config_paths as $cfg) {
    if (file_exists($cfg)) {
        require_once $cfg;
        break;
    }
}

// 如果系统配置中没有 $conn，尝试独立连接
if (!isset($conn) || !($conn instanceof mysqli)) {
    // ★ 部署时请修改为实际数据库信息
    $db_host = 'localhost';
    $db_user = '7tan';
    $db_pass = '';
    $db_name = '7tan';

    $conn = new mysqli($db_host, $db_user, $db_pass, $db_name);
    if ($conn->connect_error) {
        http_response_code(500);
        echo json_encode(['ok' => false, 'error' => 'db connection failed'], JSON_UNESCAPED_UNICODE);
        exit;
    }
}

$conn->set_charset('utf8mb4');

// ── 确保表存在 ──
$conn->query("
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
// 取第一个 IP（穿透代理时可能是逗号分隔的列表）
$ip = explode(',', $ip)[0];
$ip = trim($ip);

// ── 当前时间 ──
$today = date('Y-m-d');
$now   = date('Y-m-d H:i:s');

// ── 检查设备是否已存在 ──
$stmt = $conn->prepare("SELECT id, first_date FROM 7tan_client_sessions WHERE device_id = ? LIMIT 1");
if (!$stmt) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'db error'], JSON_UNESCAPED_UNICODE);
    exit;
}

$stmt->bind_param('s', $id);
$stmt->execute();
$result = $stmt->get_result();

if ($row = $result->fetch_assoc()) {
    // ── 回头客：更新最后活跃时间 ──
    $stmt->close();

    // 如果 first_date < 今天，标记为"回头客"
    $stmt = $conn->prepare("
        UPDATE 7tan_client_sessions 
        SET version = ?, 
            last_active = ?, 
            ip_address = ?,
            username = IF(? != '', ?, username),
            type = IF(first_date < ?, '回头客', type)
        WHERE device_id = ?
    ");
    $stmt->bind_param('sssssss', $ver, $now, $ip, $user, $user, $today, $id);
    $stmt->execute();
} else {
    // ── 新设备 ──
    $stmt->close();

    $type = '新设备';
    $stmt = $conn->prepare("
        INSERT INTO 7tan_client_sessions 
            (device_id, version, username, first_date, last_active, type, ip_address) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ");
    $stmt->bind_param('sssssss', $id, $ver, $user, $today, $now, $type, $ip);
    $stmt->execute();
}

$stmt->close();
$conn->close();

// ── 返回成功 ──
echo json_encode(['ok' => true], JSON_UNESCAPED_UNICODE);
