<?php
// ============================================================
// B4: 刷新 Token（续费/升级后调用）
// GET /api/auth/refresh.php
// 用户续费后点 [刷新状态] → 重新签发含最新 pro_expires 的 JWT
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

$JWT_SECRET = defined('JWT_SECRET') ? JWT_SECRET : 'change-me-to-a-random-64-char-string';
$JWT_ISSUER = '7tan.com';
$JWT_EXPIRE = 30 * 24 * 3600;  // 30 天

// ============================================================
// 获取 Token
// ============================================================
$token = '';
$auth_header = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
if (preg_match('/Bearer\s+(.+)/i', $auth_header, $m)) {
    $token = $m[1];
}
if ($token === '' && !empty($_GET['token'])) {
    $token = $_GET['token'];
}

if ($token === '') {
    http_response_code(401);
    echo json_encode(['code' => -1, 'message' => '缺少 Token']);
    exit;
}

// ============================================================
// 解析旧 Token（允许已过期的 Token，只要签名有效）
// ============================================================
try {
    // 验证签名但不检查过期时间
    $payload = jwt_decode_skip_expiry($token, $JWT_SECRET);
} catch (Exception $e) {
    http_response_code(401);
    echo json_encode(['code' => -1, 'message' => 'Token 无效: ' . $e->getMessage()]);
    exit;
}

$uid = (int)($payload['uid'] ?? 0);

// ============================================================
// 查数据库获取最新状态
// ============================================================
$db   = get_db_connection();
$stmt = $db->prepare('SELECT id, username, pro_activated, pro_expires FROM ll_useregs WHERE id = :uid LIMIT 1');
$stmt->execute([':uid' => $uid]);
$user = $stmt->fetch(PDO::FETCH_ASSOC);

if (!$user) {
    http_response_code(401);
    echo json_encode(['code' => -1, 'message' => '用户不存在']);
    exit;
}

$now           = time();
$pro_activated = (int)($user['pro_activated'] ?? 0);
$pro_expires   = (int)($user['pro_expires']   ?? 0);
$is_pro        = ($pro_activated === 1 && $pro_expires > $now);

// ============================================================
// 签发新 Token（含最新状态）
// ============================================================
$new_payload = [
    'iss'          => $JWT_ISSUER,
    'iat'          => $now,
    'exp'          => $now + $JWT_EXPIRE,
    'uid'          => (int)$user['id'],
    'username'     => $user['username'],
    'level'        => $is_pro ? 'pro' : 'free',
    'pro_activated'=> $pro_activated,
    'pro_expires'  => $pro_expires,
    'jti'          => bin2hex(random_bytes(16)),
];

$new_token = jwt_encode($new_payload, $JWT_SECRET);

// ============================================================
// 响应
// ============================================================
echo json_encode([
    'code'    => 0,
    'message' => 'Token 已刷新',
    'data'    => [
        'token'         => $new_token,
        'uid'           => (int)$user['id'],
        'username'      => $user['username'],
        'level'         => $is_pro ? 'pro' : 'free',
        'pro_activated' => $pro_activated,
        'pro_expires'   => $pro_expires,
        'pro_expires_at'=> $pro_expires > 0 ? date('Y-m-d H:i:s', $pro_expires) : null,
    ],
], JSON_UNESCAPED_UNICODE);
