<?php
// ============================================================
// B5b: 查询专业版状态
// GET /api/pro/status.php
// 查 user_pro_subscriptions 表（不查 ll_useregs）
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

$db = get_db_connection();

// 查用户基本信息
$stmt = $db->prepare('SELECT id, username FROM ll_useregs WHERE id = :uid LIMIT 1');
$stmt->execute([':uid' => $uid]);
$row = $stmt->fetch(PDO::FETCH_ASSOC);

if (!$row) {
    http_response_code(404);
    echo json_encode(['code' => -1, 'message' => '用户不存在']);
    exit;
}

// 查专业版订阅状态（新表）
$stmt = $db->prepare(
    'SELECT id, plan, months, amount, activated_at, expires_at
     FROM user_pro_subscriptions
     WHERE user_id = :uid AND status = 1 AND expires_at > NOW()
     ORDER BY expires_at DESC
     LIMIT 1'
);
$stmt->execute([':uid' => $uid]);
$sub = $stmt->fetch(PDO::FETCH_ASSOC);

$now = time();

if ($sub) {
    $pro_activated   = 1;
    $pro_expires     = strtotime($sub['expires_at']);
    $remaining_days  = max(0, (int)(($pro_expires - $now) / 86400));
    $remaining_text  = $remaining_days . ' 天';
    $level           = 'pro';
} else {
    $pro_activated   = 0;
    $pro_expires     = 0;
    $remaining_days  = 0;
    $remaining_text  = '未激活';
    $level           = 'free';
}

// 查余额
$stmt = $db->prepare('SELECT balance FROM user_balance WHERE user_id = :uid LIMIT 1');
$stmt->execute([':uid' => $uid]);
$balance = $stmt->fetchColumn();
$balance = $balance !== false ? (float)$balance : 0.00;

echo json_encode([
    'code'    => 0,
    'message' => 'ok',
    'data'    => [
        'uid'            => (int)$row['id'],
        'username'       => $row['username'],
        'level'          => $level,
        'pro_activated'  => $pro_activated,
        'pro_expires'    => $pro_expires,
        'pro_expires_at' => $pro_expires > 0 ? date('Y-m-d H:i:s', $pro_expires) : null,
        'remaining_days' => $remaining_days,
        'remaining_text' => $remaining_text,
        'balance'        => $balance,
        'server_time'    => $now,
    ],
], JSON_UNESCAPED_UNICODE);
