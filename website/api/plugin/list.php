<?php

// ============================================================
// 插件中心 - 插件列表 & 用户状态 API
// GET /api/plugin/list.php
// 返回: 插件目录 + 当前用户余额(元) + 已购授权列表
// 认证: BBS 登录会话（与 wallet.php 同源）
// ============================================================

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { http_response_code(200); exit; }

require_once __DIR__ . '/../../bbs/config.php';

if (!isLoggedIn()) {
    echo json_encode(['code' => -1, 'message' => '请先登录', 'need_login' => true], JSON_UNESCAPED_UNICODE);
    exit;
}

$pdo = getDB();
$userId = (int)getCurrentUserId();

// ========== 插件目录（内置配置，可扩展） ==========
$PLUGINS = [
    'viral_writer' => [
        'id'          => 'viral_writer',
        'name'        => '爆款写作',
        'icon'        => '✍️',
        'price'       => 5000,          // 分（50 元）
        'price_yuan'  => 50,
        'type'        => 'per_device',  // 按台授权
        'trial'       => 5,             // 免费试用次数
        'desc'        => '公众号爆款文章一站式生成：10个爆款选题、10个爆款标题、五段式大纲、正文撰写、金句卡片、发布前质量检查。',
        'features'    => [
            '爆款选题：10个选题带情绪价值/人群/潜力分',
            '爆款标题：10个标题带类型标签与打开率预测',
            '五段式大纲：钩子→故事→金句→升华→互动',
            '正文撰写：口语化有画面感，可直接粘贴发布',
            '金句卡片：6条金句+1080x608排版建议',
            '发布前检查：标题长度/结构/敏感词风险'
        ],
        'purchase_note' => '50元/台（永久授权，绑定当前电脑）',
    ],
];

// ========== 查询余额 ==========
$balanceCents = 0;
$frozenCents  = 0;
$stmt = $pdo->prepare('SELECT balance, frozen FROM ll_cash_wallet WHERE user_id = ?');
$stmt->execute([$userId]);
$w = $stmt->fetch(PDO::FETCH_ASSOC);
if ($w) {
    $balanceCents = (int)$w['balance'];
    $frozenCents  = (int)$w['frozen'];
}
$availableCents = $balanceCents - $frozenCents;

// ========== 查询已购授权 ==========
$orders = [];
$stmt = $pdo->prepare(
    'SELECT order_no, plugin_id, plugin_name, price, fingerprint, license_key, created_at
     FROM ll_plugin_orders WHERE user_id = ? ORDER BY id DESC LIMIT 50'
);
$stmt->execute([$userId]);
foreach ($stmt->fetchAll(PDO::FETCH_ASSOC) as $row) {
    $orders[] = [
        'order_no'    => $row['order_no'],
        'plugin_id'   => $row['plugin_id'],
        'plugin_name' => $row['plugin_name'],
        'price_yuan'  => round((int)$row['price'] / 100, 2),
        'fingerprint' => $row['fingerprint'],
        'license_key' => $row['license_key'],
        'created_at'  => $row['created_at'],
    ];
}

echo json_encode([
    'code' => 0,
    'data' => [
        'user' => [
            'uid'        => $userId,
            'username'   => isset($_SESSION['username']) ? $_SESSION['username'] : '',
        ],
        'balance' => [
            'balance_yuan'  => round($balanceCents / 100, 2),
            'frozen_yuan'   => round($frozenCents / 100, 2),
            'available_yuan'=> round($availableCents / 100, 2),
        ],
        'plugins' => array_values($PLUGINS),
        'orders'  => $orders,
    ],
], JSON_UNESCAPED_UNICODE);
