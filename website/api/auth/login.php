<?php
// ============================================================
// B2: 登录 API
// POST /api/auth/login.php
// 查 ll_useregs 验证密码 + 查 user_pro_subscriptions 判断专业版
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
    echo json_encode(['code' => -1, 'message' => '仅支持 POST 请求']);
    exit;
}

// ============================================================
// 配置
// ============================================================
require_once __DIR__ . '/../../config/database.php';
require_once __DIR__ . '/../../lib/jwt_helper.php';

$JWT_SECRET = defined('JWT_SECRET') ? JWT_SECRET : 'change-me-to-a-random-64-char-string';
$JWT_ISSUER = '7tan.com';
$JWT_EXPIRE = 30 * 24 * 3600;  // 30 天

// ============================================================
// 获取输入（兼容客户端 username + 旧版 account）
// ============================================================
$input = json_decode(file_get_contents('php://input'), true);

if (!$input) {
    http_response_code(400);
    echo json_encode(['code' => -1, 'message' => '请提供 JSON 请求体']);
    exit;
}

$account  = trim($input['username'] ?? $input['account'] ?? '');
$password = trim($input['password'] ?? '');

if ($account === '' || $password === '') {
    http_response_code(400);
    echo json_encode(['code' => -1, 'message' => '账号和密码不能为空']);
    exit;
}

// ============================================================
// 查询用户（兼容用户名/手机号/邮箱登录）
// ============================================================
$db   = get_db_connection();
$stmt = $db->prepare(
    'SELECT id, username, password, salt, phone, email, status
     FROM ll_useregs
     WHERE username = :account OR phone = :account2 OR email = :account3
     LIMIT 1'
);
$stmt->execute([
    ':account'  => $account,
    ':account2' => $account,
    ':account3' => $account,
]);
$user = $stmt->fetch(PDO::FETCH_ASSOC);

if (!$user) {
    http_response_code(401);
    echo json_encode(['code' => -1, 'message' => '账号或密码错误']);
    exit;
}

// 检查账号状态
if ((int)$user['status'] !== 1) {
    http_response_code(403);
    echo json_encode(['code' => -1, 'message' => '账号已被禁用，请联系管理员']);
    exit;
}

// ============================================================
// 验证密码（兼容 md5+salt 和 password_hash 两种格式）
// ============================================================
$password_ok = false;

if (!empty($user['salt']) && strlen($user['salt']) >= 6) {
    // 旧格式: md5(md5(password) + salt)
    $password_ok = (md5(md5($password) . $user['salt']) === $user['password']);
} else {
    // 新格式: password_hash
    $password_ok = password_verify($password, $user['password']);
}

if (!$password_ok) {
    http_response_code(401);
    echo json_encode(['code' => -1, 'message' => '账号或密码错误']);
    exit;
}

// ============================================================
// 查询专业版状态（从新建的 user_pro_subscriptions 表）
// ============================================================
$now = time();

$stmt = $db->prepare(
    'SELECT id, plan, months, amount, activated_at, expires_at
     FROM user_pro_subscriptions
     WHERE user_id = :uid AND status = 1 AND expires_at > NOW()
     ORDER BY expires_at DESC
     LIMIT 1'
);
$stmt->execute([':uid' => $user['id']]);
$sub = $stmt->fetch(PDO::FETCH_ASSOC);

$pro_activated = $sub ? 1 : 0;
$pro_expires   = $sub ? strtotime($sub['expires_at']) : 0;
$is_pro        = ($pro_activated === 1 && $pro_expires > $now);

// ============================================================
// 签发 JWT（RS256）
// ============================================================
$payload = [
    'iss'            => $JWT_ISSUER,
    'iat'            => $now,
    'exp'            => $now + $JWT_EXPIRE,
    'uid'            => (int)$user['id'],
    'username'       => $user['username'],
    'level'          => $is_pro ? 'pro' : 'free',
    'pro_activated'  => $pro_activated,
    'pro_expires'    => $pro_expires,
];

$token = generate_jwt($payload, $JWT_SECRET);

// ============================================================
// 返回
// ============================================================
echo json_encode([
    'code'    => 0,
    'message' => '登录成功',
    'data'    => [
        'token'  => $token,
        'expire' => $now + $JWT_EXPIRE,
        'user'   => [
            'uid'            => (int)$user['id'],
            'username'       => $user['username'],
            'phone'          => $user['phone'],
            'email'          => $user['email'],
            'level'          => $is_pro ? 'pro' : 'free',
            'pro_activated'  => $pro_activated,
            'pro_expires'    => $pro_expires,
            'pro_expires_at' => $pro_expires > 0 ? date('Y-m-d H:i:s', $pro_expires) : null,
        ],
    ],
], JSON_UNESCAPED_UNICODE);
