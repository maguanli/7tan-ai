-- ============================================
-- 7Tan 客户端流量统计 - 建表 SQL
-- 
-- 部署方式:
--   在 phpMyAdmin 或 MySQL 命令行中执行本文件
--   或者直接访问 api/7tan_ping.php（自动建表）
-- ============================================

CREATE TABLE IF NOT EXISTS `7tan_client_sessions` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `device_id` VARCHAR(32) NOT NULL COMMENT '匿名设备标识(16位GUID)',
    `version` VARCHAR(16) DEFAULT 'unknown' COMMENT '客户端版本号',
    `username` VARCHAR(64) DEFAULT '' COMMENT '用户名(可选)',
    `first_date` DATE NOT NULL COMMENT '首次出现日期',
    `last_active` DATETIME NOT NULL COMMENT '最后活跃时间',
    `type` VARCHAR(10) DEFAULT '新设备' COMMENT '新设备/回头客',
    `ip_address` VARCHAR(45) DEFAULT '' COMMENT 'IP地址',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    
    INDEX `idx_device` (`device_id`),
    INDEX `idx_last_active` (`last_active`),
    INDEX `idx_first_date` (`first_date`),
    INDEX `idx_type` (`type`),
    INDEX `idx_version` (`version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='7Tan客户端会话记录';
