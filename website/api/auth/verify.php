<?php
// ============================================================
// B3: 验证 Token + 返回会员状态
// GET /api/auth/verify.php
// 客户端离线验签失败时调此接口在线验证
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
// 获取 Token
// ============================================================
$token = '';

// 方式1: Authorization header (Bearer xxx)
$auth_header = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
if (preg_match('/Bearer\s+(.+)/i', $auth_header, $m)) {
    $token = $m[1];
}

// 方式2: query string ?token=xxx
if ($token === '' && !empty($_GET['token'])) {
    $token = $_GET['token'];
}

if ($token === '') {
    http_response_code(401);
    echo json_encode(['code' => -1, 'message' => '缺少 Token', 'data' => ['level' => 'free']]);
    exit;
}

// ============================================================
// 验证 JWT
// ============================================================
try {
    $payload = jwt_decode($token, $JWT_SECRET);
} catch (Exception $e) {
    http_response_code(401);
    echo json_encode([
        'code'    => -1,
        'message' => 'Token 无效: ' . $e->getMessage(),
        'data'    => ['level' => 'free'],
    ]);
    exit;
}

$uid = (int)($payload['uid'] ?? 0);

// ============================================================
// 查数据库获取最新状态（比 Token 里存的更实时）
// ============================================================
$db   = get_db_connection();
$stmt = $db->prepare('SELECT id, username, pro_activated, pro_expires FROM ll_useregs WHERE id = :uid LIMIT 1');
$stmt->execute([':uid' => $uid]);
$user = $stmt->fetch(PDO::FETCH_ASSOC);

if (!$user) {
    http_response_code(401);
    echo json_encode(['code' => -1, 'message' => '用户不存在', 'data' => ['level' => 'free']]);
    exit;
}

$now           = time();
$pro_activated = (int)($user['pro_activated'] ?? 0);
$pro_expires   = (int)($user['pro_expires']   ?? 0);
$is_pro        = ($pro_activated === 1 && $pro_expires > $now);

// ============================================================
// 响应
// ============================================================
echo json_encode([
    'code'    => 0,
    'message' => 'ok',
    'data'    => [
        'uid'           => (int)$user['id'],
        'username'      => $user['username'],
        'level'         => $is_pro ? 'pro' : 'free',
        'pro_activated' => $pro_activated,
        'pro_expires'   => $pro_expires,
        'pro_expires_at'=> $pro_expires > 0 ? date('Y-m-d H:i:s', $pro_expires) : null,
        'server_time'   => $now,
    ],
], JSON_UNESCAPED_UNICODE);
