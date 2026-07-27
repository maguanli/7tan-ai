<?php
// ============================================================
// B4: Refresh Token
// GET /api/auth/refresh.php
// Re-issues JWT with latest pro_expires after renewal
// ============================================================

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

require_once __DIR__ . '/../../config/database.php';
require_once __DIR__ . '/../../lib/jwt_helper.php';

$JWT_SECRET = defined('JWT_SECRET') ? JWT_SECRET : 'change-me-to-a-random-64-char-string';

// ============================================================
// Extract Token (4 sources)
// ============================================================
$token = '';

// 1. Authorization header (including Apache REDIRECT_ variant)
$auth_header = $_SERVER['HTTP_AUTHORIZATION'] ?? $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ?? '';
if (!empty($auth_header) && preg_match('/Bearer\s+(.+)/i', $auth_header, $m)) {
    $token = $m[1];
}

// 2. GET param
if (empty($token) && !empty($_GET['token'])) {
    $token = $_GET['token'];
}

// 3. POST JSON body
if (empty($token)) {
    $raw_body = file_get_contents('php://input');
    if (!empty($raw_body)) {
        $body = json_decode($raw_body, true);
        if (!empty($body['token'])) {
            $token = $body['token'];
        }
    }
}

// 4. POST form
if (empty($token) && !empty($_POST['token'])) {
    $token = $_POST['token'];
}

if (empty($token)) {
    http_response_code(401);
    echo json_encode(['code' => -1, 'message' => 'Missing Token']);
    exit;
}

// ============================================================
// Decode old Token (skip expiry check)
// ============================================================
try {
    $payload = jwt_decode_auto_skip_expiry($token, $JWT_SECRET);
} catch (JWTException $e) {
    http_response_code(401);
    echo json_encode(['code' => -1, 'message' => 'Token invalid: ' . $e->getMessage()], JSON_UNESCAPED_UNICODE);
    exit;
} catch (\Throwable $e) {
    http_response_code(401);
    echo json_encode(['code' => -1, 'message' => 'Token parse error: ' . $e->getMessage()], JSON_UNESCAPED_UNICODE);
    exit;
}

$uid = (int)($payload['uid'] ?? 0);
$db = get_db_connection();

// ============================================================
// Query user info (ll_useregs)
// ============================================================
$stmt = $db->prepare('SELECT id, ll_name, ll_pwd, ll_date, email FROM ll_useregs WHERE id = :uid LIMIT 1');
$stmt->execute([':uid' => $uid]);
$user = $stmt->fetch(PDO::FETCH_ASSOC);

if (!$user) {
    http_response_code(401);
    echo json_encode(['code' => -1, 'message' => 'User not found']);
    exit;
}

// ============================================================
// Query latest pro subscription status
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
// Issue new JWT
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
// Response
// ============================================================
echo json_encode([
    'code'    => 0,
    'message' => 'Token refreshed',
    'data'    => [
        'token'         => $new_token,
        'level'         => $is_pro ? 'pro' : 'free',
        'pro_activated' => $pro_activated,
        'pro_expires'   => $pro_expires,
        'pro_expires_at'=> $pro_expires > 0 ? date('Y-m-d H:i:s', $pro_expires) : null,
    ],
], JSON_UNESCAPED_UNICODE);
