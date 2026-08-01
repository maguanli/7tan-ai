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
$db = get_db_connection();

// 先尝试查含 trial_ai_count，如果列不存在则回退
try {
    $stmt = $db->prepare(
        'SELECT id, ll_name, ll_pass, ll_shouji, ll_mail, trial_ai_count
         FROM ll_useregs
         WHERE ll_name = :name1 OR ll_shouji = :name2 OR ll_mail = :name3
         LIMIT 1'
    );
    $stmt->execute([':name1' => $username, ':name2' => $username, ':name3' => $username]);
    $user = $stmt->fetch(PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    // trial_ai_count 列尚不存在 → 回退查询（等执行 migration.sql 后自动恢复）
    $stmt = $db->prepare(
        'SELECT id, ll_name, ll_pass, ll_shouji, ll_mail
         FROM ll_useregs
         WHERE ll_name = :name1 OR ll_shouji = :name2 OR ll_mail = :name3
         LIMIT 1'
    );
    $stmt->execute([':name1' => $username, ':name2' => $username, ':name3' => $username]);
    $user = $stmt->fetch(PDO::FETCH_ASSOC);
}

if (!$user) {
    http_response_code(401);
    echo json_encode(['code' => -1, 'message' => '账号或密码错误']);
    exit;
}

// 密码比对（兼容 MD5 哈希和明文两种存储格式）
// v2.1 — 2026-07-29 15:15 明文优先
$password_ok = ($user['ll_pass'] === $password || $user['ll_pass'] === md5($password));
if (!$password_ok) {
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
// 同步 BBS Session（让 BBS 和 API 互通登录状态）
// ============================================================
if (session_status() === PHP_SESSION_NONE) {
    session_start();
}
$_SESSION['user_id'] = (int)$user['id'];
$_SESSION['user_name'] = $user['ll_name'];
$_SESSION['user_nickname'] = $user['ll_n_name'] ?? $user['ll_name'];

$trial_ai_count = (int)($user['trial_ai_count'] ?? 0);

// ============================================================
// 签发 JWT
// ============================================================
$token = jwt_encode_auto([
    'uid'            => (int)$user['id'],
    'username'       => $user['ll_name'],
    'level'          => $is_pro ? 'pro' : 'free',
    'pro_activated'  => $pro_activated,
    'pro_expires'    => $pro_expires,
    'trial_ai_count' => $trial_ai_count,    // 试用的 AI 次数（0=已用完）
    'iat'            => $now,
    'exp'            => $now + 86400 * 30,  // 30天过期
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
// 签发 PRO License（RSA 签名，供客户端离线验签防伪造）
// 仅 PRO 用户有此项；公钥内置在客户端软件中
// ============================================================
$pro_license = null;
if ($is_pro) {
    $pk_path = defined('RSA_PRIVATE_KEY_PATH') ? RSA_PRIVATE_KEY_PATH : '';
    if ($pk_path && file_exists($pk_path)) {
        $pk = file_get_contents($pk_path);
        $license_data = json_encode([
            'uid'         => (int)$user['id'],
            'level'       => 'pro',
            'pro_expires' => $pro_expires,
            'issued_at'   => $now,
        ]);
        $sig = '';
        if (openssl_sign($license_data, $sig, $pk, 'sha256WithRSAEncryption')) {
            // 格式: base64url(signature).base64url(payload)
            $pro_license = base64url_encode($sig) . '.' . base64url_encode($license_data);
        }
    }
}

// ============================================================
// 设备统计（登录时附带回传，供客户端多设备提醒）
// ============================================================
$device_count = 0;
$device_suspicious = 0;
if (!defined('DEVICE_LIMIT')) { define('DEVICE_LIMIT', 3); }
try {
    $stmt = $db->prepare('SELECT COUNT(*) AS cnt, MAX(suspicious) AS sus FROM user_devices WHERE user_id = :uid');
    $stmt->execute([':uid' => $user['id']]);
    $drow = $stmt->fetch(PDO::FETCH_ASSOC);
    $device_count = (int)($drow['cnt'] ?? 0);
    $device_suspicious = (int)($drow['sus'] ?? 0);
} catch (PDOException $e) {
    // user_devices 表不存在（设备指纹功能未启用）→ 忽略
}

// ============================================================
// 响应
// ============================================================
echo json_encode([
    'code'    => 0,
    'message' => '登录成功',
    'data'    => [
        'token'       => $token,
        'pro_license' => $pro_license,   // RSA 签名的 PRO 授权凭证
        'user'        => [
            'uid'           => (int)$user['id'],
            'username'      => $user['ll_name'],
            'phone'         => $user['ll_shouji'] ?? '',
            'email'         => $user['ll_mail'] ?? '',
            'level'          => $is_pro ? 'pro' : 'free',
            'pro_activated'  => $pro_activated,
            'pro_expires'    => $pro_expires,
            'pro_expires_at' => $pro_expires > 0 ? date('Y-m-d H:i:s', $pro_expires) : null,
            'trial_ai_count' => $trial_ai_count,   // AI 试用剩余次数
            'device_count'    => $device_count,        // 该账号已登录过的设备数
            'device_limit'    => DEVICE_LIMIT,         // 允许的最大设备数
            'device_suspicious' => $device_suspicious, // 是否已被标记可疑（转卖/共享）
        ],
    ],
], JSON_UNESCAPED_UNICODE);
