<?php
// ============================================================
// 设备指纹上报 + 多设备检测（防转卖溯源）
// POST /api/auth/device.php
//
// 客户端登录成功后异步上报设备指纹；
// 服务器记录设备，并检测同一账号是否在过多设备上登录（转卖/共享预警）。
//
// 请求: {"token": "...", "device_id": "32位hex", "fingerprint": "sha256",
//        "device_name": "主机名", "os_info": "Windows 10"}
// 响应: {"code":0, "data": {"device_id":"...", "device_count":1,
//        "device_limit":3, "suspicious":0, "warn":""}}
// ============================================================

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['code' => -1, 'message' => '仅支持 POST']);
    exit;
}

require_once __DIR__ . '/../../config/database.php';
require_once __DIR__ . '/../../lib/jwt_helper.php';

$JWT_SECRET = defined('JWT_SECRET') ? JWT_SECRET : 'change-me-to-a-random-64-char-string';

// 设备数阈值：超过即标记可疑（转卖/共享）
if (!defined('DEVICE_LIMIT')) { define('DEVICE_LIMIT', 3); }

$input = json_decode(file_get_contents('php://input'), true);
if (!$input) {
    http_response_code(400);
    echo json_encode(['code' => -1, 'message' => '请求格式错误']);
    exit;
}

$token       = $input['token'] ?? '';
$device_id   = trim((string)($input['device_id'] ?? ''));
$fingerprint = trim((string)($input['fingerprint'] ?? ''));
$device_name = trim((string)($input['device_name'] ?? ''));
$os_info     = trim((string)($input['os_info'] ?? ''));

if (empty($token)) {
    http_response_code(401);
    echo json_encode(['code' => -1, 'message' => '请先登录']);
    exit;
}
if (empty($device_id) || empty($fingerprint)) {
    http_response_code(400);
    echo json_encode(['code' => -1, 'message' => '缺少设备指纹']);
    exit;
}

// ============================================================
// 验证 JWT
// ============================================================
try {
    $payload = jwt_decode_auto($token, $JWT_SECRET);
} catch (Exception $e) {
    http_response_code(401);
    echo json_encode(['code' => -1, 'message' => '令牌无效或已过期']);
    exit;
}
$uid = (int)($payload['uid'] ?? 0);
if ($uid <= 0) {
    http_response_code(401);
    echo json_encode(['code' => -1, 'message' => '令牌无效']);
    exit;
}

$db = get_db_connection();

// ============================================================
// 自动建表（首次请求自动创建，无需手动执行 SQL）
// ============================================================
$db->exec("CREATE TABLE IF NOT EXISTS user_devices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    device_id VARCHAR(64) NOT NULL,
    fingerprint VARCHAR(128) NOT NULL DEFAULT '',
    device_name VARCHAR(128) NOT NULL DEFAULT '',
    os_info VARCHAR(128) NOT NULL DEFAULT '',
    ip VARCHAR(64) NOT NULL DEFAULT '',
    first_seen INT NOT NULL,
    last_seen INT NOT NULL,
    login_count INT NOT NULL DEFAULT 1,
    suspicious TINYINT NOT NULL DEFAULT 0,
    UNIQUE KEY uk_user_device (user_id, device_id),
    KEY idx_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");

// ============================================================
// UPSERT 设备记录（同一设备重复上报只累加次数）
// 注意：PDO 原生预处理模式（EMULATE_PREPARES=false）下
//       命名参数必须唯一，不能重复出现，故全部用独立参数名
// ============================================================
$now = time();
$ip  = $_SERVER['REMOTE_ADDR'] ?? '';

$stmt = $db->prepare(
    'INSERT INTO user_devices (user_id, device_id, fingerprint, device_name, os_info, ip, first_seen, last_seen, login_count)
     VALUES (:uid, :did, :fp, :dn, :os, :ip, :ts1, :ts2, 1)
     ON DUPLICATE KEY UPDATE
       last_seen   = :ts3,
       login_count = login_count + 1,
       fingerprint = :fp2,
       device_name = :dn2,
       os_info     = :os2,
       ip          = :ip2'
);
$stmt->execute([
    ':uid' => $uid,
    ':did' => $device_id,
    ':fp'  => $fingerprint,
    ':dn'  => $device_name,
    ':os'  => $os_info,
    ':ip'  => $ip,
    ':ts1' => $now,
    ':ts2' => $now,
    ':ts3' => $now,
    ':fp2' => $fingerprint,
    ':dn2' => $device_name,
    ':os2' => $os_info,
    ':ip2' => $ip,
]);

// ============================================================
// 多设备检测
// ============================================================
$stmt = $db->prepare('SELECT COUNT(*) AS cnt, MAX(suspicious) AS sus FROM user_devices WHERE user_id = :uid');
$stmt->execute([':uid' => $uid]);
$row = $stmt->fetch(PDO::FETCH_ASSOC);
$device_count = (int)($row['cnt'] ?? 0);
$suspicious   = (int)($row['sus'] ?? 0);

// 超过阈值 → 标记可疑（只标记不封号，供管理员后续处理）
if ($device_count > DEVICE_LIMIT && !$suspicious) {
    $db->prepare('UPDATE user_devices SET suspicious = 1 WHERE user_id = :uid')
       ->execute([':uid' => $uid]);
    $suspicious = 1;
}

echo json_encode([
    'code'    => 0,
    'message' => 'ok',
    'data'    => [
        'device_id'    => $device_id,
        'device_count' => $device_count,
        'device_limit' => DEVICE_LIMIT,
        'suspicious'   => $suspicious,
        'warn'         => $device_count > DEVICE_LIMIT
            ? "您的账号已在 {$device_count} 台设备上使用，如非本人操作请及时修改密码"
            : '',
    ],
], JSON_UNESCAPED_UNICODE);
