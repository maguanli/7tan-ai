<?php

// ============================================================
// 插件中心 - 购买 API
// POST /api/plugin/purchase.php
// 入参: { plugin_id, fingerprint }
// 流程: 登录校验 → 插件/指纹校验 → 防重复 → 余额扣款(事务)
//       → RSA 签名生成授权码 → 订单留痕 → 返回授权码
// 授权码格式: 指纹.签名(RSA-2048 PKCS1v15 SHA256, base64url)
// ============================================================

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { http_response_code(200); exit; }
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['code' => -1, 'message' => '仅支持 POST']);
    exit;
}

require_once __DIR__ . '/../../bbs/config.php';

if (!isLoggedIn()) {
    echo json_encode(['code' => -1, 'message' => '请先登录', 'need_login' => true], JSON_UNESCAPED_UNICODE);
    exit;
}

$pdo = getDB();
$userId = (int)getCurrentUserId();

// ========== 插件目录（与 list.php 保持一致） ==========
$PLUGINS = [
    'viral_writer' => [
        'id'          => 'viral_writer',
        'name'        => '爆款写作',
        'price'       => 5000,
        'price_yuan'  => 50,
        'desc'        => '公众号爆款文章一站式生成',
        'license_file'=> __DIR__ . '/../../config/viral_private_key.pem', // 私钥（服务器）
    ],
];

// ========== 入参校验 ==========
$input = json_decode(file_get_contents('php://input'), true);
$pluginId = trim($input['plugin_id'] ?? '');
$fp       = strtolower(trim($input['fingerprint'] ?? ''));

if (!isset($PLUGINS[$pluginId])) {
    http_response_code(400);
    echo json_encode(['code' => -1, 'message' => '插件不存在'], JSON_UNESCAPED_UNICODE);
    exit;
}
if (!preg_match('/^[0-9a-f]{32}$/', $fp)) {
    http_response_code(400);
    echo json_encode(['code' => -1, 'message' => '机器指纹格式不正确（应为 32 位十六进制，可在软件“爆款写作”状态页复制）'], JSON_UNESCAPED_UNICODE);
    exit;
}

$plugin = $PLUGINS[$pluginId];
$price  = (int)$plugin['price'];

// ========== 防重复：同用户+同插件+同指纹已购 → 直接返回原授权码（不重复扣费） ==========
$stmt = $pdo->prepare(
    'SELECT order_no, license_key FROM ll_plugin_orders
     WHERE user_id = ? AND plugin_id = ? AND fingerprint = ? AND status = 1
     ORDER BY id DESC LIMIT 1'
);
$stmt->execute([$userId, $pluginId, $fp]);
$exist = $stmt->fetch(PDO::FETCH_ASSOC);
if ($exist) {
    echo json_encode([
        'code'    => 0,
        'message' => '您已购买过该插件（同机器），无需重复扣费',
        'data'    => [
            'order_no'    => $exist['order_no'],
            'plugin_id'   => $pluginId,
            'license_key' => $exist['license_key'],
            'reuse'       => true,
        ],
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

// ========== 余额检查（分） ==========
$stmt = $pdo->prepare('SELECT balance, frozen FROM ll_cash_wallet WHERE user_id = ?');
$stmt->execute([$userId]);
$w = $stmt->fetch(PDO::FETCH_ASSOC);
$balanceCents   = $w ? (int)$w['balance'] : 0;
$frozenCents    = $w ? (int)$w['frozen'] : 0;
$availableCents = $balanceCents - $frozenCents;

if ($availableCents < $price) {
    http_response_code(402);
    echo json_encode([
        'code' => -1,
        'message' => '余额不足，购买「' . $plugin['name'] . '」需 ¥' . number_format($price / 100, 2) . '，当前可用 ¥' . number_format($availableCents / 100, 2),
        'recharge_url' => 'https://www.7tan.com/task/wallet.php',
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

// ========== 生成授权码（RSA-2048 / PKCS1v15 / SHA-256 / base64url） ==========
$privPem = @file_get_contents($plugin['license_file']);
if ($privPem === false || empty($privPem)) {
    http_response_code(500);
    echo json_encode(['code' => -1, 'message' => '服务端授权密钥缺失，请联系管理员'], JSON_UNESCAPED_UNICODE);
    exit;
}
$priv = openssl_pkey_get_private($privPem);
if (!$priv) {
    http_response_code(500);
    echo json_encode(['code' => -1, 'message' => '授权密钥解析失败，请联系管理员'], JSON_UNESCAPED_UNICODE);
    exit;
}
$sig = '';
if (!openssl_sign($fp, $sig, $priv, OPENSSL_ALGO_SHA256)) {
    http_response_code(500);
    echo json_encode(['code' => -1, 'message' => '授权码生成失败，请联系管理员'], JSON_UNESCAPED_UNICODE);
    exit;
}
$licenseKey = $fp . '.' . rtrim(strtr(base64_encode($sig), '+/', '-_'), '=');

// ========== 事务：扣款 + 流水 + 订单 ==========
$orderNo = 'PLG' . date('YmdHis') . str_pad((string)random_int(0, 99999999), 8, '0', STR_PAD_LEFT);

$pdo->beginTransaction();
try {
    // 1) 扣余额（条件更新防并发超扣）
    $stmt = $pdo->prepare(
        'UPDATE ll_cash_wallet SET balance = balance - ? WHERE user_id = ? AND balance >= ?'
    );
    $stmt->execute([$price, $userId, $price]);
    if ($stmt->rowCount() !== 1) {
        throw new Exception('扣款失败（余额不足或账户异常）');
    }
    // 2) 流水
    $stmt = $pdo->prepare('SELECT balance, frozen FROM ll_cash_wallet WHERE user_id = ?');
    $stmt->execute([$userId]);
    $afterW = $stmt->fetch(PDO::FETCH_ASSOC);
    $afterBalance = (int)$afterW['balance'];

    $stmt = $pdo->prepare(
        'INSERT INTO ll_cash_wallet_log (user_id, type, amount, balance_before, balance_after, ref_id, remark, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, NOW())'
    );
    $stmt->execute([
        $userId, 'plugin_buy', -$price, $balanceCents, $afterBalance,
        $orderNo, '购买插件：' . $plugin['name'] . '（' . substr($fp, 0, 8) . '…）'
    ]);

    // 3) 订单留痕
    $stmt = $pdo->prepare(
        'INSERT INTO ll_plugin_orders (order_no, user_id, plugin_id, plugin_name, price, fingerprint, license_key, status, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, 1, NOW())'
    );
    $stmt->execute([$orderNo, $userId, $pluginId, $plugin['name'], $price, $fp, $licenseKey]);

    $pdo->commit();
} catch (Exception $e) {
    $pdo->rollBack();
    http_response_code(500);
    echo json_encode(['code' => -1, 'message' => '购买失败：' . $e->getMessage()], JSON_UNESCAPED_UNICODE);
    exit;
}

// ========== 返回 ==========
echo json_encode([
    'code'    => 0,
    'message' => '购买成功！授权码已生成，请在软件中输入激活',
    'data'    => [
        'order_no'    => $orderNo,
        'plugin_id'   => $pluginId,
        'plugin_name' => $plugin['name'],
        'fingerprint' => $fp,
        'license_key' => $licenseKey,
        'reuse'       => false,
    ],
], JSON_UNESCAPED_UNICODE);
