<?php
// ============================================================
// B5a: 购买专业版 API（余额扣款 → 即时激活）
// POST /api/pro/purchase.php
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
require_once __DIR__ . '/../../lib/auth_middleware.php';  // 登录验证中间件

$JWT_SECRET = defined('JWT_SECRET') ? JWT_SECRET : 'change-me-to-a-random-64-char-string';

// ============================================================
// 验证登录
// ============================================================
$user = require_login($JWT_SECRET);  // 返回 ['uid'=>..., 'username'=>...]
$uid  = (int)$user['uid'];

// ============================================================
// 定价配置
// ============================================================
$PLANS = [
    'monthly'      => ['name' => '月付',  'months' => 1,  'price' => 50,  'label' => ''],
    'quarterly'    => ['name' => '季付',  'months' => 3,  'price' => 120, 'label' => '⭐ 推荐'],
    'semi_annual'  => ['name' => '半年付', 'months' => 6,  'price' => 200, 'label' => '🔥 最火'],
    'annual'       => ['name' => '年付',  'months' => 12, 'price' => 350, 'label' => '👑 最省'],
];

// ============================================================
// 获取输入
// ============================================================
$input = json_decode(file_get_contents('php://input'), true);
$plan  = trim($input['plan'] ?? 'semi_annual');

if (!isset($PLANS[$plan])) {
    http_response_code(400);
    echo json_encode(['code' => -1, 'message' => '无效的套餐类型']);
    exit;
}

$plan_info = $PLANS[$plan];
$months    = $plan_info['months'];
$amount    = $plan_info['price'];

// ============================================================
// 查询用户余额和当前专业版状态
// ============================================================
$db = get_db_connection();

$stmt = $db->prepare(
    'SELECT u.id, u.pro_activated, u.pro_expires, COALESCE(b.balance, 0) AS balance
     FROM ll_useregs u
     LEFT JOIN user_balance b ON u.id = b.user_id
     WHERE u.id = :uid
     LIMIT 1'
);
$stmt->execute([':uid' => $uid]);
$row = $stmt->fetch(PDO::FETCH_ASSOC);

if (!$row) {
    http_response_code(404);
    echo json_encode(['code' => -1, 'message' => '用户不存在']);
    exit;
}

$balance       = (float)$row['balance'];
$pro_activated = (int)($row['pro_activated'] ?? 0);
$pro_expires   = (int)($row['pro_expires']   ?? 0);
$now           = time();

// ============================================================
// 检查余额
// ============================================================
if ($balance < $amount) {
    http_response_code(402);
    echo json_encode([
        'code'    => -1,
        'message' => '余额不足',
        'data'    => [
            'balance'     => $balance,
            'need'        => $amount,
            'shortage'    => round($amount - $balance, 2),
            'recharge_url'=> '/user/recharge',
        ],
    ]);
    exit;
}

// ============================================================
// 计算新的到期时间
// ============================================================
// 如果当前是专业版且未过期 → 在现有到期时间上叠加
// 否则 → 从现在开始算
if ($pro_activated === 1 && $pro_expires > $now) {
    $new_expires = strtotime("+{$months} months", $pro_expires);
} else {
    $new_expires = strtotime("+{$months} months", $now);
}

// ============================================================
// 事务：扣余额 + 更新会员 + 记录流水
// ============================================================
try {
    $db->beginTransaction();

    // 1. 扣余额
    $stmt = $db->prepare(
        'UPDATE user_balance SET balance = balance - :amount, updated_at = NOW()
         WHERE user_id = :uid AND balance >= :amount2'
    );
    $stmt->execute([':uid' => $uid, ':amount' => $amount, ':amount2' => $amount]);
    if ($stmt->rowCount() === 0) {
        throw new Exception('扣款失败，余额不足或账户异常');
    }

    // 2. 更新会员状态
    $stmt = $db->prepare(
        'UPDATE ll_useregs
         SET pro_activated = 1, pro_expires = :new_expires
         WHERE id = :uid'
    );
    $stmt->execute([':uid' => $uid, ':new_expires' => $new_expires]);

    // 3. 记录流水（如果网站有 pro_purchases 表）
    $trade_no = 'PRO' . date('YmdHis') . strtoupper(substr(bin2hex(random_bytes(3)), 0, 6));
    $stmt = $db->prepare(
        'INSERT INTO pro_purchases (user_id, plan, months, amount, pay_type, trade_no, status, activated_at, expires_at, created_at)
         VALUES (:uid, :plan, :months, :amount, :pay_type, :trade_no, 1, NOW(), :expires_at, NOW())'
    );
    $stmt->execute([
        ':uid'        => $uid,
        ':plan'       => $plan,
        ':months'     => $months,
        ':amount'     => $amount,
        ':pay_type'  => 'balance',
        ':trade_no'  => $trade_no,
        ':expires_at'=> date('Y-m-d H:i:s', $new_expires),
    ]);

    $db->commit();
} catch (Exception $e) {
    $db->rollBack();
    http_response_code(500);
    echo json_encode(['code' => -1, 'message' => '购买失败: ' . $e->getMessage()]);
    exit;
}

// ============================================================
// 成功响应
// ============================================================
$new_balance = round($balance - $amount, 2);

echo json_encode([
    'code'    => 0,
    'message' => '购买成功！专业版已激活',
    'data'    => [
        'plan'          => $plan_info['name'],
        'months'        => $months,
        'amount'        => $amount,
        'balance_after' => $new_balance,
        'pro_activated' => 1,
        'pro_expires'   => $new_expires,
        'pro_expires_at'=> date('Y-m-d H:i:s', $new_expires),
        'trade_no'      => $trade_no,
    ],
], JSON_UNESCAPED_UNICODE);
