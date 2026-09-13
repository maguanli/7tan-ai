<?php
header('Content-Type: text/plain; charset=utf-8');

require_once __DIR__ . '/config/database.php';

try {
    $db = get_db_connection();
    
    echo "=== 数据库: 7tan_cn ===\n\n";
    
    // 1. 列出所有表
    $tables = $db->query("SHOW TABLES")->fetchAll(PDO::FETCH_COLUMN);
    echo "--- 所有表 ---\n";
    foreach ($tables as $t) echo "  $t\n";
    
    // 2. 用户相关表的字段
    foreach ($tables as $t) {
        if (stripos($t, 'user') !== false || stripos($t, 'member') !== false) {
            echo "\n--- $t 字段 ---\n";
            $cols = $db->query("SHOW COLUMNS FROM `$t`")->fetchAll();
            foreach ($cols as $col) {
                echo "  {$col['Field']} ({$col['Type']})";
                if ($col['Key'] === 'PRI') echo " [PK]";
                echo "\n";
            }
        }
    }
    
    // 3. session 相关表
    foreach ($tables as $t) {
        if (stripos($t, 'session') !== false || stripos($t, 'sess') !== false) {
            echo "\n--- $t 字段 ---\n";
            $cols = $db->query("SHOW COLUMNS FROM `$t`")->fetchAll();
            foreach ($cols as $col) {
                echo "  {$col['Field']} ({$col['Type']})";
                if ($col['Key'] === 'PRI') echo " [PK]";
                echo "\n";
            }
            // 显示最近3条记录
            $rows = $db->query("SELECT * FROM `$t` LIMIT 3")->fetchAll();
            echo "  最近记录: ";
            print_r($rows);
        }
    }
    
    // 4. 检查 $_SESSION 当前值
    session_start();
    echo "\n--- \$_SESSION 内容 ---\n";
    print_r($_SESSION);
    
    // 5. 检查 Cookie
    echo "\n--- \$_COOKIE ---\n";
    print_r($_COOKIE);
    
} catch (Exception $e) {
    echo "错误: " . $e->getMessage();
}
