<?php
/**
 * 7坛社区
 * 深圳市柒贰叁叁网络科技有限公司版权所有
 */
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/strip_ubb.php';
require_once __DIR__ . '/_board_seo.php';

$pdo = getDB();

// 获取版块ID
$bankuaiId = isset($_GET['id']) ? intval($_GET['id']) : 0;
$filter = isset($_GET['filter']) ? trim($_GET['filter']) : '';
$page = isset($_GET['page']) ? max(1, intval($_GET['page'])) : 1;

// 旧格式 ?filter=xx / ?page=N → 301 重定向到伪静态路径（消除重复内容，统一被收录 URL）
// 说明：比较时剥掉语言前缀，跳转目标保留当前语言前缀；已是规范路径则不动，杜绝重定向环
if ($bankuaiId > 0) {
    $__origUri = isset($_SERVER['HTTP_X_ORIGINAL_URI']) && $_SERVER['HTTP_X_ORIGINAL_URI'] !== ''
               ? $_SERVER['HTTP_X_ORIGINAL_URI']
               : (isset($_SERVER['REQUEST_URI']) ? $_SERVER['REQUEST_URI'] : '');
    $__origPath = strtok($__origUri, '?');
    if ($__origPath === false || $__origPath === '') $__origPath = '/';
    $__origNoLang = preg_replace('#^/(en|ja|ko|es|fr|de|ru|pt|vi|th|id|ar|zh-tw)(?=/|$)#', '', $__origPath);
    if ($__origNoLang === '' || $__origNoLang === false) $__origNoLang = '/';

    $__canonPath = '/bbs/board/' . $bankuaiId;
    if ($filter) $__canonPath .= '_' . urlencode($filter);
    if ($page > 1) $__canonPath .= '_' . $page;
    $__canonPath .= '/';

    $__legacyQuery = (bool) preg_match('/[?&](page|filter)=/', $__origUri);
    if ($__legacyQuery || rtrim($__origNoLang, '/') !== rtrim($__canonPath, '/')) {
        header('HTTP/1.1 301 Moved Permanently');
        header('Location: ' . $__canonPath);
        exit;
    }
}
$pageSize = 20;
$offset = ($page - 1) * $pageSize;

// 获取版块信息
$bankuai = null;
$isFollowing = false;
$topicCount = 0;
$todayCount = 0;
$banzhuList = [];
$bankuais = [];
$currentUser = isLoggedIn() ? getUserInfo(getCurrentUserId()) : null;

