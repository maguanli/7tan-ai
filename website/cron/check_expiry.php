<?php
// ============================================================
// B6: 到期处理脚本
// 位置: /cron/check_expiry.php
// 建议 crontab: 每天凌晨 2:00 执行
//   0 2 * * * /usr/bin/php /www/wwwroot/7tan.com/cron/check_expiry.php
// ============================================================

// 只能在 CLI 下运行
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
// 1. 7天后到期 → 发送站内信提醒
// ============================================================
$in_7_days = $now + 7 * 86400;

$stmt = $db->prepare(
    'SELECT id, username, pro_expires
     FROM ll_useregs
     WHERE pro_activated = 1
       AND pro_expires > :now
       AND pro_expires <= :in_7_days'
);
$stmt->execute([':now' => $now, ':in_7_days' => $in_7_days]);
$soon_users = $stmt->fetchAll(PDO::FETCH_ASSOC);

foreach ($soon_users as $user) {
    $days_left = max(0, (int)(($user['pro_expires'] - $now) / 86400));

    // 发送站内信（假设网站有 messages 表）
    $stmt = $db->prepare(
        'INSERT INTO user_messages (user_id, title, content, type, created_at)
         VALUES (:uid, :title, :content, :type, NOW())'
    );
    $stmt->execute([
        ':uid'     => $user['id'],
        ':title'   => '专业版即将到期',
        ':content' => "尊敬的用户 {$user['username']}，您的专业版会员将在 {$days_left} 天后（"
                      . date('Y-m-d', $user['pro_expires']) . "）到期。续费可享优惠，点击查看：/user/pro",
        ':type'    => 'system',
    ]);

    echo "  📨 提醒: uid={$user['id']} {$user['username']} {$days_left}天后到期\n";
}

echo "  → 7天内到期提醒: " . count($soon_users) . " 人\n\n";

// ============================================================
// 2. 已过期 → 降级（不清除 pro_activated，只标记为已过期）
//    客户端通过 pro_expires < now 判断是否过期
// ============================================================
// 不需要额外操作：客户端和服务端都是通过 pro_activated=1 AND pro_expires>now 判断
// 过期用户 pro_expires < now，自动被视为 free 用户
// 但可以记录一条通知

$stmt = $db->prepare(
    'SELECT id, username, pro_expires
     FROM ll_useregs
     WHERE pro_activated = 1
       AND pro_expires <= :now
       AND pro_expires > :yesterday'  // 今天刚过期的
);
$stmt->execute([':now' => $now, ':yesterday' => $now - 86400]);
$expired_today = $stmt->fetchAll(PDO::FETCH_ASSOC);

foreach ($expired_today as $user) {
    // 发送到期通知
    $stmt = $db->prepare(
        'INSERT INTO user_messages (user_id, title, content, type, created_at)
         VALUES (:uid, :title, :content, :type, NOW())'
    );
    $stmt->execute([
        ':uid'     => $user['id'],
        ':title'   => '专业版已到期',
        ':content' => "尊敬的用户 {$user['username']}，您的专业版会员已于 "
                      . date('Y-m-d', $user['pro_expires']) . " 到期。续费可继续使用，点击查看：/user/pro",
        ':type'    => 'system',
    ]);

    echo "  ⏰ 到期: uid={$user['id']} {$user['username']}\n";
}

echo "  → 今日到期: " . count($expired_today) . " 人\n\n";

// ============================================================
// 3. 统计
// ============================================================
$stmt = $db->query('SELECT COUNT(*) FROM ll_useregs WHERE pro_activated = 1 AND pro_expires > ' . $now);
$active_count = (int)$stmt->fetchColumn();

$stmt = $db->query('SELECT COUNT(*) FROM ll_useregs WHERE pro_activated = 1 AND pro_expires <= ' . $now);
$expired_count = (int)$stmt->fetchColumn();

echo str_repeat('-', 50) . "\n";
echo "统计: 活跃专业版 {$active_count} 人 | 已过期未续 {$expired_count} 人\n";
echo "[" . date('Y-m-d H:i:s') . "] 检查完成\n";
