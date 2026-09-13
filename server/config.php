<?php
/**
 * 管理后台 配置文件
 * 7Tan 版权所有
 */

// ── 时区统一为北京时间（防止 PHP 默认 UTC 导致统计口径偏移 8 小时）──
date_default_timezone_set('Asia/Shanghai');

// Session配置（只在未启动时配置）
if (session_status() === PHP_SESSION_NONE) {
    ini_set('session.cookie_httponly', 1);
    ini_set('session.cookie_samesite', 'Lax');
    session_name('ADMIN_SESSION');
    session_start();
}

// 数据库配置
define('DB_HOST', 'localhost');
define('DB_NAME', '7tan_cn');
define('DB_USER', 'root');
define('DB_PASS', '7233DB_Pass!2024');
define('DB_CHARSET', 'utf8mb4');

// PDO连接
function getDB(): PDO {
    static $pdo = null;
    if ($pdo === null) {
        try {
            $dsn = 'mysql:host=' . DB_HOST . ';dbname=' . DB_NAME . ';charset=' . DB_CHARSET;
            $pdo = new PDO($dsn, DB_USER, DB_PASS, [
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES => false,
            ]);
            // 强制设置字符集
            $pdo->exec("SET NAMES utf8mb4");
            $pdo->exec("SET CHARACTER SET utf8mb4");
        } catch (PDOException $e) {
            die('数据库连接失败: ' . $e->getMessage());
        }
    }
    return $pdo;
}

// 系统配置（从 set.inc 转换）
function getSettings(): array {
    static $settings = null;
    if ($settings === null) {
        $db = getDB();
        $stmt = $db->query("SELECT * FROM ll_admin WHERE id = 1 LIMIT 1");
        $settings = $stmt->fetch() ?: [];
    }
    return $settings;
}

// 会话超时时间（6小时 = 21600秒）
define('SESSION_TIMEOUT', 21600);

// 每页显示数量
define('PAGE_SIZE', 20);

// 初始化全局数据库连接（兼容 $pdo 和 $db 两种写法）
$pdo = getDB();
