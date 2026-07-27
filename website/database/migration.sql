-- ============================================================
-- B1: ll_useregs 表增加专业版字段
-- 执行方式: 在 phpMyAdmin 或 MySQL 命令行执行
-- 适用: 7tan.com 现有数据库
-- ============================================================

-- ⚠️ 前置条件: 以下表必须已存在
--   - ll_useregs       用户表（网站现有）
--   - user_balance     用户余额表（purchase.php 余额扣款依赖）
--   - user_messages    站内信表（check_expiry.php 到期提醒依赖）
--
-- ⚠️ MySQL 5.7 不支持 ADD COLUMN IF NOT EXISTS，重复执行会报错，忽略即可

ALTER TABLE ll_useregs
    ADD COLUMN pro_activated TINYINT(1) NOT NULL DEFAULT 0 COMMENT '专业版是否激活: 0=否, 1=是',
    ADD COLUMN pro_expires   BIGINT(20)  NOT NULL DEFAULT 0 COMMENT '专业版到期时间戳(Unix秒), 0=未激活/已过期';

-- 创建索引加速查询
ALTER TABLE ll_useregs
    ADD INDEX idx_pro_expires (pro_expires);

-- ============================================================
-- 可选: 专业版购买记录表（如果不想复用现有订单表）
-- 如果网站已有通用订单表，可以跳过此表，直接复用
-- ============================================================

-- CREATE TABLE IF NOT EXISTS pro_purchases (
--     id           INT PRIMARY KEY AUTO_INCREMENT,
--     user_id      INT NOT NULL,
--     plan         VARCHAR(20) NOT NULL COMMENT 'monthly/quarterly/semi_annual/annual',
--     months       INT NOT NULL DEFAULT 6,
--     amount       DECIMAL(10,2) NOT NULL,
--     pay_type     VARCHAR(20) NOT NULL COMMENT 'balance=余额支付',
--     trade_no     VARCHAR(64) COMMENT '关联的充值/扣款流水号',
--     status       TINYINT DEFAULT 1 COMMENT '1=已激活, 0=已退款',
--     activated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
--     expires_at   DATETIME DEFAULT NULL,
--     created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
--     FOREIGN KEY (user_id) REFERENCES ll_useregs(id),
--     INDEX idx_user (user_id),
--     INDEX idx_expires (expires_at)
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
