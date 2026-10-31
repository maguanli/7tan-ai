<?php
/**
 * 7坛社区
 * 深圳市柒贰叁叁网络科技有限公司版权所有
 */
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/ai_helper.php';
require_once __DIR__ . '/ubb_plus.php';

header('Content-Type: application/json; charset=utf-8');

$pdo = getDB();

// 获取参数
$topicId = isset($_POST['topic_id']) ? intval($_POST['topic_id']) : 0;
$page = isset($_POST['page']) ? max(1, intval($_POST['page'])) : 1;
$sort = isset($_POST['sort']) && $_POST['sort'] === 'desc' ? 'DESC' : 'ASC';
$pageSize = 20;

if ($topicId <= 0) {
    echo json_encode(['code' => 400, 'msg' => '参数错误']);
    exit;
}

// 获取一级回复总数（用于计算楼层号）
$stmt = $pdo->prepare("SELECT COUNT(*) FROM ll_lthf WHERE ll_id = ? AND (ll_father_id = 0 OR ll_father_id IS NULL)");
$stmt->execute([$topicId]);
$totalReplies = $stmt->fetchColumn();
$totalPages = max(1, ceil($totalReplies / $pageSize));

if ($page > $totalPages) {
    echo json_encode(['code' => 200, 'data' => [], 'msg' => '没有更多回复']);
    exit;
}

$offset = ($page - 1) * $pageSize;

// 获取当前用户
$currentUserId = getCurrentUserId();

