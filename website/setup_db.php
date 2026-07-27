<?php
// ============================================================
// 一键建表脚本 — 上传后访问一次即可
// https://www.7tan.com/setup_db.php
// 安全：仅允许本地访问（上传后可临时注释掉）
// ============================================================

// ---- 安全锁：只允许本地访问（上传到服务器后取消注释） ----
// if ($_SERVER['REMOTE_ADDR'] !== '127.0.0.1' && $_SERVER['REMOTE_ADDR'] !== '::1') {
//     http_response_code(403);
//     die('Forbidden — 仅允许本地访问。上线后请删除此文件。');
// }

require_once __DIR__ . '/config/database.php';

header('Content-Type: text/plain; charset=utf-8');

try {
    $db = get_db_connection();
    echo "✅ 数据库连接成功\n\n";
} catch (Exception $e) {
    die("❌ 数据库连接失败: " . $e->getMessage());
}

// ============================================================
// 1. 用户专业版订阅表
// ============================================================
$sql1 = "CREATE TABLE IF NOT EXISTS user_pro_subscriptions (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id     BIGINT UNSIGNED NOT NULL COMMENT '关联 ll_useregs.id',
    plan        VARCHAR(20)  NOT NULL DEFAULT 'monthly' COMMENT '套餐: monthly/quarterly/semi_annual/annual',
    months      INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '购买月数',
    amount      DECIMAL(8,2) NOT NULL DEFAULT 0 COMMENT '实付金额',
    status      TINYINT      NOT NULL DEFAULT 1 COMMENT '1=有效, 0=已过期/已退款',
    activated_at BIGINT      NOT NULL COMMENT '激活时间戳',
    expires_at  BIGINT       NOT NULL COMMENT '到期时间戳',
    created_at  BIGINT       NOT NULL COMMENT '购买时间戳',

    INDEX idx_user_status  (user_id, status),
    INDEX idx_expires      (expires_at, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专业版订阅记录（独立于 ll_useregs）';";

try {
    $db->exec($sql1);
    echo "✅ user_pro_subscriptions 表就绪\n";
} catch (PDOException $e) {
    echo "⚠️  user_pro_subscriptions: " . $e->getMessage() . "\n";
}

// ============================================================
// 2. 通知消息表（check_expiry.php 发通知用，如果已有则跳过）
// ============================================================
$sql2 = "CREATE TABLE IF NOT EXISTS user_messages (
    id        BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id   BIGINT UNSIGNED NOT NULL,
    title     VARCHAR(255) NOT NULL DEFAULT '',
    content   TEXT,
    type      VARCHAR(20)  NOT NULL DEFAULT 'system' COMMENT 'system/pro_expiry/pro_renewal',
    is_read   TINYINT      NOT NULL DEFAULT 0,
    created_at BIGINT      NOT NULL,

    INDEX idx_user_read (user_id, is_read)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户消息/通知';";

try {
    $db->exec($sql2);
    echo "✅ user_messages 表就绪\n";
} catch (PDOException $e) {
    echo "⚠️  user_messages: " . $e->getMessage() . "\n";
}

// ============================================================
// 3. 如果原来 ll_useregs 有 pro_activated/pro_expires 字段，
//    把老数据迁移过来（可选，没有就跳过）
// ============================================================
try {
    $cols = $db->query("SHOW COLUMNS FROM ll_useregs LIKE 'pro_activated'");
    if ($cols->rowCount() > 0) {
        // 老字段存在，迁移数据
        $migrated = $db->exec("
            INSERT INTO user_pro_subscriptions (user_id, plan, months, amount, status, activated_at, expires_at, created_at)
            SELECT id, 'monthly', 1, 0, 1, UNIX_TIMESTAMP(), pro_expires, UNIX_TIMESTAMP()
            FROM ll_useregs
            WHERE pro_activated = 1 AND pro_expires > UNIX_TIMESTAMP()
            AND id NOT IN (SELECT user_id FROM user_pro_subscriptions)
        ");
        echo "✅ 已从 ll_useregs 迁移 {$migrated} 条旧专业版记录\n";
    } else {
        echo "ℹ️  ll_useregs 无旧专业版字段，跳过迁移\n";
    }
} catch (PDOException $e) {
    echo "ℹ️  迁移检查跳过: " . $e->getMessage() . "\n";
}

echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n";
echo "🎉 数据库初始化完成！\n";
echo "⚠️  安全提醒：执行完毕后请删除本文件 (setup_db.php)\n";
