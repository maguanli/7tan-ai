<?php
// ============================================================
// B5b: 查询专业版状态
// GET /api/pro/status.php
// ============================================================

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

require_once __DIR__ . '/../../config/database.php';
require_once __DIR__ . '/../../lib/jwt_helper.php';
require_once __DIR__ . '/../../lib/auth_middleware.php';

$JWT_SECRET = defined('JWT_SECRET') ? JWT_SECRET : 'change-me-to-a-random-64-char-string';

$user = require_login($JWT_SECRET);
$uid  = (int)$user['uid'];

$db   = get_db_connection();
$stmt = $db->prepare(
    'SELECT u.id, u.username, u.pro_activated, u.pro_expires,
            COALESCE(b.balance, 0) AS balance
     FROM ll_useregs u
     LEFT JOIN user_balance b ON u.id = b.user_id
     WHERE u.id = :uid
     LIMIT 1'
);
$stmt->execute([':uid' => $uid]);
$row = $stmt->fetch(PDO::FETCH_ASSOC);

if (!$row) {
    http_response_code(404);
    echo json_encode(['code' => -1, 'message' => '用户不存在']);
    exit;
}

$now           = time();
$pro_activated = (int)($row['pro_activated'] ?? 0);
$pro_expires   = (int)($row['pro_expires']   ?? 0);
$is_pro        = ($pro_activated === 1 && $pro_expires > $now);

// 计算剩余天数
$remaining_days = 0;
$remaining_text = '未激活';
if ($is_pro) {
    $remaining_days = max(0, (int)(($pro_expires - $now) / 86400));
    $remaining_text = $remaining_days . ' 天';
} elseif ($pro_expires > 0) {
    $remaining_text = '已过期';
}

echo json_encode([
    'code'    => 0,
    'message' => 'ok',
    'data'    => [
        'uid'            => (int)$row['id'],
        'username'       => $row['username'],
        'level'          => $is_pro ? 'pro' : 'free',
        'pro_activated'  => $pro_activated,
        'pro_expires'    => $pro_expires,
        'pro_expires_at' => $pro_expires > 0 ? date('Y-m-d H:i:s', $pro_expires) : null,
        'remaining_days' => $remaining_days,
        'remaining_text' => $remaining_text,
        'balance'        => (float)$row['balance'],
        'server_time'    => $now,
    ],
], JSON_UNESCAPED_UNICODE);
