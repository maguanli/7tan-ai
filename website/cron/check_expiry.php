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



echo "[" . date('Y-m-d H:i:s') . "] 完整版到期检查开始\n";

echo str_repeat('-', 50) . "\n";



// ============================================================

// 1. 7天内到期 → 发送站内信提醒

//    expires_at 是 BIGINT Unix 时间戳

// ============================================================

$in_7_days = $now + 7 * 86400;



$stmt = $db->prepare(

    'SELECT s.user_id, u.ll_name, s.expires_at

     FROM user_pro_subscriptions s

     JOIN ll_useregs u ON s.user_id = u.id

     WHERE s.status = 1

       AND s.expires_at > :now

       AND s.expires_at <= :in_7_days'

);

$stmt->execute([':now' => $now, ':in_7_days' => $in_7_days]);

$soon_users = $stmt->fetchAll(PDO::FETCH_ASSOC);



foreach ($soon_users as $user) {

    $days_left = max(0, (int)(($user['expires_at'] - $now) / 86400));



    // 发送站内信（依赖 user_messages 表，不存在则跳过）

    try {

        $stmt = $db->prepare(

            'INSERT INTO user_messages (user_id, title, content, type, is_read, created_at)

             VALUES (:uid, :title, :content, :type, 0, :now)'

        );

        $stmt->execute([

            ':uid'     => $user['user_id'],

            ':title'   => '完整版即将到期',

            ':content' => "尊敬的用户 {$user['ll_name']}，您的完整版会员将在 {$days_left} 天后（"

                          . date('Y-m-d', $user['expires_at']) . "）到期。续费可享优惠，点击查看：/pro.php",

            ':type'    => 'system',

            ':now'     => $now,

        ]);

    } catch (PDOException $e) {

        // user_messages 表不存在，跳过站内信

    }



    echo "  📨 提醒: uid={$user['user_id']} {$user['ll_name']} {$days_left}天后到期\n";

}



echo "  → 7天内到期提醒: " . count($soon_users) . " 人\n\n";



// ============================================================

// 2. 处理已过期的完整版（标记为过期）

// ============================================================

$stmt = $db->prepare(

    'UPDATE user_pro_subscriptions

     SET status = 0

     WHERE status = 1 AND expires_at <= :now'

);

$stmt->execute([':now' => $now]);

$expired = $stmt->rowCount();



if ($expired > 0) {

    echo "  → 标记过期: {$expired} 条记录\n";

} else {

    echo "  → 无新过期记录\n";

}



echo str_repeat('-', 50) . "\n";

echo "[" . date('Y-m-d H:i:s') . "] 检查完成\n";