// 查询一级回复（PDO不支持 LIMIT/OFFSET 参数绑定，需直接拼接）
$stmt = $pdo->prepare("
    SELECT h.*, u.ll_n_name, u.ll_img, u.ll_dj
    FROM ll_lthf h
    LEFT JOIN ll_useregs u ON h.ll_useid = u.id
    WHERE h.ll_id = ? AND (h.ll_father_id = 0 OR h.ll_father_id IS NULL)
    ORDER BY h.id {$sort}
    LIMIT {$pageSize} OFFSET {$offset}
");
$stmt->execute([$topicId]);
$replies = $stmt->fetchAll();

// 一次性查询所有子回复（优化N+1问题）
$parentIds = array_column($replies, 'id');
$childrenMap = [];
if (!empty($parentIds)) {
    $placeholders = implode(',', array_fill(0, count($parentIds), '?'));
    $stmt = $pdo->prepare("
        SELECT h.*, u.ll_n_name, u.ll_img, u.ll_dj
        FROM ll_lthf h
        LEFT JOIN ll_useregs u ON h.ll_useid = u.id
        WHERE h.ll_father_id IN ({$placeholders})
        ORDER BY h.id ASC
    ");
    $stmt->execute($parentIds);
    $allChildren = $stmt->fetchAll();
    
    // 按父ID分组
    foreach ($allChildren as $child) {
        $childrenMap[$child['ll_father_id']][] = $child;
    }
}

// 获取用户已点赞的回复ID列表（包括子回复）
$zanedReplyIds = [];
$allReplyIds = array_merge($parentIds, array_keys($childrenMap) > 0 ? array_reduce($childrenMap, 'array_merge', []) : []);
foreach ($childrenMap as $children) {
    foreach ($children as $c) {
        $allReplyIds[] = $c['id'];
    }
}
if ($currentUserId > 0 && !empty($allReplyIds)) {
    $placeholders = implode(',', array_fill(0, count($allReplyIds), '?'));
    $stmt = $pdo->prepare("SELECT ll_targetid FROM ll_zan WHERE ll_type = 'reply' AND ll_targetid IN ({$placeholders}) AND ll_useid = ?");
    $stmt->execute(array_merge($allReplyIds, [$currentUserId]));
    foreach ($stmt->fetchAll() as $row) {
        $zanedReplyIds[$row['ll_targetid']] = true;
    }
}

// 处理回复数据
$result = [];

foreach ($replies as $index => $reply) {
    $isAi = isset($reply['ll_ai']) && $reply['ll_ai'] == 1;
    $isAi1 = $reply['ll_useid'] == AI_USER_ID;
    $isAi2 = $reply['ll_useid'] == AI2_USER_ID;
    
    // 计算楼层号
    if ($sort === 'ASC') {
        // 正序：第1页第1个=2楼
        $floorNum = ($page - 1) * $pageSize + $index + 2;
    } else {
        // 倒序：第1页第1个=总楼层
        $floorNum = $totalReplies - ($page - 1) * $pageSize - $index;
    }
    
    // 头像（统一从数据库读取，AI用户也可自定义头像）
    $avatar = $reply['ll_img'] ?: '/images/logo.png';

    // 用户名
    $username = $reply['ll_n_name'] ?: $reply['ll_name'];
    
    // 处理图片路径
    $replyImg = '';
    if (!empty($reply['ll_furl'])) {
        $replyImg = trim($reply['ll_furl']);
        if (strpos($replyImg, 'http') !== 0 && strpos($replyImg, '/bbs/') !== 0) {
            $replyImg = '/bbs/' . ltrim($replyImg, '/');
        }
    }

    // 回复数据
    $result[] = [
        'id' => $reply['id'],
        'type' => 'parent', // 一级回复
        'username' => htmlspecialchars($username),
        'avatar' => $avatar,
        'floor_num' => $floorNum,
        'floor_display' => $floorNum . '楼',
        'content' => safe_output(ubb_plus(bbs_ubb($reply['ll_text']))),
        'image' => $replyImg,
        'time' => $reply['ll_time'],
        'is_ai' => $isAi,
        'can_reply' => ($currentUserId > 0 && $reply['ll_useid'] != $currentUserId),
        'zaned' => isset($zanedReplyIds[$reply['id']]),
        'zan_count' => (int)($reply['ll_zan'] ?? 0),
        'children' => [] // 子回复数组
    ];
    
    // 添加子回复
    $children = $childrenMap[$reply['id']] ?? [];
    foreach ($children as $childIndex => $child) {
        $childIsAi = !empty($child['ll_ai']);
        $childIsAi1 = $child['ll_useid'] == AI_USER_ID;
        $childIsAi2 = $child['ll_useid'] == AI2_USER_ID;

        // 子回复头像（统一从数据库读取）
        $childAvatar = $child['ll_img'] ?: '/images/logo.png';

        // 子回复用户名
        $childUsername = $child['ll_n_name'] ?: $child['ll_name'];
        
        // 子回复图片路径
        $childImg = '';
        if (!empty($child['ll_furl'])) {
            $childImg = trim($child['ll_furl']);
            if (strpos($childImg, 'http') !== 0 && strpos($childImg, '/bbs/') !== 0) {
                $childImg = '/bbs/' . ltrim($childImg, '/');
            }
        }

        $result[] = [
            'id' => $child['id'],
            'type' => 'child', // 二级回复
            'parent_id' => $reply['id'],
            'username' => htmlspecialchars($childUsername),
            'avatar' => $childAvatar,
            'floor_num' => $floorNum,
            'floor_display' => $floorNum . '-' . ($childIndex + 1) . '楼',
            'content' => safe_output(ubb_plus(bbs_ubb($child['ll_text']))),
            'image' => $childImg,
            'time' => $child['ll_time'],
            'is_ai' => $childIsAi,
            'can_reply' => ($currentUserId > 0 && $child['ll_useid'] != $currentUserId),
            'zaned' => isset($zanedReplyIds[$child['id']]),
            'zan_count' => (int)($child['ll_zan'] ?? 0),
            'children' => null // 子回复没有子回复
        ];
    }
}

echo json_encode([
    'code' => 200, 
    'data' => $result,
    'page' => $page,
    'totalPages' => $totalPages,
    'totalReplies' => $totalReplies
]);