if ($bankuaiId > 0) {
    $stmt = $pdo->prepare("SELECT id, ll_title, ll_titleb, ll_wel, ll_text, ll_logo, ll_page FROM ll_class WHERE id = ?");
    $stmt->execute([$bankuaiId]);
    $bankuai = $stmt->fetch();

    // 版块不存在 → 404（修复软404：无效版块 id 曾返回 200，会被搜索引擎当作正常页收录）
    if (!$bankuai) {
        http_response_code(404);
        require __DIR__ . '/../404.php';
        exit;
    }
    
    // 获取版主列表
    $stmt = $pdo->prepare("
        SELECT b.id as bz_id, b.ll_idd, b.ll_useid, b.ll_shangxian, b.ll_retime,
               u.ll_n_name, u.ll_name, u.ll_img, u.ll_dj
        FROM ll_ltbz b
        LEFT JOIN ll_useregs u ON b.ll_useid = u.id
        WHERE b.ll_idd = ? AND b.ll_shangxian = 0
        ORDER BY b.id DESC
    ");
    $stmt->execute([$bankuaiId]);
    $banzhuList = $stmt->fetchAll();
    
    // 检查当前用户是否已关注该板块
    if (isLoggedIn()) {
        $stmt = $pdo->prepare("SELECT id FROM ll_follow WHERE ll_useid = ? AND ll_idd = ? AND ll_type = 1");
        $stmt->execute([getCurrentUserId(), $bankuaiId]);
        $isFollowing = $stmt->fetch() !== false;
    }
    
    // 统计帖子数和今日新帖（包括ll_or为NULL的帖子）
    $stmt = $pdo->prepare("SELECT COUNT(*) FROM ll_lt WHERE ll_idd = ? AND IFNULL(ll_or, 0) = 0");
    $stmt->execute([$bankuaiId]);
    $topicCount = $stmt->fetchColumn();
    
    $stmt = $pdo->prepare("SELECT COUNT(*) FROM ll_lt WHERE ll_idd = ? AND IFNULL(ll_or, 0) = 0 AND DATE(ll_time1) = CURDATE()");
    $stmt->execute([$bankuaiId]);
    $todayCount = $stmt->fetchColumn();
}

// 获取版块列表（包含ll_cc=2和ll_cc=12的主要板块）
$stmt = $pdo->prepare("SELECT id, ll_title, ll_page FROM ll_class WHERE ll_cc IN (2) ORDER BY ll_page ASC, id ASC");
$stmt->execute();
$bankuais = $stmt->fetchAll();

// 获取初始数据
$topics = [];
if ($bankuaiId > 0 || $filter) {
    $countConditions = ['IFNULL(ll_or, 0) = 0'];
    if ($bankuaiId > 0) {
        $countConditions[] = 'll_idd = ' . intval($bankuaiId);
    }
    $filterCondition = '';
    $filterConditionCount = ''; // 用于 COUNT 查询（无表别名）
    $orderBy = 't.ll_time2 DESC, t.ll_jh DESC, t.ll_time1 DESC';
    if ($filter === 'jing') {
        $filterCondition = ' AND t.ll_jh = 1';
        $filterConditionCount = ' AND ll_jh = 1';
        $orderBy = 't.ll_time2 DESC, t.ll_jh DESC';
    } elseif ($filter === 'ding') {
        $filterCondition = " AND t.ll_time2 = '2100-10-10 12:12:12'";
        $filterConditionCount = " AND ll_time2 = '2100-10-10 12:12:12'";
        $orderBy = 't.ll_time2 DESC';
    }
    $countWhereClause = implode(' AND ', $countConditions) . $filterConditionCount;
    $whereClause = 'IFNULL(t.ll_or, 0) = 0' . ($bankuaiId > 0 ? ' AND t.ll_idd = ' . intval($bankuaiId) : '') . $filterCondition;
    
    // 统计总数
    $countSql = "SELECT COUNT(*) FROM ll_lt WHERE $countWhereClause";
    $stmt = $pdo->prepare($countSql);
    $stmt->execute();
    $total = $stmt->fetchColumn();
    $totalPages = max(1, ceil($total / $pageSize));

    // 页码越界 → 301 回第 1 页（修复软404：越界页曾返回 200 空列表，与其它列表页行为统一）
    if ($page > $totalPages) {
        $__backList = '/bbs/board/' . $bankuaiId . ($filter ? '_' . $filter : '') . '/';
        header('Location: ' . $__backList, true, 301);
        exit;
    }
    
    // 获取初始帖子 - 使用LEFT JOIN代替子查询优化性能
    $listSql = <<<SQL
        SELECT t.id, t.ll_idd, t.ll_useid, t.ll_biaoti, t.ll_text, t.ll_rc, t.ll_rcd, 
               t.ll_jh, t.ll_lock, t.ll_ding, t.ll_jing, t.ll_time1, t.ll_time2, t.ll_furl, t.ll_url, t.ll_zan,
               u.ll_n_name as nickname, u.ll_name as username, u.ll_img as headimg,
               COALESCE(r.reply_count, 0) as ll_rchf
        FROM ll_lt t
        LEFT JOIN ll_useregs u ON t.ll_useid = u.id
        LEFT JOIN (SELECT ll_id, COUNT(*) as reply_count FROM ll_lthf GROUP BY ll_id) r ON t.id = r.ll_id
        WHERE {$whereClause}
        ORDER BY {$orderBy}
        LIMIT {$pageSize} OFFSET {$offset}
    SQL;
    $stmt = $pdo->prepare($listSql);
    $stmt->execute();
    $topics = $stmt->fetchAll();
} else {
    // 全部帖子
    $filterCondition = '';
    $filterConditionCount = ''; // 用于 COUNT 查询（无表别名）
    $orderBy = 't.ll_time2 DESC, t.ll_jh DESC, t.ll_time1 DESC';
    if ($filter === 'jing') {
        $filterCondition = ' AND t.ll_jh = 1';
        $filterConditionCount = ' AND ll_jh = 1';
        $orderBy = 't.ll_time2 DESC, t.ll_jh DESC';
    } elseif ($filter === 'ding') {
        $filterCondition = " AND t.ll_time2 = '2100-10-10 12:12:12'";
        $filterConditionCount = " AND ll_time2 = '2100-10-10 12:12:12'";
        $orderBy = 't.ll_time2 DESC';
    }
    $whereClause = 'IFNULL(t.ll_or, 0) = 0' . $filterCondition;
    
    $countSql = "SELECT COUNT(*) FROM ll_lt WHERE IFNULL(ll_or, 0) = 0" . $filterConditionCount;
    $stmt = $pdo->prepare($countSql);
    $stmt->execute();
    $total = $stmt->fetchColumn();
    $totalPages = max(1, ceil($total / $pageSize));

    // 页码越界 → 301 回第 1 页（修复软404：越界页曾返回 200 空列表，与其它列表页行为统一）
    if ($page > $totalPages) {
        $__backList = '/bbs/board/' . $bankuaiId . ($filter ? '_' . $filter : '') . '/';
        header('Location: ' . $__backList, true, 301);
        exit;
    }
    
    $listSql = <<<SQL
        SELECT t.id, t.ll_idd, t.ll_useid, t.ll_biaoti, t.ll_text, t.ll_rc, t.ll_rcd, 
               t.ll_jh, t.ll_lock, t.ll_ding, t.ll_jing, t.ll_time1, t.ll_time2, t.ll_furl, t.ll_url, t.ll_zan,
               u.ll_n_name as nickname, u.ll_name as username, u.ll_img as headimg,
               COALESCE(r.reply_count, 0) as ll_rchf
        FROM ll_lt t
        LEFT JOIN ll_useregs u ON t.ll_useid = u.id
        LEFT JOIN (SELECT ll_id, COUNT(*) as reply_count FROM ll_lthf GROUP BY ll_id) r ON t.id = r.ll_id
        WHERE {$whereClause}
        ORDER BY {$orderBy}
        LIMIT {$pageSize} OFFSET {$offset}
    SQL;
    $stmt = $pdo->prepare($listSql);
    $stmt->execute();
    $topics = $stmt->fetchAll();
}
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <base href="/bbs/">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <?php
    // SEO meta
    // 版块页：标题/描述取自 board_seo.php 的人工元数据（37 个版块逐一撰写），
    // 保证 title 落在 Bing 建议的 30-65、description 落在 85-160；
    // 未收录版块自动回退到 ll_titleb -> 通用描述，不会出现空描述。
    if ($bankuai) {
        $__bmeta   = board_seo_meta((int)$bankuaiId, $bankuai);
        $pageTitle = $__bmeta['title'];
        $pageDesc  = $__bmeta['desc'];
    } else {
        $pageTitle = '全部帖子 - 7坛游戏社区';
        $pageDesc  = '7坛游戏社区全部帖子列表，按最新回复与发布时间汇总各版块帖子、热门讨论与资源分享，轻松游戏，快乐分享。';
    }

    $pageImage = '';
    if ($bankuai && !empty($bankuai['ll_logo'])) {
        $pageImage = (strpos($bankuai['ll_logo'], 'http') === 0) ? $bankuai['ll_logo'] : 'https://img.7tan.com/' . ltrim($bankuai['ll_logo'], '/');
    }
    // 2.9（2026-10-30）：板块 logo 文件名带中文（如「游戏交流.png」），og:image 里必须百分号编码，
    // 否则微信/QQ/Facebook 抓取器取值失败、卡片无图。
    // 只编码非 ASCII 字符，保留 : / ? 等 ASCII 结构；不能用 urlencode()（会把 / 也编码掉）。
    $pageImageOgp = ($pageImage === '') ? '' : preg_replace_callback(
        '/[^\x21-\x7E]/u',
        function ($m) { return rawurlencode($m[0]); },
        $pageImage
    );
    // canonical 用的规范路径
    $__hreflangPath = '/bbs/board/' . $bankuaiId;
    if ($filter) $__hreflangPath .= '_' . urlencode($filter);
    if ($page > 1) $__hreflangPath .= '_' . $page;
    $__hreflangPath .= '/';
    ?>
    <title><?php echo $pageTitle; ?></title>
    <meta name="description" content="<?php echo htmlspecialchars($pageDesc, ENT_QUOTES); ?>">
    <meta name="keywords" content="<?php echo htmlspecialchars(($bankuai ? toHalfWidth($bankuai['ll_title']) . ',' : '') . '游戏论坛,7坛社区', ENT_QUOTES); ?>">
    <?php
    // 深分页治理 20261006：列表页第 11 页起输出 noindex,follow。
    // 背景："全部帖子"(id=0) 存在 3000+ 页近乎重复的列表页，深分页无独立价值，
    //       长期占用必应抓取预算。保留 follow 继续传递链接权重；canonical/prev/next 不变。
    $__deepPage = ($bankuaiId === 0 && $page > 10);
    ?>
    <meta name="robots" content="<?php echo $__deepPage ? 'noindex, follow' : 'index, follow'; ?>">
    <meta name="applicable-device" content="pc,mobile">
    <?php
    // 分页 SEO: canonical + prev/next（覆盖所有列表页，含"全部帖子" id=0）
        // 一律使用相对路径 canonical（与首页/帖子页一致）
        // 原写法用 $_SERVER['HTTPS'] 判协议，PHP 在 nginx 反代后取不到该值，会写出 http:// 与 sitemap 冲突
        // 相对 canonical 会按当前页面解析，天然指向当前语言版本自身，不会误指中文页
        // 2.4（2026-10-30）：canonical / prev / next 一律输出绝对地址
        $seoUrl = function($p) use ($bankuaiId, $filter) {
            $path = '/bbs/board/' . $bankuaiId;
            if ($filter) $path .= '_' . urlencode($filter);
            if ($p > 1) $path .= '_' . $p;
            $path .= '/';
            return htmlspecialchars(SITE_URL . $path, ENT_QUOTES);
        };
    ?>
    <link rel="canonical" href="<?php echo $seoUrl($page); ?>">
    <?php if ($page > 1): ?>
    <link rel="prev" href="<?php echo $seoUrl($page - 1); ?>">
    <?php endif; ?>
    <?php if ($page < $totalPages): ?>
    <link rel="next" href="<?php echo $seoUrl($page + 1); ?>">
    <?php endif; ?>
    <!-- Open Graph -->
    <meta property="og:type" content="website">
    <meta property="og:title" content="<?php echo htmlspecialchars(strip_tags($pageTitle), ENT_QUOTES); ?>">
    <meta property="og:description" content="<?php echo htmlspecialchars($pageDesc, ENT_QUOTES); ?>">
    <meta property="og:site_name" content="7坛游戏社区">
    <meta property="og:url" content="<?php echo htmlspecialchars(SITE_URL . $__hreflangPath, ENT_QUOTES); ?>">
    <?php if ($pageImageOgp !== ''): ?>
    <meta property="og:image" content="<?php echo htmlspecialchars($pageImageOgp, ENT_QUOTES); ?>">
    <?php endif; ?>
    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="<?php echo htmlspecialchars(strip_tags($pageTitle), ENT_QUOTES); ?>">
    <meta name="twitter:description" content="<?php echo htmlspecialchars($pageDesc, ENT_QUOTES); ?>">
    <?php if ($pageImageOgp !== ''): ?>
    <meta name="twitter:image" content="<?php echo htmlspecialchars($pageImageOgp, ENT_QUOTES); ?>">
    <?php endif; ?>
    <!-- 面包屑 JSON-LD -->
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": <?php echo json_encode('首页', JSON_UNESCAPED_UNICODE); ?>, "item": "https://www.7tan.com/"},
            {"@type": "ListItem", "position": 2, "name": <?php echo json_encode($bankuai ? toHalfWidth($bankuai['ll_title']) : '全部帖子', JSON_UNESCAPED_UNICODE); ?>}
        ]
    }
    </script>
    <link rel="stylesheet" href="/bbs/css/style.css?v=20261030">
    <link rel="stylesheet" href="/bbs/css/mobile-nav.css?v=20260919">
