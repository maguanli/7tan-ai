<?php
// ============================================================
// B2: 登录 API
// POST /api/auth/login.php
// 集成现有 ll_useregs 表，返回含 pro_expires 的 JWT
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
// 配置（请根据实际环境修改）
// ============================================================
require_once __DIR__ . '/../../config/database.php';  // 数据库连接
require_once __DIR__ . '/../../lib/jwt_helper.php';     // JWT 工具类

$JWT_SECRET    = defined('JWT_SECRET') ? JWT_SECRET : 'change-me-to-a-random-64-char-string';
$JWT_ISSUER    = '7tan.com';
$JWT_EXPIRE    = 30 * 24 * 3600;  // 30 天

// ============================================================
// 获取输入
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
    'SELECT id, username, phone, email, password, pro_activated, pro_expires
     FROM ll_useregs
     WHERE username = :a OR phone = :a OR email = :a
     LIMIT 1'
);
$stmt->execute([':a' => $account]);
$user = $stmt->fetch(PDO::FETCH_ASSOC);

if (!$user) {
    http_response_code(401);
    echo json_encode(['code' => -1, 'message' => '账号不存在']);
    exit;
}

// ============================================================
// 验证密码（兼容 md5 / password_hash 两种格式）
// ============================================================
$password_ok = false;

// 优先用 password_verify（新格式）
if (password_get_info($user['password'])['algo'] !== null) {
    $password_ok = password_verify($password, $user['password']);
} else {
    // 兼容旧版 md5（如果网站在用）
    $password_ok = (md5($password) === $user['password']);
}

if (!$password_ok) {
    http_response_code(401);
    echo json_encode(['code' => -1, 'message' => '密码错误']);
    exit;
}

// ============================================================
// 判断专业版状态
// ============================================================
$now           = time();
$pro_activated = (int)($user['pro_activated'] ?? 0);
$pro_expires   = (int)($user['pro_expires']   ?? 0);
$is_pro        = ($pro_activated === 1 && $pro_expires > $now);

// ============================================================
// 签发 JWT
// ============================================================
$payload = [
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

$token = jwt_encode_auto($payload, $JWT_SECRET);

// ============================================================
// 响应
// ============================================================
echo json_encode([
    'code'    => 0,
    'message' => '登录成功',
    'data'    => [
        'token'        => $token,
        'user'         => [
            'uid'           => (int)$user['id'],
            'username'      => $user['username'],
            'phone'         => $user['phone'],
            'email'         => $user['email'],
            'level'         => $is_pro ? 'pro' : 'free',
            'pro_activated' => $pro_activated,
            'pro_expires'   => $pro_expires,
            'pro_expires_at'=> $pro_expires > 0 ? date('Y-m-d H:i:s', $pro_expires) : null,
        ],
    ],
], JSON_UNESCAPED_UNICODE);
