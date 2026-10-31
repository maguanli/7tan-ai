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

// 获取用户最新帖子
$stmt = $pdo->prepare("SELECT id, ll_biaoti, ll_time2 FROM ll_lt WHERE ll_useid = ? AND ll_or = 0 ORDER BY id DESC LIMIT 5");
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
$nickname = $profileUser['ll_n_name'] ?: $profileUser['ll_name'];
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo e($nickname); ?> - <?php echo e('7坛游戏社区'); ?></title>
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
            <h5><?php echo e('📝 最新帖子'); ?></h5>
            <?php foreach ($recentTopics as $topic): ?>
            <div class="topic-item">
                <a href="<?php echo htmlspecialchars(bbsUrl('topic', $topic['id']), ENT_QUOTES); ?>"><?php echo e($topic['ll_biaoti']); ?></a>
                <div style="font-size: 12px; color: #999; margin-top: 5px;"><?php echo formatTime($topic['ll_time2']); ?></div>
            </div>
            <?php endforeach; ?>
        </div>
        <?php endif; ?>
        
        <div class="content-card">
            <h5><?php echo e('📅 注册信息'); ?></h5>
            <p style="color: #666;"><?php echo e('注册时间：'); ?><?php echo e($profileUser['ll_firsttime'] ?: '未知'); ?></p>
        </div>
    </div>
</body>
</html>
