<?php
/**
 * 7坛社区
 * 深圳市柒贰叁叁网络科技有限公司版权所有
 */

// 错误报告（只报告严重错误，避免弃用警告污染JSON输出）
error_reporting(E_ERROR | E_PARSE | E_CORE_ERROR | E_USER_ERROR);
ini_set('display_errors', 0);

// 数据库配置
// 凭据来自机器级环境变量 TAN7_DB_*（不再明文硬编码于源码）。
// 若环境变量缺失，回退读取站外密钥文件 D:\workspace\_secrets\7tan_db.php
//（该文件不在网站根目录内、不进版本库）。
if (!function_exists('_tan7_db_env')) {
    function _tan7_db_env($key, $default = '') {
        static $sec = null;
        if ($sec === null) {
            $sec = array();
            $p = 'D:/workspace/_secrets/7tan_db.php';
            if (is_file($p)) { $t = include $p; if (is_array($t)) { $sec = $t; } }
        }
        if (isset($sec[$key]) && $sec[$key] !== '') { return $sec[$key]; }
        $v = getenv($key);
        if ($v !== false && $v !== '') { return $v; }
        return $default;
    }
}
define('DB_HOST', _tan7_db_env('TAN7_DB_HOST', '127.0.0.1'));
define('DB_NAME', _tan7_db_env('TAN7_DB_NAME', '7tan_cn'));
define('DB_USER', _tan7_db_env('TAN7_DB_USER', 'root'));
define('DB_PASS', _tan7_db_env('TAN7_DB_PASS', ''));
define('DB_CHARSET', 'utf8mb4');

// 网站配置
define('SITE_NAME', '7233社区');
define('SITE_URL', 'https://www.7tan.com');
define('BBS_URL', 'https://www.7tan.com/bbs');

// 基础URL
$baseUrl = '/bbs/';

// 旧上传目录URL (管理后台uploads目录，通过Junction链接)
$uploadUrl = '/bbs/uploads/';

// 分页大小
define('PAGE_SIZE', 20);

// 时区
date_default_timezone_set('Asia/Shanghai');

// 启动会话
// 1.1（2026-10-30）：bbs 页面不加载 bootstrap.php，会话 Cookie 安全属性在此单独设置
if (session_status() === PHP_SESSION_NONE) {
    if (!headers_sent()) {
        @ini_set('session.cookie_secure', '1');
        @ini_set('session.cookie_httponly', '1');
        @ini_set('session.cookie_samesite', 'Lax');
    }
    session_start();
}

/**
 * 获取数据库连接
 */
function getDB() {
    static $pdo = null;
    if ($pdo === null) {
        try {
            $dsn = 'mysql:host=' . DB_HOST . ';dbname=' . DB_NAME . ';charset=' . DB_CHARSET;
            $pdo = new PDO($dsn, DB_USER, DB_PASS, [
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES => false,
            ]);
        } catch (PDOException $e) {
            die('数据库连接失败: ' . $e->getMessage());
        }
    }
    return $pdo;
}

require_once __DIR__ . '/../bootstrap.php';

/**
 * HTML转义函数
 */
function e($str) {
    if ($str === null || $str === false) return '';
    return htmlspecialchars($str, ENT_QUOTES | ENT_HTML5, 'UTF-8');
}

/**
 * BBS CSRF token（独立于后台 common.php，避免函数冲突）
 */
