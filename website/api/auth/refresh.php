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

// ============================================================
// 提取 Token
// ============================================================
$token = '';
if (!empty($_SERVER['HTTP_AUTHORIZATION'])) {
    $auth = $_SERVER['HTTP_AUTHORIZATION'];
    if (strpos($auth, 'Bearer ') === 0) {
        $token = substr($auth, 7);
    }
}
if (empty($token) && !empty($_GET['token'])) {
    $token = $_GET['token'];
}

if (empty($token)) {
    http_response_code(401);
    echo json_encode(['code' => -1, 'message' => '缺少 Token']);
    exit;
}

// ============================================================
// 解码旧 Token（跳过过期检查）
// ============================================================
try {
    $payload = jwt_decode_auto_skip_expiry($token, $JWT_SECRET);
} catch (JWTException $e) {
    http_response_code(401);
    echo json_encode(['code' => -1, 'message' => 'Token 无效']);
    exit;
}

$uid = (int)($payload['uid'] ?? 0);

// ============================================================
// 查用户基本信息（ll_useregs 实际列名）
// ============================================================
$db   = get_db_connection();
$stmt = $db->prepare('SELECT id, ll_name FROM ll_useregs WHERE id = :uid LIMIT 1');
$stmt->execute([':uid' => $uid]);
$user = $stmt->fetch(PDO::FETCH_ASSOC);

if (!$user) {
    http_response_code(401);
    echo json_encode(['code' => -1, 'message' => '用户不存在']);
    exit;
}

// ============================================================
// 查最新的专业版状态（expires_at 是 BIGINT Unix 时间戳）
// ============================================================
$now = time();
$stmt = $db->prepare(
    'SELECT id, plan, months, amount, activated_at, expires_at
     FROM user_pro_subscriptions
     WHERE user_id = :uid AND status = 1 AND expires_at > :now
     ORDER BY expires_at DESC
     LIMIT 1'
);
$stmt->execute([':uid' => $uid, ':now' => $now]);
$sub = $stmt->fetch(PDO::FETCH_ASSOC);

if ($sub) {
    $pro_activated = 1;
    $pro_expires   = (int)$sub['expires_at'];
    $is_pro        = ($pro_expires > $now);
} else {
    $pro_activated = 0;
    $pro_expires   = 0;
    $is_pro        = false;
}

// ============================================================
// 签发新 JWT
// ============================================================
$new_token = jwt_encode_auto([
    'uid'           => (int)$user['id'],
    'username'      => $user['ll_name'],
    'level'         => $is_pro ? 'pro' : 'free',
    'pro_activated' => $pro_activated,
    'pro_expires'   => $pro_expires,
    'iat'           => $now,
    'exp'           => $now + 86400 * 30,
], $JWT_SECRET);

// ============================================================
// 响应
// ============================================================
echo json_encode([
    'code'    => 0,
    'message' => 'Token 已刷新',
    'data'    => [
        'token'         => $new_token,
        'level'         => $is_pro ? 'pro' : 'free',
        'pro_activated' => $pro_activated,
        'pro_expires'   => $pro_expires,
        'pro_expires_at'=> $pro_expires > 0 ? date('Y-m-d H:i:s', $pro_expires) : null,
    ],
], JSON_UNESCAPED_UNICODE);
