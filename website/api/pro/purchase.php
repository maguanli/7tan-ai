<?php

// ============================================================

// B5a: 购买完整版 API（直接激活，支付由网站现有系统处理）

// POST /api/pro/purchase.php

// INSERT user_pro_subscriptions（不改 ll_useregs）

// ============================================================



header('Content-Type: application/json; charset=utf-8');

header('Access-Control-Allow-Origin: *');

header('Access-Control-Allow-Methods: POST, OPTIONS');

header('Access-Control-Allow-Headers: Content-Type, Authorization');



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

require_once __DIR__ . '/../../lib/auth_middleware.php';



if (!defined('JWT_SECRET')) { http_response_code(500); echo json_encode(['code'=>-1,'message'=>'Server config error: JWT_SECRET']); exit; }

$JWT_SECRET = JWT_SECRET;



// ============================================================

// 验证登录

// ============================================================

$user = require_login($JWT_SECRET);

$uid  = (int)$user['uid'];



// ============================================================

// 管理员验证 — 仅允许管理员直接激活，普通用户需走支付流程

// ============================================================

$ADMIN_UIDS = defined('ADMIN_UIDS') ? explode(',', ADMIN_UIDS) : [1];

if (!in_array($uid, $ADMIN_UIDS)) {

    // 非管理员必须提供支付凭证

    $payment_ref = $input['payment_ref'] ?? '';

    if (empty($payment_ref)) {

        http_response_code(403);

        echo json_encode([

            'code' => -1,

            'message' => '请先完成支付，提供 payment_ref 参数。管理员可直接激活。'

        ], JSON_UNESCAPED_UNICODE);

        exit;

    }

    // TODO: 验证 payment_ref 与支付平台回调

}



// ============================================================

// 定价配置

// ============================================================

$PLANS = [

    'monthly'     => ['name' => '月付',  'months' => 1,  'price' => 50,  'label' => ''],

    'quarterly'   => ['name' => '季付',  'months' => 3,  'price' => 120, 'label' => '⭐ 推荐'],

    'semi_annual' => ['name' => '半年付', 'months' => 6,  'price' => 200, 'label' => '🔥 最火'],

    'annual'      => ['name' => '年付',  'months' => 12, 'price' => 350, 'label' => '👑 最省'],

];



// ============================================================

// 获取输入

// ============================================================

$input = json_decode(file_get_contents('php://input'), true);

$plan  = $input['plan'] ?? '';



if (!isset($PLANS[$plan])) {

    http_response_code(400);

    echo json_encode(['code' => -1, 'message' => '无效的套餐，可选：monthly/quarterly/semi_annual/annual']);

    exit;

}



$plan_info = $PLANS[$plan];

$months    = $plan_info['months'];

$amount    = $plan_info['price'];



// ============================================================

// 计算到期时间（如果在已有有效期内续费，叠加）

// ============================================================

$db   = get_db_connection();

$now  = time();



$stmt = $db->prepare(

    'SELECT expires_at FROM user_pro_subscriptions

     WHERE user_id = :uid AND status = 1 AND expires_at > :now

     ORDER BY expires_at DESC LIMIT 1'

);

$stmt->execute([':uid' => $uid, ':now' => $now]);

$existing = $stmt->fetch(PDO::FETCH_ASSOC);



$start_from = ($existing && $existing['expires_at'] > $now)

    ? (int)$existing['expires_at']

    : $now;



$new_expires = strtotime("+{$months} months", $start_from);



// ============================================================

// 记录购买（支付由网站现有系统处理，这里直接激活）

// ============================================================

$trade_no = 'PRO_' . date('YmdHis') . '_' . $uid . '_' . bin2hex(random_bytes(4));

$stmt = $db->prepare(

    'INSERT INTO user_pro_subscriptions (user_id, plan, months, amount, status, activated_at, expires_at, created_at)

     VALUES (:uid, :plan, :months, :amount, 1, :activated_at, :expires_at, :created_at)'

);

$stmt->execute([

    ':uid'          => $uid,

    ':plan'         => $plan,

    ':months'       => $months,

    ':amount'       => $amount,

    ':activated_at' => $now,

    ':expires_at'   => $new_expires,

    ':created_at'   => $now,

]);



// ============================================================

// 返回结果

// ============================================================

echo json_encode([

    'code'    => 0,

    'message' => '购买成功！完整版已激活',

    'data'    => [

        'plan'           => $plan_info['name'],

        'months'         => $months,

        'amount'         => $amount,

        'pro_activated'  => 1,

        'pro_expires'    => $new_expires,

        'pro_expires_at' => date('Y-m-d H:i:s', $new_expires),

        'trade_no'       => $trade_no,

    ],

], JSON_UNESCAPED_UNICODE);

