<?php
// ============================================================
// 数据库连接配置
// 位置: /config/database.php
// 
// ⚠️ 如果网站已有 get_db_connection() 函数，可跳过此文件，
//    只需确保 API 文件中能获取 PDO 连接即可。
// ============================================================

// 数据库配置（来自 D:\7T723\config.php）
define('DB_HOST', 'localhost');
define('DB_PORT', '3306');
define('DB_NAME', '7tan_cn');
define('DB_USER', 'root');
define('DB_PASS', '7233DB_Pass!2024');
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
define('JWT_SECRET', 'b0c7pzhKivuV1L08eNewzqocZT69tM7tti6HZlIIHcRY4iASSGrSQjUrlBSabt1q');

// ============================================================
// RSA 密钥对（服务端用私钥签发 pro_license，客户端用公钥验签）
// ⚠️ 私钥绝对不能泄露！部署后建议放到环境变量或独立文件中
// ============================================================
define('RSA_PRIVATE_KEY', <<<'EOD'
-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC4Htitb7hyt/R6
MG2ThTXweBLQcJj1T4VGeXeD3z8G4lF1aCB46WQel+anJgz8zLQVzet0CXKM7ZpI
Yq3Pl8YdG8NRKmjpo0PYIQVDOWtU2rcHg883/fwZ6trhiX8hThuvNKDaXFZiHN/I
6VAgaBjL8HnOKZx8sjJowoDo3GbtatISw3INGrMo04AjWLomAoLX4v9C6P/bWWVc
Iemurb3eXDUDOOAsr5LNS4XwnDBCfZmnzmqI7Pq/nyz4JCPKqGLLhYhmX4xF8ZAp
Z48ZkdFXfMJ4A9Rr3osPdCD+HgJK2x46QAW32w72rHo6G6ef/1zv8NBbwsVWwB+4
5xmdugy3AgMBAAECggEAWW0qAnsL1DRCuwJAhnEh9KztPm4h7Kv16Hfgs50/yIEt
3V94viFlrnJK5g5WKobmRNziKlbYW1igId5D21s1Lzgn0olNsYTJ0/Sd0LvXxLwC
P9UmVWS4CIKIUxjsNWnxilR+d/B3SGoLy1J+x26n9I3VK2wMhIgscbNe1zsNhuwS
/s/GVXCDS3EqgVUdpCJMcufB/zk/PB6gfREwBNYFEBydclbLcnzj96/HkbMcbOgg
Xt2mpMXEunIrBvp/cX4b+EqPG2cCueLgibKPQZA2Mz0C05x0qwXLBOvzgW5fARo9
obMP0Hc6gDL0tkVHN/aAH3QLCld/dAnfILuO+K74gQKBgQDjv5YAMijoExJd7+uW
4nw0frpJhDeNgMaLqV8Fv7kzJBPUTxwHwybLqjEpHo+9oxnAqtJGskc22cH2qVw0
VUoIawL/fb9Er1qZ6FrCAQpc8XKlUcufF7y4Xb6etxbT3CX47A89su/ayfxZIqq6
2j4TwQqQ2thMUnkK4sIqKMmD9wKBgQDO9c5lyjF5ysEwuLmvrOGsAmEKS6rvyAI5
yMCEY32JyR+piV1vqi9dtCSbTHMZ01T5j3AuRjF9u8+Tiv+y0XuNMbTchMDyd6+H
PTyxyFeF//yiWAANsxPu7wA+gixj8XnsTxPjfPG+G4u60EgIc+amiFajPkWKD/wh
2jdfAQQNQQKBgQDhCpC3xNiy6RV/CPFr+IPug0KkHieehR6rJkMktRvVMtL9OOZj
rSwKlzNYhEBYjG+H98Mr5EGGK4oDp7naZGRxCPy/ZIu43OTTq8ryZIDO8i3suXRQ
0e3C567Rueyuj5xd6TPuLX/gWzIlCaJWXAx3DIraM8UDNYMxhHuDmSX2ZQKBgGTR
zeg8ZXnFUfOgKaTw/UbEKe3QCsegkaUArPhRVzimJ6x5ZHEfYM+vEB4vUesEzmJ8
g9OnEjkEIwznK8U604tm6Yp7iVsU/wdMx6J7zFdU6wdTA0OpN06wU1ggJevSGOkL
ZM7vcPyBgsJQ8KZdf8Ekrb/8d/fX7aW4Hj1Dy2uBAoGABPL2vEkQezx0Orb6Dl4+
JJhSCMn2teoj5bPXnoXqHPGmoNVOZjk5pKTYIOWM4uHJVAjyq2865ZrxeSSlg5Tj
xvUqfQRZv1TCWndC8wkZfimB6qENC5/ESbQFDDONpGP7dKad+f8hOdM7YaVA23Oj
A3Y9L+HbthhsoLN98ugICIY=
-----END PRIVATE KEY-----
EOD);

// ============================================================
// DeepSeek API 配置（服务端持有，代理试用用户的 AI 请求）
// ⚠️ 部署前替换为真实 API Key
// ============================================================
define('DEEPSEEK_API_KEY', 'sk-your-deepseek-api-key-here');
define('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1');
define('TRIAL_MODEL', 'deepseek-chat');  // 试用用户使用的模型（建议用便宜的）
