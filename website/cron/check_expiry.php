<?php
// ============================================================
// B6: 到期处理脚本
// 位置: /cron/check_expiry.php
// 查 user_pro_subscriptions 表（不查 ll_useregs）
// 建议 crontab: 每天凌晨 2:00 执行
//   0 2 * * * /usr/bin/php /www/wwwroot/7tan.com/cron/check_expiry.php
// ============================================================

if (PHP_SAPI !== 'cli') {
    http_response_code(403);
    die('仅限 CLI 执行');
}

require_once __DIR__ . '/../config/database.php';

$db  = get_db_connection();
$now = time();

echo "[" . date('Y-m-d H:i:s') . "] 专业版到期检查开始\n";
echo str_repeat('-', 50) . "\n";

// ============================================================
// 1. 7天内到期 → 发送站内信提醒
// ============================================================
$in_7_days = date('Y-m-d H:i:s', $now + 7 * 86400);
$now_str   = date('Y-m-d H:i:s', $now);

$stmt = $db->prepare(
    'SELECT s.user_id, u.username, s.expires_at
     FROM user_pro_subscriptions s
     JOIN ll_useregs u ON s.user_id = u.id
     WHERE s.status = 1
       AND s.expires_at > :now
       AND s.expires_at <= :in_7_days'
);
$stmt->execute([':now' => $now_str, ':in_7_days' => $in_7_days]);
$soon_users = $stmt->fetchAll(PDO::FETCH_ASSOC);

foreach ($soon_users as $user) {
    $days_left = max(0, (int)((strtotime($user['expires_at']) - $now) / 86400));

    // 发送站内信（依赖现有 user_messages 表）
    $stmt = $db->prepare(
        'INSERT INTO user_messages (user_id, title, content, type, created_at)
         VALUES (:uid, :title, :content, :type, NOW())'
    );
    $stmt->execute([
        ':uid'     => $user['user_id'],
        ':title'   => '专业版即将到期',
        ':content' => "尊敬的用户 {$user['username']}，您的专业版会员将在 {$days_left} 天后（"
                      . date('Y-m-d', strtotime($user['expires_at'])) . "）到期。续费可享优惠，点击查看：/user/pro",
        ':type'    => 'system',
    ]);

    echo "  📨 提醒: uid={$user['user_id']} {$user['username']} {$days_left}天后到期\n";
}

echo "  → 7天内到期提醒: " . count($soon_users) . " 人\n\n";

// ============================================================
// 2. 已到期 → 标记 status=0（不删记录，保留购买历史）
// ============================================================
$stmt = $db->prepare(
    'UPDATE user_pro_subscriptions
     SET status = 0
     WHERE status = 1 AND expires_at <= NOW()'
);
$stmt->execute();
$expired_count = $stmt->rowCount();

if ($expired_count > 0) {
    echo "  🔴 标记到期: {$expired_count} 条订阅记录已标记为过期\n\n";
} else {
    echo "  ✅ 无新到期订阅\n\n";
}

// ============================================================
// 3. 统计
// ============================================================
$stmt = $db->query(
    'SELECT COUNT(*) FROM user_pro_subscriptions WHERE status = 1 AND expires_at > NOW()'
);
$active_count = (int)$stmt->fetchColumn();

$stmt = $db->query(
    'SELECT COUNT(*) FROM user_pro_subscriptions WHERE status = 0'
);
$expired_total = (int)$stmt->fetchColumn();

echo str_repeat('-', 50) . "\n";
echo "统计: 活跃专业版 {$active_count} 人 | 累计过期 {$expired_total} 条\n";
echo "[" . date('Y-m-d H:i:s') . "] 检查完成\n";
