<?php
/**
 * 7坛社区
 * 深圳市柒贰叁叁网络科技有限公司版权所有
 *
 */
require_once __DIR__ . '/config.php';

$pdo = getDB();
$userId = isset($_GET['id']) ? intval($_GET['id']) : 0;

if ($userId <= 0) {
    // 该入口（缺 id 参数）永远不会产出内容 -> 410 Gone
    // 20261006：原为 404；410 明确告知搜索引擎“永久移除”，停止反复重抓，节省抓取预算。
    http_response_code(410);
    require __DIR__ . '/../404.php';
    exit;
}

// 获取用户信息
$stmt = $pdo->prepare("SELECT * FROM ll_useregs WHERE id = ?");
$stmt->execute([$userId]);
$profileUser = $stmt->fetch();

if (!$profileUser) {
    // 用户不存在 → 404（原为 header('Location: index.php')，相对跳转会 302 到不存在的 /bbs/user/N/index.php）
    http_response_code(404);
    require __DIR__ . '/../404.php';
    exit;
}

// 获取用户发帖数
$stmt = $pdo->prepare("SELECT COUNT(*) FROM ll_lt WHERE ll_useid = ? AND ll_or = 0");
$stmt->execute([$userId]);
$topicCount = $stmt->fetchColumn();

// 获取用户回复数
$stmt = $pdo->prepare("SELECT COUNT(*) FROM ll_lthf WHERE ll_useid = ?");
$stmt->execute([$userId]);
$replyCount = $stmt->fetchColumn();

// 获取用户好友数
$stmt = $pdo->prepare("SELECT COUNT(*) FROM ll_friend WHERE (ll_myid = ? OR ll_yourid = ?) AND ll_or = 1");
$stmt->execute([$userId, $userId]);
$friendCount = $stmt->fetchColumn();

// 获取用户粉丝数
$stmt = $pdo->prepare("SELECT COUNT(*) FROM ll_friend WHERE ll_yourid = ? AND ll_or = 1");
$stmt->execute([$userId]);
$fansCount = $stmt->fetchColumn();

// 获取用户关注数
$stmt = $pdo->prepare("SELECT COUNT(*) FROM ll_friend WHERE ll_myid = ? AND ll_or = 1");
$stmt->execute([$userId]);
$followCount = $stmt->fetchColumn();

// ── 帖子列表分页 ──
// 20261030: 原来写死 LIMIT 5，一个人发了几百篇，主页永远只露最后 5 篇。
// 改为每页 20（和板块列表 list.php 的 $pageSize 一致）。
// 20261030 v2：分页改伪静态 /bbs/user/{id}_{N}/，与板块页 /bbs/board/18_2/ 同风格。
// 旧的 ?page=N 一律 301 过去，同一页不留两个 URL。
$pageSize = 20;

$hasStatic  = isset($GLOBALS['USER_PAGE_STATIC']);
$staticPage = $hasStatic ? (int)$GLOBALS['USER_PAGE_STATIC'] : 0;
$staticRaw  = $hasStatic ? (string)(isset($GLOBALS['USER_PAGE_RAW']) ? $GLOBALS['USER_PAGE_RAW'] : $staticPage) : '';
$pageParam  = isset($_GET['page']) ? trim((string)$_GET['page']) : null;

if ($hasStatic) {
    // 走 /bbs/user/1_2/ 这条路由，不再二次跳转
    $page = $staticPage;
    if ($page <= 1) {
        header('Location: /bbs/user/' . $userId . '/', true, 301);
        exit;
    }
    if ($staticRaw !== (string)$page) {
        // 1_02 / 1_002 这类前导零写法，301 到规范地址
        header('Location: /bbs/user/' . $userId . '_' . $page . '/', true, 301);
        exit;
    }
} else {
    $page = ($pageParam !== null && ctype_digit($pageParam)) ? (int)$pageParam : 0;
    if ($pageParam !== null) {
        if ($page <= 1) {
            header('Location: /bbs/user/' . $userId . '/', true, 301);
            exit;
        }
        header('Location: /bbs/user/' . $userId . '_' . $page . '/', true, 301);
        exit;
    }
    $page = 1;
}

$topicTotal = (int)$topicCount;
$totalPages = max(1, (int)ceil($topicTotal / $pageSize));

