<?php

// ============================================================

// B3: 验证 Token + 返回会员状态

// GET /api/auth/verify.php

// Token 优先级：Authorization header > Cookie > GET > POST

// 回退：PHP Session 自动探测 > 数据库 session 表 > 401

// ============================================================



header('Content-Type: application/json; charset=utf-8');

header('Access-Control-Allow-Origin: https://www.7tan.com');

header('Access-Control-Allow-Credentials: true');

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

// 提取 Token（5 种来源）

// ============================================================

$token = '';



// ① Authorization header

$auth_header = $_SERVER['HTTP_AUTHORIZATION'] ?? $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ?? '';

if (!empty($auth_header) && preg_match('/Bearer\s+(.+)/i', $auth_header, $m)) {

    $token = $m[1];

}



// ② Cookie auth_token

if (empty($token) && !empty($_COOKIE['auth_token'])) {

    $token = $_COOKIE['auth_token'];

}



// ③ GET 参数

if (empty($token) && !empty($_GET['token'])) {

    $token = $_GET['token'];

}



// ④ POST JSON body

if (empty($token)) {

    $raw_body = file_get_contents('php://input');

    if (!empty($raw_body)) {

        $body = json_decode($raw_body, true);

        if (!empty($body['token'])) {

            $token = $body['token'];

        }

    }

}



// ⑤ POST 表单

if (empty($token) && !empty($_POST['token'])) {

    $token = $_POST['token'];

}



// ============================================================

// 快速 Token 验证（不连数据库，仅验 JWT 签名）

// ============================================================

if (!empty($token)) {

    try {

        $payload = jwt_decode_auto_skip_expiry($token, $JWT_SECRET);

    } catch (JWTException $e) {

        // Token 无效，清空，走 BBS 回退

        $token = '';

    }

}



// ============================================================

// ⑥ BBS 登录回退 - 自动探测

// ============================================================

$session_user = null;



if (empty($token)) {

    // ---- 6a. PHP Session 自动探测 ----

    if (session_status() === PHP_SESSION_NONE) {

        @session_start();

    }



    $sess_uid = 0;



    if (!empty($_SESSION)) {

        // 尝试常见键名

        foreach (['user_id', 'uid', 'userid', 'member_id', 'mid', 'id'] as $key) {

            if (!empty($_SESSION[$key]) && is_numeric($_SESSION[$key]) && (int)$_SESSION[$key] > 0) {

                $sess_uid = (int)$_SESSION[$key];

                break;

            }

        }



        // 尝试嵌套数组 $_SESSION['user']['id'] 等

        if ($sess_uid === 0) {

            foreach ($_SESSION as $v) {

                if (!is_array($v)) continue;

                foreach (['id', 'uid', 'user_id', 'userid'] as $subkey) {

                    if (!empty($v[$subkey]) && is_numeric($v[$subkey]) && (int)$v[$subkey] > 0) {

                        $sess_uid = (int)$v[$subkey];

                        break 2;

                    }

                }

            }

        }



        // 最后手段：遍历所有值，找 1-999999 的整数，数据库验证

        if ($sess_uid === 0) {

            foreach ($_SESSION as $v) {

                if (is_numeric($v) && (int)$v > 0 && (int)$v < 1000000) {

                    try {

                        $db_check = get_db_connection();

                        $chk = $db_check->prepare('SELECT COUNT(*) FROM ll_useregs WHERE id = :uid');

                        $chk->execute([':uid' => (int)$v]);

                        if ((int)$chk->fetchColumn() > 0) {

                            $sess_uid = (int)$v;

                            break;

                        }

                    } catch (\Exception $e) {}

                }

            }

        }

    }



    // ---- 6b. PHPSESSID → 数据库 session 表回退 ----

    if ($sess_uid === 0 && !empty($_COOKIE['PHPSESSID'])) {

        $sess_id = $_COOKIE['PHPSESSID'];

        try {

            $db_sess = get_db_connection();

            $tables = $db_sess->query("SHOW TABLES LIKE 'sessions'")->fetchAll(PDO::FETCH_COLUMN);

            if (!empty($tables)) {

                $stmt = $db_sess->prepare("SELECT data FROM sessions WHERE id = :id LIMIT 1");

                $stmt->execute([':id' => $sess_id]);

                $row = $stmt->fetch(PDO::FETCH_ASSOC);

                if ($row && !empty($row['data'])) {

                    $data = $row['data'];

                    if (preg_match('/user_id\|i:(\d+)/', $data, $m)) $sess_uid = (int)$m[1];

                    elseif (preg_match('/uid\|i:(\d+)/', $data, $m)) $sess_uid = (int)$m[1];

                    elseif (preg_match('/userid\|i:(\d+)/', $data, $m)) $sess_uid = (int)$m[1];

                }

            }

        } catch (\Exception $e) {}

    }



    // ---- 6c. 用探测到的 uid 查用户 ----

    if ($sess_uid > 0) {

        $db = get_db_connection();

        $stmt = $db->prepare('SELECT id, ll_name FROM ll_useregs WHERE id = :uid LIMIT 1');

        $stmt->execute([':uid' => $sess_uid]);

        $session_user = $stmt->fetch(PDO::FETCH_ASSOC);



        if ($session_user) {

            $issued_at = time();

            $expires_at = $issued_at + 86400 * 30;

            $payload = [

                'uid'      => (int)$session_user['id'],

                'username' => $session_user['ll_name'],

                'iat'      => $issued_at,

                'exp'      => $expires_at,

            ];

            $token = jwt_encode($payload, $JWT_SECRET);



            setcookie('auth_token', $token, [

                'expires'  => $expires_at,

                'path'     => '/',

                'domain'   => '',

                'secure'   => true,

                'httponly' => false,

                'samesite' => 'Lax',

            ]);

        }

    }

}



