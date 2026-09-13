-- ============================================================
-- B1: 专业版订阅记录表（新建，不修改现有表）
-- 执行方式: 在 phpMyAdmin 或 MySQL 命令行执行
-- 适用: 7tan.com 现有数据库
-- ============================================================

-- ⚠️ 前置依赖（必须已存在）:
--   - ll_useregs       用户表（网站现有）
--   - user_balance     用户余额表（purchase.php 余额扣款依赖）
--   - user_messages    站内信表（check_expiry.php 到期提醒依赖）

-- ============================================================
-- 🆕 新建表: user_pro_subscriptions
-- 用户购买专业版后，在此表新增一条记录
-- 判断是否专业版: SELECT * FROM user_pro_subscriptions
--                  WHERE user_id=? AND status=1 AND expires_at > NOW()
-- ============================================================

CREATE TABLE IF NOT EXISTS user_pro_subscriptions (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    user_id         INT NOT NULL COMMENT '用户ID，关联 ll_useregs.id',
    plan            VARCHAR(20) NOT NULL COMMENT '套餐: monthly/quarterly/semi_annual/annual',
    months          INT NOT NULL COMMENT '购买月数',
    amount          DECIMAL(10,2) NOT NULL COMMENT '实付金额',
    pay_type        VARCHAR(20) NOT NULL DEFAULT 'balance' COMMENT '支付方式: balance=余额',
    trade_no        VARCHAR(64) COMMENT '关联扣款流水号',
    status          TINYINT DEFAULT 1 COMMENT '1=有效, 0=已过期/已退款',
    activated_at    DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '激活时间',
    expires_at      DATETIME NOT NULL COMMENT '到期时间',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES ll_useregs(id) ON DELETE CASCADE,
    INDEX idx_user (user_id),
    INDEX idx_expires (expires_at),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专业版订阅记录';

-- ============================================================
-- 说明
-- ============================================================
-- 1. 不修改 ll_useregs 表，完全独立
-- 2. 用户是否专业版 = 该用户在 user_pro_subscriptions 中有 status=1 且未过期的记录
-- 3. 续费 = INSERT 新记录，旧记录自然过期
-- 4. 退款 = UPDATE status=0
-- 5. 购买历史 = SELECT * FROM user_pro_subscriptions WHERE user_id=? ORDER BY id DESC