<style>
/* 分页导航：确保始终一行 */
.pagination-list,
.pagination-list li {
    list-style: none !important;
    margin: 0 !important;
    padding: 0 !important;
}
.pagination-list {
    display: inline-flex !important;
    align-items: center;
    gap: 6px;
    flex-wrap: nowrap;
}
.pagination-list li {
    display: inline-flex !important;
    flex-shrink: 0;
    float: none !important;
}
.pagination-list li::marker { display: none !important; content: none !important; }
</style>
<script>
var _hmt = _hmt || [];
(function() {
  var hm = document.createElement("script");
  hm.src = "https://hm.baidu.com/hm.js?f5f121dbbaa5fca7a5d5fba84a19576c";
  var s = document.getElementsByTagName("script")[0]; 
  s.parentNode.insertBefore(hm, s);
})();
</script>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-9874557266132949" crossorigin="anonymous"></script>
</head>
<body>
    <header class="header">
        <div class="container">
            <div class="header-content">
                <a href="/" class="logo">
                    <span class="logo-icon">🎮</span>
                    <span class="logo-text">7坛游戏社区</span>
                </a>
                <nav class="nav">
                    <a href="https://www.7tan.com/">首页</a>
                    <a href="/android/">游戏</a>
                    <a href="/baike/">百科</a>
                    <a href="https://www.7tan.com/ai-tool/">AI工具</a>
                    <a href="/game-creator/">做游戏</a>
                    <?php if ($currentUser): ?>
                        <a href="/bbs/user.php"><?php echo e($currentUser['ll_n_name'] ?: $currentUser['ll_name']); ?></a>
                        <a href="/bbs/logout.php">退出</a>
                    <?php else: ?>
                        <a href="/bbs/login.php">登录</a>
                    <?php endif; ?>
                </nav>
            </div>
        </div>
    </header>

    <main class="main">
        <div class="container">
            <div class="breadcrumb">
                <a href="/">首页</a>
                <?php if ($bankuai): ?>
                <span class="separator">></span>
                <span class="current"><?php echo e(toHalfWidth($bankuai['ll_title'])); ?></span>
                <?php else: ?>
                <span class="separator">></span>
                <h1 class="current" style="display:inline;font-size:13px;font-weight:normal;color:#333;margin:0;padding:0;border:0;">全部帖子</h1>
                <?php endif; ?>
            </div>

            <div class="content-wrapper">
                <div class="forum-content">
                    <!-- 操作栏 -->
                    <div class="action-bar">
                        <div class="filter-tabs">
                            <?php
                            $boardBase = $bankuaiId ? '/bbs/board/' . $bankuaiId : '/bbs/list.php';
                            $jingUrl = $bankuaiId ? $boardBase . '_jing/' : $boardBase . '?filter=jing';
                            $dingUrl = $bankuaiId ? $boardBase . '_ding/' : $boardBase . '?filter=ding';
                            ?>
                            <a href="<?php echo $bankuaiId ? $boardBase . '/' : $boardBase; ?>" class="<?php echo !$filter ? 'active' : ''; ?>">全部</a>
                            <a href="<?php echo $jingUrl; ?>" class="<?php echo $filter === 'jing' ? 'active' : ''; ?>">精华</a>
                            <a href="<?php echo $dingUrl; ?>" class="<?php echo $filter === 'ding' ? 'active' : ''; ?>">置顶</a>
                        </div>
                        <?php if ($bankuaiId == 3): ?>
                        <a href="/task/publish.php" class="btn btn-primary">发布现金任务</a>
                        <?php else: ?>
                        <a href="/bbs/post.php<?php echo $bankuaiId ? '?bankuai=' . $bankuaiId : ''; ?>" class="btn btn-primary">发布帖子</a>
                        <?php endif; ?>
                    </div>

                    <!-- 帖子列表（APP风格卡片）- 无限滚动 -->
                    <div class="post-card-list" id="postList">
                        <?php if (empty($topics)): ?>
                        <?php if ($bankuaiId == 3): ?>
                        <div class="empty-tip">暂无任务，<a href="/task/publish.php">来发第一个</a></div>
                        <?php else: ?>
                        <div class="empty-tip">暂无帖子，<a href="/bbs/post.php<?php echo $bankuaiId ? '?bankuai=' . $bankuaiId : ''; ?>">来发第一个</a></div>
                        <?php endif; ?>
                        <?php else: ?>
                        <?php foreach ($topics as $topic): ?>
                        <?php 
                            $displayName = $topic['nickname'] ?: ($topic['username'] ?: '用户' . $topic['ll_useid']);
                            $displayNameT = $displayName;
                            $headimg = $topic['headimg'] ?: '/images/avatar_default.png';
                            $content = preg_replace('/\[图片\]/u', ' ', strip_tags(stripUBB($topic['ll_text'])));
                            $content = mb_strlen($content) > 100 ? mb_substr($content, 0, 100) . '...' : $content;
                            $content = toHalfWidth($content);
                            $isTop = $topic['ll_time2'] === '2100-10-10 12:12:12';
                            $isJing = !empty($topic['ll_jh']);
                            $isLock = !empty($topic['ll_lock']);
                        ?>
                        <div class="post-card <?php echo $isTop ? 'post-top' : ''; ?>">
                            <!-- 用户信息 -->
                            <div class="post-card-header">
                                <div class="post-author">
                                    <img src="<?php echo e($headimg); ?>" alt="" class="post-avatar" width="40" height="40" loading="lazy" decoding="async" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                                    <div class="post-avatar-fallback" style="display:none; width:40px; height:40px; border-radius:50%; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); align-items:center; justify-content:center; color:#fff; font-size:16px; font-weight:bold;">
                                        <?php echo mb_substr($displayNameT, 0, 1); ?>
                                    </div>
                                    <div class="post-author-info">
                                        <span class="post-author-name"><?php echo e($displayNameT); ?></span>
                                        <span class="post-time"><?php echo formatTime($topic['ll_time1']); ?></span>
                                    </div>
                                </div>
                                <?php if ($isTop): ?><span class="post-tag tag-top">置顶</span><?php endif; ?>
                                <?php if ($isJing): ?><span class="post-tag tag-jing">精华</span><?php endif; ?>
                                <?php if ($isLock): ?><span class="post-tag tag-lock">锁定</span><?php endif; ?>
                            </div>
                            
                            <!-- 帖子内容 -->
                            <a href="<?php echo bbsUrl('topic', $topic['id']); ?>" class="post-card-body" style="text-decoration:none;color:inherit;">
                                <h3 class="post-title"><?php echo e(toHalfWidth($topic['ll_biaoti'])); ?></h3>
                                <?php if ($content): ?>
                                <p class="post-content"><?php echo e($content); ?></p>
                                <?php endif; ?>
                                
                                <?php 
                                // 解析附件URL (ll_url 为主，ll_furl 为辅)
                                $images = [];
                                $videos = [];
                                $audios = [];
                                
                                $furl = trim($topic['ll_url'] ?? '');
                                if (empty($furl)) {
                                    $furl = trim($topic['ll_furl'] ?? '');
                                }
                                
                                if (!empty($furl)) {
                                    // 格式1: |（格式：类型|路径|大小| (老格式如 7723_cn)
                                    // 格式2: |说明|URL|说明|URL| (多行)
                                    // 格式3: |URL,URL,URL| (逗号分隔)
                                    // 格式4: 纯URL
                                    
                                    // 先尝试老格式 (包含 "格式" 关键词)
                                    if (strpos($furl, '格式') !== false) {
                                        // 解码 Unicode 转义 (\uxxxx) 并解析
                                        $decodedFurl = preg_replace('/\\\\u([0-9a-fA-F]{4})/i', '&#x$1;', $furl);
                                        $decodedFurl = html_entity_decode($decodedFurl);
                                        // 匹配: |说明（格式：类型|路径| （使用非贪婪匹配 .+? 来匹配多个附件）
                                        preg_match_all('/\|.+?\（格式[：:]\s*(\w+)\|\s*([^|\n]+)\|/u', $decodedFurl, $matches, PREG_SET_ORDER);
                                        foreach ($matches as $m) {
                                            $type = strtolower(trim($m[1]));
                                            $path = trim($m[2]);
                                            // 判断类型
                                            if (in_array($type, ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'])) {
                                                $images[] = $path;
                                            } elseif (in_array($type, ['mp4', 'webm', 'avi', 'mov', 'mkv', 'flv', 'wmv'])) {
                                                $videos[] = $path;
                                            } elseif (in_array($type, ['mp3', 'wav', 'ogg', 'm4a', 'aac', 'flac'])) {
                                                $audios[] = $path;
                                            }
                                        }
                                    }
                                    
                                    // 尝试竖线分隔格式：|说明|URL|说明|URL| (无"格式"关键词)
                                    if (empty($images) && empty($videos) && empty($audios)) {
                                        // 解码 Unicode 转义
                                        $decodedFurl = preg_replace('/\\\\u([0-9a-fA-F]{4})/i', '&#x$1;', $furl);
                                        $decodedFurl = html_entity_decode($decodedFurl);
                                        
                                        // 匹配 |说明|URL| 格式（跳过空部分，取第2、4、6...个竖线分隔项）
                                        if (preg_match_all('/\|([^|]+)\|([^\s|]+)/', $decodedFurl, $pipeMatches, PREG_SET_ORDER)) {
                                            foreach ($pipeMatches as $m) {
                                                $label = trim($m[1]);
                                                $url = trim($m[2]);
                                                if (empty($url)) continue;
                                                
                                                // 判断类型（根据说明文字或URL扩展名）
                                                $ext = strtolower(pathinfo($url, PATHINFO_EXTENSION));
                                                if (in_array($ext, ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'])) {
                                                    $images[] = $url;
                                                } elseif (in_array($ext, ['mp4', 'webm', 'avi', 'mov', 'mkv', 'flv', 'wmv'])) {
                                                    $videos[] = $url;
                                                } elseif (in_array($ext, ['mp3', 'wav', 'ogg', 'm4a', 'aac', 'flac'])) {
                                                    $audios[] = $url;
                                                } elseif (in_array($ext, ['', 'jpg', 'jpeg', 'png', 'gif'])) {
                                                    // 扩展名为空或常见图片格式，默认当图片处理
                                                    $images[] = $url;
                                                }
                                            }
                                        }
                                    }
                                    
                                    // 如果竖线格式没匹配到，尝试普通URL格式
                                    if (empty($images) && empty($videos) && empty($audios)) {
                                        // 规范化换行符 \r\n -> \n, \r -> \n
                                        $furl = preg_replace('/\r\n?/', "\n", $furl);
                                        // 支持换行或逗号分隔
                                        if (strpos($furl, "\n") !== false) {
                                            $parts = explode("\n", $furl);
                                        } elseif (strpos($furl, ',') !== false) {
                                            $parts = explode(',', $furl);
                                        } else {
                                            $parts = [$furl];
                                        }
                                        
                                        foreach ($parts as $part) {
                                            $part = trim($part);
                                            if (empty($part)) continue;
                                            // 支持 http:// https:// 和相对路径 (uploads/...)
                                            if (preg_match('/(?:https?:\/\/)?[^\s|]+/', $part, $matches)) {
                                                $url = trim($matches[0]);
                                                if (empty($url)) continue;
                                                // 跳过纯说明文字
                                                if (strpos($url, '.') === false) continue;
                                                // 去掉重复的 uploads/ 前缀（数据库已包含完整相对路径）
                                                $url = preg_replace('#^uploads/#', '', $url);
                                                $ext = strtolower(pathinfo($url, PATHINFO_EXTENSION));
                                                if (in_array($ext, ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'])) {
                                                    $images[] = $url;
                                                } elseif (in_array($ext, ['mp4', 'webm', 'avi', 'mov', 'mkv', 'flv', 'wmv'])) {
                                                    $videos[] = $url;
                                                } elseif (in_array($ext, ['mp3', 'wav', 'ogg', 'm4a', 'aac', 'flac'])) {
                                                    $audios[] = $url;
                                                }
                                            }
                                        }
                                    }
                                }
                                
                                // 显示图片网格
                                if (!empty($images)):
                                    $imgCount = count($images);
                                    $colClass = $imgCount == 1 ? 'col-12' : ($imgCount == 2 ? 'col-6' : 'col-4');
                                ?>
                                <div class="post-images-grid row g-1">
                                    <?php foreach (array_slice($images, 0, 9) as $img): 
                                        $fullUrl = (strpos($img, 'http') === 0) ? $img : $uploadUrl . $img;
                                    ?>
                                    <div class="<?php echo $colClass; ?>">
                                        <img src="<?php echo e($fullUrl); ?>" alt="" class="post-image-thumb rounded" loading="lazy" decoding="async" style="width:100%;height:120px;object-fit:cover;cursor:pointer;" onclick="event.preventDefault();previewImage(this.src)" onerror="this.style.display='none';this.parentElement.innerHTML='<div style=&quot;width:100%;height:120px;background:#f0f0f0;display:flex;align-items:center;justify-content:center;border-radius:8px;&quot;><span style=&quot;font-size:32px;&quot;>🖼️</span></div>';">
                                    </div>
                                    <?php endforeach; ?>
                                </div>
                                <?php endif; ?>
                                
                                <?php 
                                // 显示视频播放器
                                if (!empty($videos)): ?>
                                <div class="post-media-player" onclick="event.preventDefault();">
                                    <?php foreach ($videos as $video): 
                                        $videoUrl = (strpos($video, 'http') === 0) ? $video : $uploadUrl . $video;
                                    ?>
                                    <div class="media-item">
                                        <video controls style="width:100%;max-height:250px;border-radius:8px;background:#000;">
                                            <source src="<?php echo e($videoUrl); ?>" type="video/mp4">
                                            您的浏览器不支持视频播放
                                        </video>
                                    </div>
                                    <?php endforeach; ?>
                                </div>
                                <?php endif; ?>
                                
                                <?php 
                                // 显示音频播放器
                                if (!empty($audios)): ?>
                                <div class="post-media-player" onclick="event.preventDefault();">
                                    <?php foreach ($audios as $audio): 
                                        $audioUrl = (strpos($audio, 'http') === 0) ? $audio : $uploadUrl . $audio;
                                    ?>
                                    <div class="media-item">
                                        <audio controls style="width:100%;">
                                            <source src="<?php echo e($audioUrl); ?>" type="audio/mpeg">
                                            您的浏览器不支持音频播放
                                        </audio>
                                    </div>
                                    <?php endforeach; ?>
                                </div>
                                <?php endif; ?>
                            </a>
                            
                            <!-- 帖子统计 -->
                            <div class="post-card-footer">
                                <span class="post-stat">
                                    💬 <?php echo $topic['ll_rchf']; ?> 回复
                                </span>
                                <span class="post-stat">
                                    <?php echo (int)($topic['ll_zan'] ?? 0) > 0 ? '💚' : '🤍'; ?> <?php echo (int)($topic['ll_zan'] ?? 0); ?> 点赞
                                </span>
                                <span class="post-stat">
                                    👀 <?php echo $topic['ll_rc']; ?> 浏览
                                </span>
                                <?php if ($topic['ll_time2'] && $topic['ll_time2'] !== $topic['ll_time1']): ?>
                                <span class="post-last-reply">
                                    最后回复: <?php echo formatTime($topic['ll_time2']); ?>
                                </span>
                                <?php endif; ?>
                            </div>
                        </div>
                        <?php endforeach; ?>
                        <?php endif; ?>
                    </div>
                    
                    <!-- 分页导航 -->
                    <?php
                    if ($totalPages > 1):
                        // 分页URL：filter嵌路径，第1页不带_N后缀
                        $pageUrl = function($p) use ($bankuaiId, $filter) {
                            $base = '/bbs/board/' . $bankuaiId;
                            if ($filter) $base .= '_' . urlencode($filter);
                            if ($p > 1) $base .= '_' . $p;
                            // 带上当前语言前缀，避免翻页后跳回中文版
                            return $base . '/';
                        };
                    ?>
                    <nav class="pagination" aria-label="分页导航">
                        <ul class="pagination-list">
                            <?php if ($page > 1): ?>
                            <li><a href="<?php echo $pageUrl($page - 1); ?>" class="page-btn page-prev" rel="prev">‹ 上一页</a></li>
                            <?php endif; ?>
                            
                            <?php
                            // 智能分页：始终显示第一页、最后一页、当前页±2
                            $pagesToShow = [];
                            $pagesToShow[] = 1;
                            for ($i = max(2, $page - 2); $i <= min($totalPages - 1, $page + 2); $i++) {
                                $pagesToShow[] = $i;
                            }
                            if ($totalPages > 1) $pagesToShow[] = $totalPages;
                            $pagesToShow = array_unique($pagesToShow);
                            sort($pagesToShow);
                            $lastShown = 0;
                            foreach ($pagesToShow as $p):
                                if ($p > $lastShown + 1):
                            ?>
                            <li><span class="page-ellipsis">…</span></li>
                            <?php endif; ?>
                            <?php if ($p == $page): ?>
                            <li><span class="page-num active" aria-current="page"><?php echo $p; ?></span></li>
                            <?php else: ?>
                            <li><a href="<?php echo $pageUrl($p); ?>" class="page-num"><?php echo $p; ?></a></li>
                            <?php endif;
                                $lastShown = $p;
                            endforeach; ?>
                            
                            <?php if ($page < $totalPages): ?>
                            <li><a href="<?php echo $pageUrl($page + 1); ?>" class="page-btn page-next" rel="next">下一页 ›</a></li>
                            <?php endif; ?>
                        </ul>
                        <div class="pagination-info"><?php echo str_replace(array('{a}','{b}'), array($total, $totalPages), '共 {a} 条帖子，{b} 页'); ?></div>
                    </nav>
                    <?php endif; ?>
                </div>

                <!-- 侧边栏 -->
                <div class="sidebar">
                    <?php if ($bankuai): ?>
                    <div class="panel">
                        <div class="panel-header">
                            <span class="panel-icon">📋</span> 版务信息
                        </div>
                        <div class="panel-body">
                            <div class="forum-header-card-compact">
                                <div class="forum-header-main">
                                    <?php if (!empty($bankuai['ll_logo'])): ?>
                                    <img src="<?php echo e($pageImage); ?>" alt="" class="forum-logo" width="56" height="56" loading="lazy" decoding="async">
                                    <?php endif; ?>
                                    <div class="forum-header-info">
                                        <h1 class="forum-title"><?php echo e(toHalfWidth($bankuai['ll_title'])); ?></h1>
                                        <?php if (!empty($bankuai['ll_titleb'])): ?>
                                        <p class="forum-subtitle"><?php echo e(toHalfWidth($bankuai['ll_titleb'])); ?></p>
                                        <?php endif; ?>
                                    </div>
                                </div>
                                <div class="forum-header-stats">
                                    <span class="stat-item">📝 帖子 <?php echo $topicCount ?? 0; ?></span>
                                    <span class="stat-item">📅 今日 <?php echo $todayCount ?? 0; ?></span>
                                </div>
                                <?php if (!empty($bankuai['ll_wel'])): ?>
                                <div class="forum-welcome">
                                    <i class="icon-welcome"></i> <?php echo e($bankuai['ll_wel']); ?>
                                </div>
                                <?php endif; ?>
                                <?php if (!empty($bankuai['ll_text'])): ?>
                                <div class="forum-rules">
                                    <i class="icon-rules"></i> <strong>版规：</strong><?php echo e($bankuai['ll_text']); ?>
                                </div>
                                <?php endif; ?>
                                <?php if (!empty($banzhuList)): ?>
                                <div class="forum-banzhu">
                                    <span class="banzhu-label">👑 版主：</span>
                                    <div class="banzhu-list">
                                        <?php foreach ($banzhuList as $bz): ?>
                                        <a href="/bbs/user.php?id=<?php echo $bz['ll_useid']; ?>" class="banzhu-item">
                                            <img src="<?php echo e($bz['ll_img'] ?: '/images/logo.png'); ?>" alt="" class="banzhu-avatar" width="24" height="24" loading="lazy" decoding="async" onerror="this.onerror=null;this.src='/images/logo.png';">
                                            <span class="banzhu-name"><?php echo e($bz['ll_n_name'] ?: $bz['ll_name'] ?: '版主'); ?></span>
                                        </a>
                                        <?php endforeach; ?>
                                    </div>
                                </div>
                                <?php endif; ?>
                                
                                <!-- 关注按钮 -->
                                <div class="forum-follow">
                                    <?php if (isLoggedIn()): ?>
                                    <button id="followBtn" class="btn <?php echo $isFollowing ? 'btn-warning' : 'btn-primary'; ?>" data-following="<?php echo $isFollowing ? '1' : '0'; ?>">
                                        <i class="<?php echo $isFollowing ? 'bi bi-heart-fill' : 'bi bi-heart'; ?>"></i>
                                        <span id="followText"><?php echo $isFollowing ? '取消关注' : '关注板块'; ?></span>
                                    </button>
                                    <?php else: ?>
                                    <a href="/bbs/login.php" class="btn btn-primary">
                                        <i class="bi bi-heart"></i> 登录后关注
                                    </a>
                                    <?php endif; ?>
                                </div>
                            </div>
                        </div>
                    </div>
                    <?php endif; ?>
                    
                    <div class="panel">
                        <div class="panel-header">📂 版块分类</div>
                        <div class="panel-body">
                            <ul class="bankuai-list">
                                <li <?php echo !$bankuaiId ? 'class="active"' : ''; ?>>
                                    <a href="/bbs/list.php">全部帖子</a>
                                </li>
                                <?php foreach ($bankuais as $bk): ?>
                                <li <?php echo $bankuaiId == $bk['id'] ? 'class="active"' : ''; ?>>
                                    <a href="/bbs/board/<?php echo $bk['id']; ?>/"><?php echo e(toHalfWidth($bk['ll_title'])); ?></a>
                                </li>
                                <?php endforeach; ?>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <footer class="footer">
        <div class="container">
            <p>&copy; 2009 <a href="/" title="7坛游戏社区" class="footer-brand">7坛游戏社区</a> All Rights Reserved</p>
            <?php include __DIR__ . '/_footer_seo.php'; ?>
        </div>
    </footer>

    <!-- 引入 Bootstrap Icons -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css?v=20260906">
    
    <link rel="stylesheet" href="/bbs/css/list.css?v=20260906">

    
    <script src="/bbs/js/list.js"></script>
    <script>
    // 关注按钮事件
    if (document.getElementById('followBtn')) {
        document.getElementById('followBtn').addEventListener('click', function() {
            toggleFollow(<?php echo $bankuaiId; ?>);
        });
    }
    </script>
    
    <!-- 返回顶部 -->
    <button class="back-to-top" id="backToTop" title="返回顶部">↑</button>

    <script src="/bbs/js/common.js"></script>
<?php $mobileNavActive = 'list'; include __DIR__ . '/mobile_nav.php'; ?>
</body>
</html>