// ============================================================

// Debug 模式：输出探测过程（访问 ?debug=1）

// ============================================================

if (!empty($_GET['debug'])) {

    http_response_code(200);

    echo json_encode([

        'code'  => 0,

        'debug' => [

            'session_status'     => session_status(),

            'session_keys'       => !empty($_SESSION) ? array_keys($_SESSION) : [],

            'session_sample'     => !empty($_SESSION) ? array_map(function ($v) {

                if (is_array($v)) return '(array[' . count($v) . '] keys:' . implode(',', array_keys($v)) . ')';

                if (is_string($v)) return substr($v, 0, 100);

                return $v;

            }, $_SESSION) : '(empty)',

            'detected_uid'       => $sess_uid ?? 0,

            'phpsessid'          => $_COOKIE['PHPSESSID'] ?? 'none',

            'all_cookie_keys'    => array_keys($_COOKIE),

            'session_user_found' => $session_user ? true : false,

            'token_generated'    => !empty($token),

        ],

    ], JSON_UNESCAPED_UNICODE);

    exit;

}



// ============================================================

// 如果仍然没有 token 且没有 BBS 用户 → 401

// ============================================================

if (empty($token) && !$session_user) {

    http_response_code(401);

    echo json_encode(['code' => -1, 'message' => '请先登录', 'data' => ['level' => 'free']]);

    exit;

}



// ============================================================

// JWT 解码获取 uid

// ============================================================

if (!empty($token)) {

    try {

        $payload = jwt_decode_auto_skip_expiry($token, $JWT_SECRET);

    } catch (JWTException $e) {

        http_response_code(401);

        echo json_encode([

            'code'    => -1,

            'message' => 'Token 无效: ' . $e->getMessage(),

            'data'    => ['level' => 'free'],

        ]);

        exit;

    }

    $uid = (int)($payload['uid'] ?? 0);

} else {

    $uid = (int)$session_user['id'];

}



// ============================================================

// 查用户基本信息

// ============================================================

$db = $db ?? get_db_connection();



$stmt = $db->prepare('SELECT id, ll_name FROM ll_useregs WHERE id = :uid LIMIT 1');

$stmt->execute([':uid' => $uid]);

$user = $stmt->fetch(PDO::FETCH_ASSOC);



if (!$user) {

    http_response_code(401);

    echo json_encode([

        'code'    => -1,

        'message' => '用户不存在',

        'data'    => ['level' => 'free'],

    ]);

    exit;

}



// ============================================================

// 查完整版状态

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

// 返回

// ============================================================

echo json_encode([

    'code'    => 0,

    'message' => 'ok',

    'data'    => [

        'uid'            => (int)$user['id'],

        'username'       => $user['ll_name'],

        'level'          => $is_pro ? 'pro' : 'free',

        'pro_activated'  => $pro_activated,

        'pro_expires'    => $pro_expires,

        'pro_expires_at' => $pro_expires > 0 ? date('Y-m-d H:i:s', $pro_expires) : null,

        'server_time'    => $now,

        'token'          => $token,

    ],

], JSON_UNESCAPED_UNICODE);

