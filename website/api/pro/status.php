<?php

// ============================================================

// B5b: 查询完整版状态

// GET /api/pro/status.php

// 查 user_pro_subscriptions 表（不查 ll_useregs 的 pro 字段）

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



if (!defined('JWT_SECRET')) { http_response_code(500); echo json_encode(['code'=>-1,'message'=>'Server config error: JWT_SECRET']); exit; }

$JWT_SECRET = JWT_SECRET;



$user = require_login($JWT_SECRET);

$uid  = (int)$user['uid'];



$db = get_db_connection();



// 查用户基本信息（ll_useregs 实际列名）

$stmt = $db->prepare('SELECT id, ll_name FROM ll_useregs WHERE id = :uid LIMIT 1');

$stmt->execute([':uid' => $uid]);

$row = $stmt->fetch(PDO::FETCH_ASSOC);



if (!$row) {

    http_response_code(404);

    echo json_encode(['code' => -1, 'message' => '用户不存在']);

    exit;

}



// 查完整版订阅状态（新表 user_pro_subscriptions）

// 注意：expires_at 是 BIGINT Unix 时间戳

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

    $pro_activated   = 1;

    $pro_expires     = (int)$sub['expires_at'];

    $remaining_days  = max(0, (int)(($pro_expires - $now) / 86400));

    $remaining_text  = $remaining_days . ' 天';

    $level           = 'pro';

    $plan            = $sub['plan'];

} else {

    $pro_activated   = 0;

    $pro_expires     = 0;

    $remaining_days  = 0;

    $remaining_text  = '未开通';

    $level           = 'free';

    $plan            = null;

}



// 查余额（如果网站有 user_balance 表则查，没有返回 0）

$balance = 0;

try {

    $stmt = $db->prepare('SELECT balance FROM user_balance WHERE user_id = :uid LIMIT 1');

    $stmt->execute([':uid' => $uid]);

    $bal = $stmt->fetch(PDO::FETCH_ASSOC);

    if ($bal) {

        $balance = (float)$bal['balance'];

    }

} catch (Exception $e) {

    // user_balance 表可能不存在，忽略

}



echo json_encode([

    'code' => 0,

    'message' => 'ok',

    'data' => [

        'uid'            => (int)$row['id'],

        'username'       => $row['ll_name'],

        'level'          => $level,

        'plan'           => $plan,

        'pro_activated'  => $pro_activated,

        'pro_expires'    => $pro_expires,

        'pro_expires_at' => $pro_expires > 0 ? date('Y-m-d H:i:s', $pro_expires) : null,

        'remaining_days' => $remaining_days,

        'remaining_text' => $remaining_text,

        'balance'        => $balance,

        'server_time'    => $now,

    ],

], JSON_UNESCAPED_UNICODE);

