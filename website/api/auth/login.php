<?php
// ============================================================
// B2: 登录 API
// POST /api/auth/login.php
// 验证用户名密码 → 查询专业版状态 → 签发 JWT
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

// ============================================================
// 解析请求
// ============================================================
$input = json_decode(file_get_contents('php://input'), true);
if (!$input) {
    http_response_code(400);
    echo json_encode(['code' => -1, 'message' => '请求格式错误']);
    exit;
}

// 兼容客户端发 username 或 account
$username = $input['username'] ?? $input['account'] ?? '';
$password = $input['password'] ?? '';

if (empty($username) || empty($password)) {
    http_response_code(400);
    echo json_encode(['code' => -1, 'message' => '用户名和密码不能为空']);
    exit;
}

// ============================================================
// 查用户（ll_useregs 实际列名：ll_name / ll_pass）
// ============================================================
$db   = get_db_connection();
$stmt = $db->prepare(
    'SELECT id, ll_name, ll_pass, ll_shouji, ll_mail
     FROM ll_useregs
     WHERE ll_name = :name1 OR ll_shouji = :name2 OR ll_mail = :name3
     LIMIT 1'
);
$stmt->execute([':name1' => $username, ':name2' => $username, ':name3' => $username]);
$user = $stmt->fetch(PDO::FETCH_ASSOC);

if (!$user) {
    http_response_code(401);
    echo json_encode(['code' => -1, 'message' => '账号或密码错误']);
    exit;
}

// 密码直接对比（如果网站用 MD5，改为 md5($password) === $user['ll_pass']）
if ($password !== $user['ll_pass']) {
    http_response_code(401);
    echo json_encode(['code' => -1, 'message' => '账号或密码错误']);
    exit;
}

// ============================================================
// 查询专业版状态（user_pro_subscriptions 表，expires_at 是 BIGINT Unix 时间戳）
// ============================================================
$now = time();
$stmt = $db->prepare(
    'SELECT id, plan, months, amount, activated_at, expires_at
     FROM user_pro_subscriptions
     WHERE user_id = :uid AND status = 1 AND expires_at > :now
     ORDER BY expires_at DESC
     LIMIT 1'
);
$stmt->execute([':uid' => $user['id'], ':now' => $now]);
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
// 签发 JWT
// ============================================================
$token = jwt_encode_auto([
    'uid'           => (int)$user['id'],
    'username'      => $user['ll_name'],
    'level'         => $is_pro ? 'pro' : 'free',
    'pro_activated' => $pro_activated,
    'pro_expires'   => $pro_expires,
    'iat'           => $now,
    'exp'           => $now + 86400 * 30, // 30天过期
], $JWT_SECRET);

// ============================================================
// 设置 auth_token Cookie（供 pro.php 等页面读取）
// ============================================================
setcookie('auth_token', $token, [
    'expires'  => $now + 86400 * 30,
    'path'     => '/',
    'domain'   => '',
    'secure'   => false,
    'httponly' => false,
    'samesite' => 'Lax',
]);

// ============================================================
// 响应
// ============================================================
echo json_encode([
    'code'    => 0,
    'message' => '登录成功',
    'data'    => [
        'token'         => $token,
        'user'          => [
            'uid'           => (int)$user['id'],
            'username'      => $user['ll_name'],
            'phone'         => $user['ll_shouji'] ?? '',
            'email'         => $user['ll_mail'] ?? '',
            'level'         => $is_pro ? 'pro' : 'free',
            'pro_activated' => $pro_activated,
            'pro_expires'   => $pro_expires,
            'pro_expires_at'=> $pro_expires > 0 ? date('Y-m-d H:i:s', $pro_expires) : null,
        ],
    ],
], JSON_UNESCAPED_UNICODE);
