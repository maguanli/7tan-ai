<?php
// ============================================================
// 数据库连接配置（模板）
// 位置: /config/database.php
// 
// ⚠️ 如果网站已有数据库配置文件，请忽略此文件，
//    只需确保其他文件中的 get_db_connection() 函数存在即可。
// ============================================================

// 数据库配置
define('DB_HOST', '127.0.0.1');
define('DB_PORT', '3306');
define('DB_NAME', '7tan');
define('DB_USER', 'root');
define('DB_PASS', 'your-password-here');
define('DB_CHARSET', 'utf8mb4');

/**
 * 获取 PDO 数据库连接（单例）
 */
function get_db_connection(): PDO
{
    static $pdo = null;

    if ($pdo === null) {
        $dsn = sprintf(
            'mysql:host=%s;port=%s;dbname=%s;charset=%s',
            DB_HOST, DB_PORT, DB_NAME, DB_CHARSET
        );

        $pdo = new PDO($dsn, DB_USER, DB_PASS, [
            PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES   => false,
        ]);
    }

    return $pdo;
}

// ============================================================
// JWT 密钥（建议 64 字符随机字符串）
// 客户端 RSA 公钥验签用此密钥签发 JWT 的对称密钥
// ============================================================
define('JWT_SECRET', 'change-me-to-a-random-64-char-string-here-please!!!!');