function bbs_csrf_token() {
    if (empty($_SESSION['bbs_csrf_token'])) {
        $_SESSION['bbs_csrf_token'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['bbs_csrf_token'];
}

function bbs_csrf_field() {
    return '<input type="hidden" name="csrf_token" value="' . e(bbs_csrf_token()) . '">';
}

function bbs_verify_csrf() {
    $token = $_POST['csrf_token'] ?? '';
    if (empty($_SESSION['bbs_csrf_token']) || !hash_equals($_SESSION['bbs_csrf_token'], $token)) {
        http_response_code(403);
        die('无效的请求令牌，请刷新页面重试。');
    }
    return true;
}

/**
 * 全角转半角函数
 * 用于处理标题、板块名称、用户名等显示内容
 * 将全角数字和字母转换为标准半角字符
 */
function toHalfWidth($str) {
    if (empty($str)) return '';

    // 全角符号 -> 半角。与正文 bbs_ubb() 的映射保持一致；
    // 中文标点（，．：；！？）和括号（（）［］｛｝＜＞）不在此表内，一律保持全角。
    static $symbol_map = [
        '＃'=>'#','＄'=>'$','％'=>'%','＆'=>'&','＊'=>'*','＋'=>'+','－'=>'-',
        '／'=>'/','＝'=>'=','＠'=>'@','＾'=>'^','＿'=>'_','｀'=>'`','｜'=>'|',
    ];

    // 使用 mb_convert_kana 函数转换（需 mbstring 扩展）
    // 'rsn' = 全角字母(r) + 全角空格(s) + 全角数字(n)
    // 注意：不可用 'a'——它会把中文标点（，：；！？）一并转成半角
    if (function_exists('mb_convert_kana')) {
        return strtr(mb_convert_kana($str, 'rsn', 'UTF-8'), $symbol_map);
    }

    // 备用：手动映射表（行为与上面 'rsn' + $symbol_map 完全一致）
    static $map = [
        '０'=>'0','１'=>'1','２'=>'2','３'=>'3','４'=>'4','５'=>'5',
        '６'=>'6','７'=>'7','８'=>'8','９'=>'9',
        'ａ'=>'a','ｂ'=>'b','ｃ'=>'c','ｄ'=>'d','ｅ'=>'e','ｆ'=>'f',
        'ｇ'=>'g','ｈ'=>'h','ｉ'=>'i','ｊ'=>'j','ｋ'=>'k','ｌ'=>'l',
        'ｍ'=>'m','ｎ'=>'n','ｏ'=>'o','ｐ'=>'p','ｑ'=>'q','ｒ'=>'r',
        'ｓ'=>'s','ｔ'=>'t','ｕ'=>'u','ｖ'=>'v','ｗ'=>'w','ｘ'=>'x',
        'ｙ'=>'y','ｚ'=>'z',
        'Ａ'=>'A','Ｂ'=>'B','Ｃ'=>'C','Ｄ'=>'D','Ｅ'=>'E','Ｆ'=>'F',
        'Ｇ'=>'G','Ｈ'=>'H','Ｉ'=>'I','Ｊ'=>'J','Ｋ'=>'K','Ｌ'=>'L',
        'Ｍ'=>'M','Ｎ'=>'N','Ｏ'=>'O','Ｐ'=>'P','Ｑ'=>'Q','Ｒ'=>'R',
        'Ｓ'=>'S','Ｔ'=>'T','Ｕ'=>'U','Ｖ'=>'V','Ｗ'=>'W','Ｘ'=>'X',
        'Ｙ'=>'Y','Ｚ'=>'Z',
        '　'=>' ',
        '＃'=>'#','＄'=>'$','％'=>'%','＆'=>'&','＊'=>'*','＋'=>'+','－'=>'-',
        '／'=>'/','＝'=>'=','＠'=>'@','＾'=>'^','＿'=>'_','｀'=>'`','｜'=>'|',
    ];

    return strtr($str, $map);
}

/**
 * 获取当前用户ID
 */
function getCurrentUserId() {
    return isset($_SESSION['user_id']) ? intval($_SESSION['user_id']) : 0;
}

/**
 * 获取当前用户名
 */
function getCurrentUserName() {
    return isset($_SESSION['user_name']) ? $_SESSION['user_name'] : '';
}

/**
 * 检查用户是否已登录
 */
function isLoggedIn() {
    return getCurrentUserId() > 0;
}

/**
 * 获取用户信息
 */
function getUserInfo($userId) {
    $pdo = getDB();
    $stmt = $pdo->prepare('SELECT * FROM ll_useregs WHERE id = ?');
    $stmt->execute([$userId]);
    return $stmt->fetch();
}

/**
 * 伪静态URL生成函数（2025 SEO最佳实践）
 * 格式：/bbs/123/ （无扩展名）
 */
function bbsUrl($type, $id = null, $params = []) {
    $base = '/bbs/';
    switch ($type) {
        case 'topic':      // 帖子详情 (三级URL: /bbs/xxx/)
            return $base . intval($id) . '/';
        case 'board':      // 板块列表
            return $base . 'board/' . intval($id) . '/';
        case 'user':       // 用户主页
            return $base . 'user/' . intval($id) . '/';
        case 'post':       // 发帖页
            return $base . 'post/';
        case 'search':     // 搜索页
            return $base . 'search/';
        case 'message':    // 私信对话
            return $base . 'message.php?to=' . intval($id); // 私信需要参数，保持原样
        default:
            return $base;
    }
}

/**
 * 格式化时间
 */
function formatTime($timestamp) {
    if (empty($timestamp)) return '';
    
    if (is_numeric($timestamp)) {
        return date('Y-m-d H:i', $timestamp);
    }
    
    try {
        $date = new DateTime($timestamp);
        return $date->format('Y-m-d H:i');
    } catch (Exception $e) {
        return $timestamp;
    }
}

/**
 * 相对时间（多少分钟/小时/天前）
 */
function timeAgo($timestamp) {
    if (empty($timestamp)) return '';
    
    try {
        if (is_numeric($timestamp)) {
            $timestamp = '@' . $timestamp;
        }
        $date = new DateTime($timestamp);
        $now = new DateTime();
        $diff = $now->getTimestamp() - $date->getTimestamp();
        
        if ($diff < 60) return '刚刚';
        if ($diff < 3600) return str_replace('{n}', floor($diff / 60), '{n}分钟前');
        if ($diff < 86400) return str_replace('{n}', floor($diff / 3600), '{n}小时前');
        if ($diff < 604800) return str_replace('{n}', floor($diff / 86400), '{n}天前');
        
        return $date->format('Y-m-d');
    } catch (Exception $e) {
        return $timestamp;
    }
}

/**
 * 截断字符串
 */
function truncate($str, $length = 100, $suffix = '...') {
    if (mb_strlen($str) <= $length) return $str;
    return mb_substr($str, 0, $length) . $suffix;
}

/**
 * 获取板块名称
 */
function bbs_getCategoryName($categoryId) {
    $pdo = getDB();
    $stmt = $pdo->prepare('SELECT ll_title FROM ll_class WHERE id = ?');
    $stmt->execute([$categoryId]);
    $result = $stmt->fetch();
    return $result ? $result['ll_title'] : '未知板块';
}

/**
 * 获取帖子统计
 */
function getTopicStats($topicId) {
    $pdo = getDB();
    $stats = [];
    
    // 回复数
    $stmt = $pdo->prepare('SELECT COUNT(*) FROM ll_lthf WHERE ll_id = ?');
    $stmt->execute([$topicId]);
    $stats['replies'] = $stmt->fetchColumn();
    
    // 最后回复时间
    $stmt = $pdo->prepare('SELECT MAX(ll_time) FROM ll_lthf WHERE ll_id = ?');
    $stmt->execute([$topicId]);
    $stats['last_reply'] = $stmt->fetchColumn();
    
    return $stats;
}



/**
 * UBB内容处理（对应ASP的ubb1函数）
 * 处理全角转半角、把换行标记还原成<br>、转换UBB标签为HTML
 * 注意：此函数输出的HTML是安全的，不需要再转义
 */
function bbs_ubb($text) {
    if (empty($text)) return '';
    
    // 全角转半角映射
    static $fullwidth_map = null;
    if ($fullwidth_map === null) {
        $fullwidth_map = [
            '１' => '1', '２' => '2', '３' => '3', '４' => '4', '５' => '5',
            '６' => '6', '７' => '7', '８' => '8', '９' => '9', '０' => '0',
            '－' => '-', '％' => '%',
            '＋' => '+', '＝' => '=', '＊' => '*', '＆' => '&', '～' => '~',
            '（' => '(', '）' => ')', '［' => '[',
            '］' => ']', '｛' => '{', '｝' => '}', '＜' => '<', '＞' => '>',
            '￥' => '¥', '　' => ' ', '’' => "'", '"' => '"'
        ];
    }
    
    // 1. 全角转半角
    $text = strtr($text, $fullwidth_map);
    
    // 2. 换行标记转<br>
    $text = str_replace("\r\n", '<br>', $text);
    $text = str_replace("\n", '<br>', $text);
    $text = str_replace("\r", '<br>', $text);
    // 处理ASP存储的双反斜杠 \\ 换行
    $text = str_replace('\\\\', '<br>', $text);
    
    // 3. 对齐标签（需要先处理，避免被其他标签干扰）
    $text = preg_replace('/\((left)\)/i', '<div style="text-align:left;">', $text);
    $text = preg_replace('/\((center)\)/i', '<div style="text-align:center;">', $text);
    $text = preg_replace('/\((right)\)/i', '<div style="text-align:right;">', $text);
    $text = preg_replace('/<\/div>(\s*)<br>/i', '</div>$1', $text);
    
    // 4. 转换UBB标签（圆括号格式）
    $text = preg_replace('/\(b\)(.+?)\(\/b\)/is', '<strong>$1</strong>', $text);
    $text = preg_replace('/\(i\)(.+?)\(\/i\)/is', '<em>$1</em>', $text);
    $text = preg_replace('/\(u\)(.+?)\(\/u\)/is', '<u>$1</u>', $text);
    $text = preg_replace('/\(s\)(.+?)\(\/s\)/is', '<small>$1</small>', $text);
    $text = preg_replace('/\(strike\)(.+?)\(\/strike\)/is', '<del>$1</del>', $text);
    $text = preg_replace('/\(img\)(.{5,}?)\(\/img\)/is', '<a href="$1" target="_blank"><img src="$1" alt="图片" style="max-width:100%;max-height:400px;object-fit:contain;border-radius:8px;" loading="lazy"></a>', $text);
    $text = preg_replace('/\(nimg\)(.{5,}?)\(\/nimg\)/is', '<img src="$1" alt="图片" style="max-width:100%;max-height:400px;object-fit:contain;border-radius:8px;" loading="lazy">', $text);
    $text = preg_replace('/\(url\)(.{5,}?)\(\/url\)/is', '<a href="$1" target="_blank">$1</a>', $text);
    $text = preg_replace('/\(url=(.+?)\)(.+?)\(\/url\)/is', '<a href="$1" target="_blank">$2</a>', $text);
    $text = preg_replace('/\(quote\)(.+?)\(\/quote\)/is', '<blockquote style="border-left:3px solid #ccc;padding:5px 10px;margin:10px 0;background:#f9f9f9;">$1</blockquote>', $text);
    $text = preg_replace('/\(big\)(.+?)\(\/big\)/is', '<big>$1</big>', $text);
    $text = preg_replace('/\(small\)(.+?)\(\/small\)/is', '<small>$1</small>', $text);
    $text = preg_replace('/\(red\)(.+?)\(\/red\)/is', '<span style="color:red;">$1</span>', $text);
    $text = preg_replace('/\(green\)(.+?)\(\/green\)/is', '<span style="color:green;">$1</span>', $text);
    $text = preg_replace('/\(blue\)(.+?)\(\/blue\)/is', '<span style="color:blue;">$1</span>', $text);
    $text = preg_replace('/\(yellow\)(.+?)\(\/yellow\)/is', '<span style="color:yellow;">$1</span>', $text);
    $text = preg_replace('/\(marquee\)(.+?)\(\/marquee\)/is', '<marquee>$1</marquee>', $text);
    $text = preg_replace('/\(center\)(.+?)\(\/center\)/is', '<div style="text-align:center;">$1</div>', $text);
    $text = preg_replace('/\(left\)(.+?)\(\/left\)/is', '<div style="text-align:left;">$1</div>', $text);
    $text = preg_replace('/\(right\)(.+?)\(\/right\)/is', '<div style="text-align:right;">$1</div>', $text);
    $text = preg_replace('/\(code\)(.+?)\(\/code\)/is', '<pre style="background:#f5f5f5;padding:10px;overflow-x:auto;">$1</pre>', $text);
    $text = preg_replace('/\(li\)(.+?)\(\/li\)/is', '<li>$1</li>', $text);
    
    // 5. 转换UBB标签（方括号格式）
    $text = preg_replace('/\[img\](.+?)\[\/img\]/is', '<a href="$1" target="_blank"><img src="$1" alt="图片" style="max-width:100%;max-height:400px;object-fit:contain;border-radius:8px;" loading="lazy"></a>', $text);
    $text = preg_replace('/\[url=(.+?)\](.+?)\[\/url\]/is', '<a href="$1" target="_blank">$2</a>', $text);
    $text = preg_replace('/\[url\](.+?)\[\/url\]/is', '<a href="$1" target="_blank">$1</a>', $text);
    $text = preg_replace('/\[b\](.+?)\[\/b\]/is', '<strong>$1</strong>', $text);
    $text = preg_replace('/\[i\](.+?)\[\/i\]/is', '<em>$1</em>', $text);
    $text = preg_replace('/\[u\](.+?)\[\/u\]/is', '<u>$1</u>', $text);
    $text = preg_replace('/\[s\](.+?)\[\/s\]/is', '<small>$1</small>', $text);
    
    // 6. 表情标签 [/:name] 或 [/:XX] 格式 - 转换为表情图片
    // 常见论坛表情，如 [/pk] [/ye] [/xu] 等
    $text = preg_replace_callback('/\[\/:([a-zA-Z0-9]{1,8})\]/i', function($matches) {
        $emoji = strtolower($matches[1]);
        // 常见表情映射表
        $emoji_map = [
            'pk' => 'pkaigun', 'tu' => 'tushe', 'xu' => 'xuxiao', 'zk' => 'zuoya', 
            'jy' => 'jiayou', 'shui' => 'shuijiao', 'cy' => 'ciya', 'hx' => 'huaxin',
            'ng' => 'nu', 'han' => 'han', 'wb' => 'weibo', 'ld' => 'leng', 
            'fd' => 'fendou', 'yl' => 'yali', 'yz' => 'yinzhang', 'qiang' => 'qiang',
            'cd' => 'chidi', 'dao' => 'dao', 'baoquan' => 'baoquan', 'cai' => 'caidao',
            'ruo' => 'ruo', 'chang' => 'chang', 'ku' => 'ku', 'jing' => 'jing',
            'sx' => 'shengxin', 'gz' => 'guzhang', 'lw' => 'liwu', 'yy' => 'yinyue',
            'bd' => 'baodong', 'qushi' => 'qushi', 'chou' => 'chou', 'xiao' => 'xiaoku',
            'se' => 'seseme', 'baiyecao' => 'baiyecao', 'a' => 'a', 'b' => 'b',
            'c' => 'c', 'd' => 'd', 'e' => 'e', 'f' => 'f',
            'love' => 'love', 'ok' => 'ok', 'no' => 'no', 'ye' => 'yes'
        ];
        if (isset($emoji_map[$emoji])) {
            return '<img src="/images/face/' . $emoji_map[$emoji] . '.gif" alt="[:' . $emoji . ']" title="' . $emoji . '"/>';
        }
        return '[:' . $emoji . ']';
    }, $text);
    
    // 6.2 APP端表情标签 [表情名称] 格式 - 转换为表情图片
    // 支持 [笑] [加油] [大哭] 等APP端格式
    $emoji_map_app = [
        '笑' => '/images/20smile-smile.png',
        '大笑' => '/images/21lol.png',
        '俏皮' => '/images/19qiaopi.png',
        '加油' => '/images/08jiayou.png',
        '鼓鼓掌' => '/images/14guzhang.png',
        '牛' => '/images/11niubi.png',
        '怒了' => '/images/24angry.png',
        '哭泣' => '/images/25weep.png',
        '好失望' => '/images/18shiwang.png',
        '滴汗' => '/images/10han.png',
        '为什么' => '/images/13why.png',
        '摊手' => '/images/12hand.png',
        '好逊' => '/images/15xunka.png',
        '很赞' => '/images/03zan.png',
        '围观' => '/images/27weiguan.png',
        '心心' => '/images/36heart.png',
        '心碎了' => '/images/37heartbreak.png',
        '献花花' => '/images/38flower.png',
        '干杯' => '/images/40cheers.png',
        '能力圈' => '/images/33nengliquan.png',
        '毛估估' => '/images/06maogugu.png',
        '护城河' => '/images/28moat.png',
        '赚大了' => '/images/23earn.png',
        '亏大了' => '/images/09lose.png',
        '困顿' => '/images/26sleepy.png',
        '不说了' => '/images/17shutup.png',
        '好困惑' => '/images/43kunhuo.png',
        '想一下' => '/images/44sikao.png',
        '傲' => '/images/45aoman.png',
        '赞成' => '/images/05woshou.png',
        '不赞' => '/images/04bian.png',
    ];
    
    foreach ($emoji_map_app as $name => $url) {
        $text = str_replace('[' . $name . ']', '<img src="' . $url . '" alt="' . $name . '" title="' . $name . '" style="width:24px;height:24px;vertical-align:middle;"/>', $text);
    }
    
    // 7. @提及用户功能 - @用户名 或 @(用户名) 
    $text = preg_replace('/@(\w+)/i', '<span style="color:#1890ff;">@$1</span>', $text);
    $text = preg_replace('/@\((.+?)\)/i', '<span style="color:#1890ff;">@$1</span>', $text);
    
    // 7.5. ☆用户名☆(ID:数字) 格式的用户链接 - 转换为绿色可点击链接
    // 匹配 ☆用户名☆(ID:12345) 格式
    $text = preg_replace('/☆(.+?)☆\((ID:\d+)\)/i', '<a href="/bbs/user.php?id=$2" style="color:#52c41a;text-decoration:none;">☆$1☆($2)</a>', $text);
    // 单独的用户名☆(ID:数字) 格式
    $text = preg_replace('/(.+?)☆\((ID:\d+)\)/i', '<a href="/bbs/user.php?id=$2" style="color:#52c41a;text-decoration:none;">$1☆($2)</a>', $text);
    // 单独 ☆用户名☆(ID:数字) 格式（开头没有字符）
    $text = preg_replace('/^☆(.+?)☆\((ID:\d+)\)/i', '<a href="/bbs/user.php?id=$2" style="color:#52c41a;text-decoration:none;">☆$1☆($2)</a>', $text);
    
    // 8. 给img标签添加onerror处理
    $text = preg_replace_callback('/<img\s+([^>]*?)>/i', function($matches) {
        if (preg_match('/\bonerror\s*=/i', $matches[1])) {
            return $matches[0];
        }
        return '<img ' . $matches[1] . ' onerror="this.onerror=null;this.src=\'/images/blank.png\';this.alt=\'图片已丢失\';">';
    }, $text);
    
    return $text;
}

/**
 * 安全输出（保留UBB生成的HTML标签）
 * 注意：此函数应在ubb()之后调用，ubb()已经生成了安全的HTML
 */
function safe_output($text) {
    if (empty($text)) return '';
    // ubb()函数已经处理了HTML转义和UBB转换
    // 这里只需要确保输出是安全的，不再重复转义HTML标签
    return $text;
}

/**
 * Textarea安全输出 - 保留换行，不转义
 */
function textarea_escape($str) {
    if ($str === null || $str === false) return '';
    return htmlspecialchars($str, ENT_NOQUOTES, 'UTF-8');
}

/**
 * 简化UBB处理（对应ASP的ubb2函数）
 * 用于处理LOGO、图片等简单URL，不进行复杂的UBB标签转换
 * 只处理简单的 |分隔|格式 和 换行
 */
function bbs_ubb2($text) {
    if (empty($text)) return '';
    
    // 处理 |分隔| 格式：保留最后一个URL（通常是图片）
    if (strpos($text, '|') !== false) {
        $parts = explode('|', $text);
        // 过滤出有效的URL
        $urls = [];
        foreach ($parts as $part) {
            $part = trim($part);
            // 跳过说明文字，保留URL
            if (preg_match('/\.(jpg|jpeg|png|gif|webp|svg)/i', $part) || 
                strpos($part, 'uploads/') === 0 || 
                strpos($part, 'http') === 0) {
                $urls[] = $part;
            }
        }
        if (!empty($urls)) {
            return end($urls); // 返回最后一个URL
        }
    }
    
    // 处理换行符
    $text = str_replace(["\r\n", "\n", "\r"], ' ', $text);
    
    return trim($text);
}

/**
 * 清除首页缓存（主站 + 论坛列表）
 * 发帖/编辑/回复/锁定后调用，确保首页即时更新
 */
function clearHomeCache() {
    $files = [
        __DIR__ . '/../cache/home.cache',
        __DIR__ . '/../cache/bbs/home.cache',
    ];
    foreach ($files as $f) {
        if (file_exists($f)) {
            @unlink($f);
        }
    }
}

/**
 * 清除某帖子的详情页缓存（所有排序 × 所有语言）
 *
 * 刻意按已知文件名逐个 unlink，而不用 glob()：
 * cache/topic 实测有 78 万个文件，glob 每次都要枚举整个目录，NTFS 上开销极大。
 * 文件名规则是确定的，见 bbs/view.php：{topicId}_{ASC|DESC}_{LANG}.cache
 *
 * @param int $topicId 帖子 ID
 * @return int 实际删除的文件数
 */
function clearTopicCache($topicId) {
    $topicId = (int)$topicId;
    if ($topicId <= 0) {
        return 0;
    }
    $dir = __DIR__ . '/../cache/topic/';
    $langs = array('zh', 'zh-tw', 'en', 'ja', 'ko', 'es', 'fr', 'de', 'ru', 'pt', 'vi', 'th', 'id', 'ar');
    $deleted = 0;
    foreach (array('ASC', 'DESC') as $sort) {
        foreach ($langs as $lang) {
            $file = $dir . $topicId . '_' . $sort . '_' . $lang . '.cache';
            if (is_file($file) && @unlink($file)) {
                $deleted++;
            }
        }
    }
    return $deleted;
}

/**
 * 判断当前请求是否来自搜索引擎爬虫 / 自动化客户端
 *
 * 用途：浏览量统计去噪。本站爬虫流量远大于真人
 * （8 天就在 cache/topic 里生成了 78 万个缓存文件），若把爬虫计入浏览量会严重虚高。
 *
 * @return bool true = 机器人
 */
function isBotRequest() {
    static $isBot = null;
    if ($isBot !== null) {
        return $isBot;
    }
    $ua = strtolower(isset($_SERVER['HTTP_USER_AGENT']) ? $_SERVER['HTTP_USER_AGENT'] : '');
    if ($ua === '') {
        return $isBot = true; // 无 UA，一律按机器人处理
    }
    $tokens = array(
        'bot', 'spider', 'crawl', 'slurp', 'yandex', 'sogou', 'duckduck',
        'semrush', 'ahrefs', 'mj12', 'dotbot', 'petalbot', 'bytespider',
        'facebookexternalhit', 'python-requests', 'python-urllib',
        'curl/', 'wget/', 'go-http-client', 'okhttp', 'java/', 'libwww',
        'scrapy', 'headlesschrome', 'lighthouse', 'pingdom', 'uptimerobot',
        'exabot', 'ia_archiver', 'archive.org_bot', 'applebot',
    );
    foreach ($tokens as $token) {
        if (strpos($ua, $token) !== false) {
            return $isBot = true;
        }
    }
    return $isBot = false;
}