// 越界页 301 回第 1 页（list.php 同款：越界页曾返回 200 空列表，属软 404）
if ($page > $totalPages) {
    header('Location: /bbs/user/' . $userId . '/', true, 301);
    exit;
}

$offset = ($page - 1) * $pageSize;
$stmt = $pdo->prepare("SELECT t.id, t.ll_biaoti, t.ll_time2, t.ll_rc, t.ll_idd, c.ll_title AS board_title
                         FROM ll_lt t LEFT JOIN ll_class c ON t.ll_idd = c.id
                        WHERE t.ll_useid = ? AND t.ll_or = 0
                        ORDER BY t.id DESC LIMIT " . $pageSize . " OFFSET " . $offset);
$stmt->execute([$userId]);
$recentTopics = $stmt->fetchAll();

// 等级名称
$levelZh = ['游客', '新手玩家', '初级玩家', '中级玩家', '高级玩家', '资深玩家', '专家玩家', '大师玩家'];
$level = intval($profileUser['ll_dj'] ?? 0);
$level = max(0, min($level, 7));
$levelName = $levelZh[$level];

// 检查当前用户是否已登录
$currentUserId = getCurrentUserId();
$isOwnProfile = ($currentUserId == $userId);

// 检查是否已关注
$isFollowing = false;
if (!$isOwnProfile && $currentUserId > 0) {
    $stmt = $pdo->prepare("SELECT id FROM ll_friend WHERE ll_myid = ? AND ll_yourid = ?");
    $stmt->execute([$currentUserId, $userId]);
    $isFollowing = $stmt->fetch() !== false;
}

// ── canonical 自引用 ──
$canonicalPath = '/bbs/user/' . $userId . '/';
if ($page > 1) $canonicalPath = '/bbs/user/' . $userId . '_' . $page . '/';   // 分页页自引用，用伪静态地址
$nickname = $profileUser['ll_n_name'] ?: $profileUser['ll_name'];
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo e($nickname); ?><?php if ($page > 1) echo e(' 第' . $page . '页'); ?> - <?php echo e('7坛游戏社区'); ?></title>
    <meta name="description" content="<?php echo e($nickname); ?> — <?php echo e('7坛游戏社区'); ?>">
    <link rel="canonical" href="<?php echo htmlspecialchars($canonicalPath, ENT_QUOTES); ?>">
    <link rel="stylesheet" href="https://cdn.bootcdn.net/ajax/libs/bootstrap/5.3.0/css/bootstrap.min.css?v=20260906">
    <style>
        body { background: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        .profile-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 20px; text-align: center; }
        .profile-avatar { width: 120px; height: 120px; border-radius: 50%; border: 5px solid white; object-fit: cover; }
        .profile-name { font-size: 24px; font-weight: bold; margin-top: 15px; }
        .profile-sign { font-size: 14px; opacity: 0.9; margin-top: 5px; }
        .profile-level { display: inline-block; background: rgba(255,255,255,0.2); padding: 4px 12px; border-radius: 20px; font-size: 12px; margin-top: 10px; }
        .stats-row { display: flex; justify-content: center; gap: 40px; margin-top: 25px; }
        .stat-item { text-align: center; }
        .stat-num { font-size: 24px; font-weight: bold; }
        .stat-label { font-size: 12px; opacity: 0.8; }
        .content-card { background: white; border-radius: 12px; padding: 20px; margin-top: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .content-card h5 { color: #333; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #667eea; }
        .topic-item { padding: 12px 0; border-bottom: 1px solid #eee; }
        .topic-item:last-child { border-bottom: none; }
        .topic-item a { color: #333; text-decoration: none; }
        .topic-item a:hover { color: #667eea; }
        .count-badge { display: inline-block; font-size: 12px; font-weight: 400; color: #667eea; background: #eef0fd; border-radius: 10px; padding: 2px 9px; margin-left: 8px; vertical-align: middle; }
        .topic-meta { font-size: 12px; color: #999; margin-top: 6px; display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
        .topic-meta .board-tag { color: #667eea; text-decoration: none; background: #f0f2ff; border-radius: 4px; padding: 1px 7px; }
        .topic-meta .board-tag:hover { background: #e3e7ff; }
        .pager { display: flex; gap: 6px; flex-wrap: wrap; justify-content: center; align-items: center; margin-top: 18px; padding-top: 16px; border-top: 1px solid #eee; }
        .pager .pg { display: inline-block; min-width: 34px; text-align: center; padding: 6px 10px; border: 1px solid #e2e2e2; border-radius: 6px; color: #555; text-decoration: none; font-size: 13px; background: #fff; }
        .pager .pg:hover { border-color: #667eea; color: #667eea; }
        .pager .pg.on { background: #667eea; border-color: #667eea; color: #fff; font-weight: 600; }
        .pager .pg-dot { color: #bbb; padding: 0 2px; font-size: 13px; }
        .back-btn { position: absolute; top: 20px; left: 20px; color: white; text-decoration: none; }
        .container { position: relative; }
    </style>
<script>
var _hmt = _hmt || [];
(function() {
  var hm = document.createElement("script");
  hm.src = "https://hm.baidu.com/hm.js?f5f121dbbaa5fca7a5d5fba84a19576c";
  var s = document.getElementsByTagName("script")[0]; 
  s.parentNode.insertBefore(hm, s);
})();
</script></head>
<body>
    <div class="profile-header">
        <div class="container">
            <a href="javascript:history.back()" class="back-btn"><?php echo e('← 返回'); ?></a>
            <img src="<?php echo e($profileUser['ll_img'] ?: '/images/logo.png'); ?>" class="profile-avatar" onerror="this.onerror=null;this.src='/images/logo.png';">
            <div class="profile-name"><?php echo e($nickname); ?></div>
            <div class="profile-sign"><?php echo e($profileUser['ll_sign'] ?: '这个人很懒，什么都没写'); ?></div>
            <?php if (!empty($profileUser['ll_age']) && $profileUser['ll_age'] > 0): ?>
            <div style="font-size: 13px; opacity: 0.8; margin-top: 6px;">🎂 <?php echo $profileUser['ll_age']; ?><?php echo e('岁'); ?>
                <?php if (!empty($profileUser['ll_sex'])): ?>
                    · <?php echo $profileUser['ll_sex'] == '男' ? '♂' : ($profileUser['ll_sex'] == '女' ? '♀' : ''); ?><?php echo $profileUser['ll_sex'] == '男' ? e('男') : ($profileUser['ll_sex'] == '女' ? e('女') : e($profileUser['ll_sex'])); ?>
                <?php endif; ?>
            </div>
            <?php endif; ?>
            <div class="profile-level">Lv.<?php echo $level; ?> <?php echo e($levelName); ?></div>
            <?php if (!$isOwnProfile && $currentUserId > 0): ?>
            <div style="margin-top: 15px;">
                <a href="message.php?to=<?php echo $userId; ?>" class="btn btn-light btn-sm" style="background: rgba(255,255,255,0.9); color: #667eea; border: none; margin-right: 10px;">
                    <?php echo e('✉️ 发私信'); ?>
                </a>
                <?php if ($isFollowing): ?>
                <span style="color: rgba(255,255,255,0.7);"><?php echo e('✓ 已关注'); ?></span>
                <?php else: ?>
                <a href="user.php?tab=follow&id=<?php echo $userId; ?>" class="btn btn-light btn-sm" style="background: rgba(255,255,255,0.2); color: white; border: 1px solid rgba(255,255,255,0.5);">
                    <?php echo e('+ 关注'); ?>
                </a>
                <?php endif; ?>
            </div>
            <?php elseif ($isOwnProfile): ?>
            <div style="margin-top: 15px;">
                <a href="user.php" class="btn btn-light btn-sm" style="background: rgba(255,255,255,0.9); color: #667eea; border: none;">
                    <?php echo e('编辑个人资料'); ?>
                </a>
            </div>
            <?php endif; ?>
            <div class="stats-row">
                <div class="stat-item">
                    <div class="stat-num"><?php echo $topicCount; ?></div>
                    <div class="stat-label"><?php echo e('帖子'); ?></div>
                </div>
                <div class="stat-item">
                    <div class="stat-num"><?php echo $replyCount; ?></div>
                    <div class="stat-label"><?php echo e('回复'); ?></div>
                </div>
                <div class="stat-item">
                    <div class="stat-num"><?php echo $friendCount; ?></div>
                    <div class="stat-label"><?php echo e('好友'); ?></div>
                </div>
                <div class="stat-item">
                    <div class="stat-num"><?php echo $fansCount; ?></div>
                    <div class="stat-label"><?php echo e('粉丝'); ?></div>
                </div>
                <div class="stat-item">
                    <div class="stat-num"><?php echo $followCount; ?></div>
                    <div class="stat-label"><?php echo e('关注'); ?></div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="container" style="max-width: 800px; padding: 20px;">
        <?php if (!empty($recentTopics)): ?>
        <div class="content-card">
            <h5><?php echo e('📝 帖子'); ?><span class="count-badge"><?php echo e('共 ' . $topicTotal . ' 篇'); ?></span><?php if ($totalPages > 1): ?><span class="count-badge"><?php echo e('第 ' . $page . ' / ' . $totalPages . ' 页'); ?></span><?php endif; ?></h5>
            <?php foreach ($recentTopics as $topic): ?>
            <div class="topic-item">
                <a href="<?php echo htmlspecialchars(bbsUrl('topic', $topic['id']), ENT_QUOTES); ?>"><?php echo e($topic['ll_biaoti']); ?></a>
                <div class="topic-meta">
                    <?php if (!empty($topic['board_title'])): ?>
                    <a class="board-tag" href="<?php echo htmlspecialchars(bbsUrl('board', $topic['ll_idd']), ENT_QUOTES); ?>"><?php echo e($topic['board_title']); ?></a>
                    <?php endif; ?>
                    <span><?php echo formatTime($topic['ll_time2']); ?></span>
                    <span><?php echo (int)($topic['ll_rc'] ?? 0); ?><?php echo e(' 次浏览'); ?></span>
                </div>
            </div>
            <?php endforeach; ?>
            <?php if ($totalPages > 1): ?>
            <nav class="pager" aria-label="<?php echo e('帖子分页'); ?>">
                <?php
                $baseUrl   = '/bbs/user/' . $userId;   // 不带尾斜杠：第 1 页补 /，第 N 页补 _N/
                $pgUrl     = function ($p) use ($baseUrl) {
                    return $p <= 1 ? $baseUrl . '/' : $baseUrl . '_' . $p . '/';
                };
                $winStart  = max(1, $page - 2);
                $winEnd    = min($totalPages, $page + 2);
                ?>
                <?php if ($page > 1): ?>
                <a class="pg" href="<?php echo $pgUrl($page - 1); ?>"><?php echo e('← 上一页'); ?></a>
                <?php endif; ?>
                <?php if ($winStart > 1): ?>
                <a class="pg" href="<?php echo $pgUrl(1); ?>">1</a>
                <?php if ($winStart > 2): ?><span class="pg-dot">…</span><?php endif; ?>
                <?php endif; ?>
                <?php for ($p = $winStart; $p <= $winEnd; $p++): ?>
                    <?php if ($p === $page): ?>
                <span class="pg on"><?php echo $p; ?></span>
                    <?php else: ?>
                <a class="pg" href="<?php echo $pgUrl($p); ?>"><?php echo $p; ?></a>
                    <?php endif; ?>
                <?php endfor; ?>
                <?php if ($winEnd < $totalPages): ?>
                <?php if ($winEnd < $totalPages - 1): ?><span class="pg-dot">…</span><?php endif; ?>
                <a class="pg" href="<?php echo $pgUrl($totalPages); ?>"><?php echo $totalPages; ?></a>
                <?php endif; ?>
                <?php if ($page < $totalPages): ?>
                <a class="pg" href="<?php echo $pgUrl($page + 1); ?>"><?php echo e('下一页 →'); ?></a>
                <?php endif; ?>
            </nav>
            <?php endif; ?>
        </div>
        <?php else: ?>
        <div class="content-card">
            <h5><?php echo e('📝 帖子'); ?></h5>
            <p style="color: #888; font-size: 14px; margin: 0;"><?php echo e('这个账号还没有发过帖子'); ?></p>
        </div>
        <?php endif; ?>
        
        <div class="content-card">
            <h5><?php echo e('📅 注册信息'); ?></h5>
            <p style="color: #666;"><?php echo e('注册时间：'); ?><?php echo e($profileUser['ll_firsttime'] ?: '未知'); ?></p>
        </div>
    </div>
</body>
</html>
