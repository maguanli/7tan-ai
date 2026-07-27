<?php
// ============================================================
// B5a: 购买专业版 API（余额扣款 → 即时激活）
// POST /api/pro/purchase.php
// 扣余额 → INSERT user_pro_subscriptions（不改 ll_useregs）
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

$JWT_SECRET = defined('JWT_SECRET') ? JWT_SECRET : 'change-me-to-a-random-64-char-string';

// ============================================================
// 验证登录
// ============================================================
$user = require_login($JWT_SECRET);
$uid  = (int)$user['uid'];

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
$input  = json_decode(file_get_contents('php://input'), true);
$plan   = $input['plan'] ?? '';
$months = (int)($input['months'] ?? 0);

// 如果传了 plan，用 plan 查价格；否则用 months 反查
if (!empty($plan) && isset($PLANS[$plan])) {
    $plan_info = $PLANS[$plan];
    $amount    = $plan_info['price'];
    $months    = $plan_info['months'];
} elseif ($months > 0) {
    // 按 months 匹配套餐
    $found = false;
    foreach ($PLANS as $key => $info) {
        if ($info['months'] === $months) {
            $plan      = $key;
            $plan_info = $info;
            $amount    = $info['price'];
            $found     = true;
            break;
        }
    }
    if (!$found) {
        http_response_code(400);
        echo json_encode(['code' => -1, 'message' => '无效的购买月数']);
        exit;
    }
} else {
    http_response_code(400);
    echo json_encode(['code' => -1, 'message' => '请指定套餐 plan 或购买月数 months']);
    exit;
}

// ============================================================
// 查询余额
// ============================================================
$db  = get_db_connection();
$stmt = $db->prepare('SELECT balance FROM user_balance WHERE user_id = :uid LIMIT 1');
$stmt->execute([':uid' => $uid]);
$balance = (float)($stmt->fetchColumn() ?: 0);

if ($balance < $amount) {
    http_response_code(402);
    echo json_encode([
        'code'    => -1,
        'message' => '余额不足，需要 ' . $amount . ' 元，当前余额 ' . $balance . ' 元',
        'data'    => [
            'required' => $amount,
            'balance'  => $balance,
            'shortage' => round($amount - $balance, 2),
        ],
    ]);
    exit;
}

// ============================================================
// 计算到期时间
// ============================================================
$now = time();

// 如果当前有未过期的专业版，在现有到期时间基础上叠加
$stmt = $db->prepare(
    'SELECT expires_at FROM user_pro_subscriptions
     WHERE user_id = :uid AND status = 1 AND expires_at > :now
     ORDER BY expires_at DESC
     LIMIT 1'
);
$stmt->execute([':uid' => $uid, ':now' => $now]);
$existing = $stmt->fetch(PDO::FETCH_ASSOC);

if ($existing) {
    $base_time = (int)$existing['expires_at'];
} else {
    $base_time = $now;
}
$new_expires = strtotime("+{$months} months", $base_time);

// ============================================================
// 生成流水号
// ============================================================
$trade_no = 'PRO' . date('YmdHis') . rand(1000, 9999) . $uid;

// ============================================================
// 事务: 扣余额 + 写入订阅记录
// ============================================================
$db->beginTransaction();

try {
    // 1. 扣余额
    $stmt = $db->prepare(
        'UPDATE user_balance SET balance = balance - :amount WHERE user_id = :uid'
    );
    $stmt->execute([':amount' => $amount, ':uid' => $uid]);

    // 2. 写入订阅记录（expires_at/activated_at/created_at 都是 BIGINT Unix 时间戳）
    $stmt = $db->prepare(
        'INSERT INTO user_pro_subscriptions (user_id, plan, months, amount, status, activated_at, expires_at, created_at)
         VALUES (:uid, :plan, :months, :amount, 1, :now, :expires_at, :now)'
    );
    $stmt->execute([
        ':uid'        => $uid,
        ':plan'       => $plan,
        ':months'     => $months,
        ':amount'     => $amount,
        ':now'        => $now,
        ':expires_at' => $new_expires,
    ]);

    $db->commit();
} catch (Exception $e) {
    $db->rollBack();
    http_response_code(500);
    echo json_encode(['code' => -1, 'message' => '购买失败: ' . $e->getMessage()]);
    exit;
}

// ============================================================
// 查询最新余额
// ============================================================
$stmt = $db->prepare('SELECT balance FROM user_balance WHERE user_id = :uid LIMIT 1');
$stmt->execute([':uid' => $uid]);
$new_balance = round((float)$stmt->fetchColumn(), 2);

// ============================================================
// 返回
// ============================================================
echo json_encode([
    'code'    => 0,
    'message' => '购买成功！专业版已激活',
    'data'    => [
        'plan'           => $plan_info['name'],
        'months'         => $months,
        'amount'         => $amount,
        'balance_after'  => $new_balance,
        'pro_activated'  => 1,
        'pro_expires'    => $new_expires,
        'pro_expires_at' => date('Y-m-d H:i:s', $new_expires),
        'trade_no'       => $trade_no,
    ],
], JSON_UNESCAPED_UNICODE);
