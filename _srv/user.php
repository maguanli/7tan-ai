<?php
/**
 * 7坛社区
 * 深圳市柒贰叁叁网络科技有限公司版权所有
 */
require_once __DIR__ . '/config.php';

// ========== AJAX 接口：加载更多帖子（支持sort参数） ==========
if (isset($_GET['ajax']) && $_GET['ajax'] === 'topics' && isset($_GET['page'])) {
    header('Content-Type: application/json; charset=utf-8');
    if (!isLoggedIn()) {
        echo json_encode(['code' => 401, 'msg' => '请先登录']);
        exit;
    }
    $pdo = getDB();
    $userId = getCurrentUserId();
    $page = max(1, intval($_GET['page']));
    $pageSize = 10;
    $offset = ($page - 1) * $pageSize;
    $sortType = $_GET['sort'] ?? 'latest';

    // 根据排序类型选择查询
    if ($sortType === 'hot') {
        $stmt = $pdo->prepare("
            SELECT id, ll_biaoti, ll_rc, ll_rchf, ll_time1 
            FROM ll_lt 
            WHERE ll_useid = ? AND ll_or = 0 
            ORDER BY (COALESCE(ll_rchf, 0) + COALESCE(ll_rc, 0)) DESC, id DESC
            LIMIT ? OFFSET ?
        ");
    } else {
        $stmt = $pdo->prepare("SELECT id, ll_biaoti, ll_rc, ll_rchf, ll_time1 FROM ll_lt WHERE ll_useid = ? AND ll_or = 0 ORDER BY id DESC LIMIT ? OFFSET ?");
    }
    $stmt->execute([$userId, $pageSize, $offset]);
    $topics = $stmt->fetchAll();

    // 批量获取回复数
    if (!empty($topics)) {
        $ids = array_column($topics, 'id');
        $placeholders = implode(',', array_fill(0, count($ids), '?'));
        $stmt = $pdo->prepare("SELECT ll_id, COUNT(*) as cnt FROM ll_lthf WHERE ll_id IN ($placeholders) GROUP BY ll_id");
        $stmt->execute($ids);
        $replyCounts = array_column($stmt->fetchAll(), 'cnt', 'll_id');
        foreach ($topics as &$t) {
            $t['reply_count'] = $replyCounts[$t['id']] ?? 0;
        }
    }

    foreach ($topics as &$__t) { $__t['ll_biaoti'] = $__t['ll_biaoti']; }
    unset($__t);
    echo json_encode(['code' => 200, 'data' => $topics, 'hasMore' => count($topics) === $pageSize]);
    exit;
}

// ========== AJAX 接口：加载更多回复（支持sort参数） ==========
if (isset($_GET['ajax']) && $_GET['ajax'] === 'replies' && isset($_GET['page'])) {
    header('Content-Type: application/json; charset=utf-8');
    if (!isLoggedIn()) {
        echo json_encode(['code' => 401, 'msg' => '请先登录']);
        exit;
    }
    $pdo = getDB();
    $userId = getCurrentUserId();
    $page = max(1, intval($_GET['page']));
    $pageSize = 10;
    $offset = ($page - 1) * $pageSize;
    $sortType = $_GET['sort'] ?? 'latest';

    if ($sortType === 'hot') {
        $stmt = $pdo->prepare("
            SELECT h.id, h.ll_id as topic_id, h.ll_text, h.ll_time, h.ll_zan,
                   t.ll_biaoti as topic_title
            FROM ll_lthf h
            LEFT JOIN ll_lt t ON h.ll_id = t.id
            WHERE h.ll_useid = ?
            ORDER BY h.ll_zan DESC, h.id DESC
            LIMIT ? OFFSET ?
        ");
    } else {
        $stmt = $pdo->prepare("
            SELECT h.id, h.ll_id as topic_id, h.ll_text, h.ll_time, h.ll_zan,
                   t.ll_biaoti as topic_title
            FROM ll_lthf h
            LEFT JOIN ll_lt t ON h.ll_id = t.id
            WHERE h.ll_useid = ?
            ORDER BY h.id DESC LIMIT ? OFFSET ?
        ");
    }
    $stmt->execute([$userId, $pageSize, $offset]);
    $myReplies = $stmt->fetchAll();

    foreach ($myReplies as &$__r) { $__r['topic_title'] = $__r['topic_title']; $__r['ll_text'] = $__r['ll_text']; }
    unset($__r);
    echo json_encode(['code' => 200, 'data' => $myReplies, 'hasMore' => count($myReplies) === $pageSize]);
    exit;
}

// 检查登录
if (!isLoggedIn()) {
    header('Location: ' . '/bbs/login.php');
    exit;
}

$pdo = getDB();
$userId = getCurrentUserId();
$tab = $_GET['tab'] ?? 'profile';

// ========== 获取统计数据 ==========
$stats = [];

// 获取用户信息
$stmt = $pdo->prepare("SELECT * FROM ll_useregs WHERE id = ?");
$stmt->execute([$userId]);
$user = $stmt->fetch();

if (!$user) {
    header('Location: ' . '/bbs/login.php');
    exit;
}

// 获取签到信息
$today = date('Y-m-d');
$stmt = $pdo->prepare("SELECT ll_liandai, ll_jinbi FROM ll_qiandao WHERE ll_useid = ? AND DATE(ll_retime) = ?");
$stmt->execute([$userId, $today]);
$todaySign = $stmt->fetch(PDO::FETCH_ASSOC) ?: null;

$stmt = $pdo->prepare("SELECT MAX(ll_liandai) as max_liandai FROM ll_qiandao WHERE ll_useid = ?");
$stmt->execute([$userId]);
$maxSign = $stmt->fetch(PDO::FETCH_ASSOC);
$stats['sign_days'] = $maxSign ? (int)$maxSign['max_liandai'] : 0;

// 合并统计查询 - 使用 UNION 减少查询次数
$statsSql = "
    SELECT 'topics' as k, COUNT(*) as v FROM ll_lt WHERE ll_useid = ?
    UNION ALL
    SELECT 'replies', COUNT(*) FROM ll_lthf WHERE ll_useid = ?
    UNION ALL
    SELECT 'favorites', COUNT(*) FROM ll_shouchang WHERE ll_useid = ?
    UNION ALL
    SELECT 'downloads', COUNT(*) FROM ll_renwu WHERE ll_useid = ?
    UNION ALL
    SELECT 'comments', COUNT(*) FROM ll_adyxhf WHERE ll_useid = ? AND ll_pid = 0
    UNION ALL
    SELECT 'friends', COUNT(*) FROM ll_friend WHERE (ll_myid = ? OR ll_yourid = ?) AND ll_or = 1
    UNION ALL
    SELECT 'unread_msg', COUNT(*) FROM ll_gestbook WHERE ll_yourid = ? AND ll_reador = 0
    UNION ALL
    SELECT 'fans', COUNT(*) FROM ll_friend WHERE ll_yourid = ? AND ll_or = 1
    UNION ALL
    SELECT 'follow_boards', COUNT(*) FROM ll_follow WHERE ll_useid = ? AND ll_type = 1
";
$stmt = $pdo->prepare($statsSql);
$stmt->execute([$userId, $userId, $userId, $userId, $userId, $userId, $userId, $userId, $userId, $userId]);
$statsData = array_column($stmt->fetchAll(), 'v', 'k');

$stats = array_merge($stats, [
    'topics' => (int)$statsData['topics'],
    'replies' => (int)$statsData['replies'],
    'favorites' => (int)$statsData['favorites'],
    'downloads' => (int)$statsData['downloads'],
    'comments' => (int)$statsData['comments'],
    'friends' => (int)$statsData['friends'],
    'unread_msg' => (int)$statsData['unread_msg'],
    'fans' => (int)$statsData['fans'],
    'follow_boards' => (int)$statsData['follow_boards']
]);


// 等级名称映射
$levelNames = ['游客', '新手玩家', '初级玩家', '中级玩家', '高级玩家', '资深玩家', '专家玩家', '大师玩家'];

// 获取用户信息
$currentUserId = getCurrentUserId();
$currentUser = $currentUserId > 0 ? getUserInfo($currentUserId) : null;
$level = $currentUser ? (int)($currentUser['ll_dj'] ?? 0) : 0;
$levelName = $levelNames[min($level, 7)] ?? '游客';

// 查询实名认证状态
$stmt = $pdo->prepare("SELECT * FROM ll_cash_user_verification WHERE user_id = ? ORDER BY id DESC LIMIT 1");
$stmt->execute([$userId]);
$verification = $stmt->fetch(PDO::FETCH_ASSOC) ?: null;
$verifyStatus = $verification ? (int)$verification['verify_status'] : -1; // -1=未提交, 0=审核中, 1=已认证, 2=已拒绝

// ========== 处理操作 ==========
$message = '';
$messageType = 'success';

// 获取action（支持POST和GET）
$action = $_SERVER['REQUEST_METHOD'] === 'POST' 
    ? ($_POST['action'] ?? ($_GET['action'] ?? ''))
    : ($_GET['action'] ?? '');

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // 修改头像（支持URL和文件上传）
    if ($action === 'update_avatar') {
        $avatar = $_POST['avatar'] ?? '';
        
        // 处理文件上传
        if (!empty($_FILES['avatar_file']['name']) && $_FILES['avatar_file']['error'] === UPLOAD_ERR_OK) {
            $file = $_FILES['avatar_file'];
            $allowed = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
            $maxSize = 2 * 1024 * 1024; // 2MB
            
            if (!in_array($file['type'], $allowed)) {
                $message = '只支持 JPG/PNG/GIF/WebP 格式图片';
                $messageType = 'error';
            } elseif ($file['size'] > $maxSize) {
                $message = '图片大小不能超过 2MB';
                $messageType = 'error';
            } else {
                // 创建上传目录（存到主站根目录，与Nginx代理路径一致）
                $uploadDir = __DIR__ . '/../uploads/avatar/';
                if (!is_dir($uploadDir)) {
                    mkdir($uploadDir, 0755, true);
                }
                
                // 生成文件名
                $ext = pathinfo($file['name'], PATHINFO_EXTENSION);
                $filename = 'avatar_' . $userId . '_' . time() . '.' . $ext;
                $filepath = $uploadDir . $filename;
                
                if (move_uploaded_file($file['tmp_name'], $filepath)) {
                    $avatar = '/uploads/avatar/' . $filename;
                    $pdo->prepare("UPDATE ll_useregs SET ll_img = ? WHERE id = ?")->execute([$avatar, $userId]);
                    $message = '头像上传成功！';
                    // 刷新用户数据
                    $stmt = $pdo->prepare("SELECT * FROM ll_useregs WHERE id = ?");
                    $stmt->execute([$userId]);
                    $user = $stmt->fetch();
                } else {
                    $message = '文件上传失败';
                    $messageType = 'error';
                }
            }
        } elseif (!empty($avatar)) {
            // URL方式
            if (filter_var($avatar, FILTER_VALIDATE_URL) || preg_match('/^https?:\/\//', $avatar) || strpos($avatar, '/') === 0) {
                $pdo->prepare("UPDATE ll_useregs SET ll_img = ? WHERE id = ?")->execute([$avatar, $userId]);
                $message = '头像修改成功！';
                // 刷新用户数据
                $stmt = $pdo->prepare("SELECT * FROM ll_useregs WHERE id = ?");
                $stmt->execute([$userId]);
                $user = $stmt->fetch();
            } else {
                $message = '头像URL格式不正确';
                $messageType = 'error';
            }
        }
    }

    // 修改昵称
    if ($action === 'update_nickname') {
        $nickname = trim($_POST['nickname'] ?? '');
        if (!empty($nickname) && mb_strlen($nickname) <= 20) {
            $pdo->prepare("UPDATE ll_useregs SET ll_n_name = ? WHERE id = ?")->execute([$nickname, $userId]);
            $message = '昵称修改成功！';
            $stmt = $pdo->prepare("SELECT * FROM ll_useregs WHERE id = ?");
            $stmt->execute([$userId]);
            $user = $stmt->fetch();
        } else {
            $message = '昵称不能为空且不超过20个字符';
            $messageType = 'error';
        }
    }

    // 修改性别
    if ($action === 'update_sex') {
        $sex = $_POST['sex'] ?? '';
        if (in_array($sex, ['男', '女'])) {
            $pdo->prepare("UPDATE ll_useregs SET ll_sex = ? WHERE id = ?")->execute([$sex, $userId]);
            $message = '性别修改成功！';
            $stmt = $pdo->prepare("SELECT * FROM ll_useregs WHERE id = ?");
            $stmt->execute([$userId]);
            $user = $stmt->fetch();
        }
    }

    // 修改生日
    if ($action === 'update_birthday') {
        $birthday = $_POST['birthday'] ?? '';
        if (preg_match('/^\d{4}-\d{2}-\d{2}$/', $birthday)) {
            $pdo->prepare("UPDATE ll_useregs SET ll_birthday = ? WHERE id = ?")->execute([$birthday, $userId]);
            $message = '生日修改成功！';
            $stmt = $pdo->prepare("SELECT * FROM ll_useregs WHERE id = ?");
            $stmt->execute([$userId]);
            $user = $stmt->fetch();
        }
    }

    // 修改登录密码
    if ($action === 'update_password') {
        $oldPwd = $_POST['old_password'] ?? '';
        $newPwd = $_POST['new_password'] ?? '';
        $confirmPwd = $_POST['confirm_password'] ?? '';
        
        if (empty($oldPwd) || empty($newPwd) || empty($confirmPwd)) {
            $message = '请填写所有密码字段';
            $messageType = 'error';
        } elseif ($newPwd !== $confirmPwd) {
            $message = '两次输入的新密码不一致';
            $messageType = 'error';
        } elseif (mb_strlen($newPwd) < 6 || mb_strlen($newPwd) > 20) {
            $message = '新密码长度必须为6-20个字符';
            $messageType = 'error';
        } else {
            // 验证旧密码（使用ll_pass字段）
            $stmt = $pdo->prepare("SELECT ll_pass FROM ll_useregs WHERE id = ?");
            $stmt->execute([$userId]);
            $userRow = $stmt->fetch();
            $storedPwd = $userRow['ll_pass'] ?? '';
            
            // 明文密码比较
            if ($oldPwd !== $storedPwd) {
                $message = '原密码错误';
                $messageType = 'error';
            } else {
                // 更新新密码到ll_pass字段
                $pdo->prepare("UPDATE ll_useregs SET ll_pass = ? WHERE id = ?")->execute([$newPwd, $userId]);
                $message = '密码修改成功！';
                // 刷新用户数据
                $stmt = $pdo->prepare("SELECT * FROM ll_useregs WHERE id = ?");
                $stmt->execute([$userId]);
                $user = $stmt->fetch();
            }
        }
    }

    // 修改个人签名
    if ($action === 'update_sign') {
        $sign = trim($_POST['sign'] ?? '');
        if (mb_strlen($sign) <= 100) {
            $pdo->prepare("UPDATE ll_useregs SET ll_sign = ? WHERE id = ?")->execute([$sign, $userId]);
            $message = '个人签名修改成功！';
            $stmt = $pdo->prepare("SELECT * FROM ll_useregs WHERE id = ?");
            $stmt->execute([$userId]);
            $user = $stmt->fetch();
        } else {
            $message = '个人签名不能超过100个字符';
            $messageType = 'error';
        }
    }

    // 绑定手机
    if ($action === 'bind_phone') {
        $phone = trim($_POST['phone'] ?? '');
        if (preg_match('/^1[3-9]\d{9}$/', $phone)) {
            // 检查手机号是否已被其他账号绑定
            $stmt = $pdo->prepare("SELECT id FROM ll_useregs WHERE ll_shouji = ? AND id != ?");
            $stmt->execute([$phone, $userId]);
            if ($stmt->fetch()) {
                $message = '该手机号已被其他账号绑定';
                $messageType = 'error';
            } else {
                $pdo->prepare("UPDATE ll_useregs SET ll_shouji = ? WHERE id = ?")->execute([$phone, $userId]);
                $message = '手机绑定成功！';
                $stmt = $pdo->prepare("SELECT * FROM ll_useregs WHERE id = ?");
                $stmt->execute([$userId]);
                $user = $stmt->fetch();
            }
        } else {
            $message = '请输入正确的手机号';
            $messageType = 'error';
        }
    }

    // 上传背景图片
    if ($action === 'update_background') {
        $bgUrl = trim($_POST['background_url'] ?? '');
        
        // 处理文件上传
        if (!empty($_FILES['background_file']['name']) && $_FILES['background_file']['error'] === UPLOAD_ERR_OK) {
            $file = $_FILES['background_file'];
            $allowed = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
            $maxSize = 5 * 1024 * 1024; // 5MB
            
            if (!in_array($file['type'], $allowed)) {
                $message = '只支持 JPG/PNG/GIF/WebP 格式图片';
                $messageType = 'error';
            } elseif ($file['size'] > $maxSize) {
                $message = '图片大小不能超过 5MB';
                $messageType = 'error';
            } else {
                $uploadDir = __DIR__ . '//uploads/background/';
                if (!is_dir($uploadDir)) {
                    mkdir($uploadDir, 0755, true);
                }
                $ext = pathinfo($file['name'], PATHINFO_EXTENSION);
                $filename = 'bg_' . $userId . '_' . time() . '.' . $ext;
                $filepath = $uploadDir . $filename;
                
                if (move_uploaded_file($file['tmp_name'], $filepath)) {
                    $bgUrl = '/uploads/background/' . $filename;
                } else {
                    $message = '文件上传失败';
                    $messageType = 'error';
                }
            }
        }
        
        if (empty($messageType) || $messageType !== 'error') {
            if (!empty($bgUrl)) {
                $pdo->prepare("UPDATE ll_useregs SET ll_beijing = ? WHERE id = ?")->execute([$bgUrl, $userId]);
                $message = '背景图片设置成功！';
            } else {
                $pdo->prepare("UPDATE ll_useregs SET ll_beijing = NULL WHERE id = ?")->execute([$userId]);
                $message = '背景图片已清除';
            }
            $stmt = $pdo->prepare("SELECT * FROM ll_useregs WHERE id = ?");
            $stmt->execute([$userId]);
            $user = $stmt->fetch();
        }
    }

    // 清除背景图片（支持GET请求）
    if ($action === 'clear_bg') {
        // 先获取当前背景图片路径
        $stmt = $pdo->prepare("SELECT ll_beijing FROM ll_useregs WHERE id = ?");
        $stmt->execute([$userId]);
        $oldUser = $stmt->fetch();
        
        // 删除上传的文件
        $bgPath = $oldUser['ll_beijing'] ?? '';
        if (!empty($bgPath)) {
            // 计算可能的文件路径
            $possiblePaths = [
                $_SERVER['DOCUMENT_ROOT'] . $bgPath,
                __DIR__ . '/../' . $bgPath,
                __DIR__ . '/../../' . $bgPath,
            ];
            foreach ($possiblePaths as $filePath) {
                $filePath = str_replace(['\\', '//'], ['/', '/'], $filePath);
                if (file_exists($filePath)) {
                    @unlink($filePath);
                    error_log("Deleted background file: $filePath");
                    break;
                }
            }
        }
        
        // 清空数据库字段
        $pdo->prepare("UPDATE ll_useregs SET ll_beijing = NULL WHERE id = ?")->execute([$userId]);
        
        // 重定向避免刷新重复提交
        header('Location: ' . '/bbs/user.php?tab=settings&msg=cleared');
        exit;
    }

    // 上传背景音乐
    if ($action === 'update_bgm') {
        if (!empty($_FILES['bgm_file']['name']) && $_FILES['bgm_file']['error'] === UPLOAD_ERR_OK) {
            $file = $_FILES['bgm_file'];
            $allowed = ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg', 'audio/m4a'];
            $maxSize = 10 * 1024 * 1024; // 10MB
            
            $ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
            if (!in_array($ext, ['mp3', 'wav', 'ogg', 'm4a'])) {
                $message = '只支持 MP3/WAV/OGG/M4A 格式音频';
                $messageType = 'error';
            } elseif ($file['size'] > $maxSize) {
                $message = '文件大小不能超过 10MB';
                $messageType = 'error';
            } else {
                $uploadDir = __DIR__ . '//uploads/bgm/';
                if (!is_dir($uploadDir)) {
                    mkdir($uploadDir, 0755, true);
                }
                $filename = 'bgm_' . $userId . '_' . time() . '.' . $ext;
                $filepath = $uploadDir . $filename;
                
                if (move_uploaded_file($file['tmp_name'], $filepath)) {
                    $bgmUrl = '/uploads/bgm/' . $filename;
                    
                    // 删除旧文件
                    $stmt = $pdo->prepare("SELECT ll_bgm FROM ll_useregs WHERE id = ?");
                    $stmt->execute([$userId]);
                    $oldUser = $stmt->fetch();
                    if (!empty($oldUser['ll_bgm'])) {
                        $oldFile = __DIR__ . '/..' . $oldUser['ll_bgm'];
                        if (file_exists($oldFile)) @unlink($oldFile);
                    }
                    
                    $pdo->prepare("UPDATE ll_useregs SET ll_bgm = ? WHERE id = ?")->execute([$bgmUrl, $userId]);
                    $message = '背景音乐上传成功！';
                    
                    // 重新获取用户数据
                    $stmt = $pdo->prepare("SELECT * FROM ll_useregs WHERE id = ?");
                    $stmt->execute([$userId]);
                    $user = $stmt->fetch();
                } else {
                    $message = '文件上传失败';
                    $messageType = 'error';
                }
            }
        } else {
            $message = '请选择音频文件';
            $messageType = 'error';
        }
    }

    // 清除背景音乐
    if ($action === 'clear_bgm') {
        // 获取并删除旧文件
        $stmt = $pdo->prepare("SELECT ll_bgm FROM ll_useregs WHERE id = ?");
        $stmt->execute([$userId]);
        $oldUser = $stmt->fetch();
        if (!empty($oldUser['ll_bgm'])) {
            $oldFile = __DIR__ . '/..' . $oldUser['ll_bgm'];
            if (file_exists($oldFile)) @unlink($oldFile);
        }
        
        $pdo->prepare("UPDATE ll_useregs SET ll_bgm = NULL WHERE id = ?")->execute([$userId]);
        $message = '背景音乐已清除';
        
        // 重新获取用户数据
        $stmt = $pdo->prepare("SELECT * FROM ll_useregs WHERE id = ?");
        $stmt->execute([$userId]);
        $user = $stmt->fetch();
    }

    // 实名认证提交
    if ($action === 'submit_verification') {
        $realName = trim($_POST['real_name'] ?? '');
        $idCard = trim($_POST['id_card'] ?? '');
        $phone = trim($_POST['phone'] ?? '');
        
        // 验证
        if (empty($realName) || mb_strlen($realName) < 2 || mb_strlen($realName) > 20) {
            $message = '请输入正确的姓名（2-20个字符）';
            $messageType = 'error';
        } elseif (!preg_match('/^\d{17}[\dXx]$/', $idCard)) {
            $message = '请输入正确的18位身份证号码';
            $messageType = 'error';
        } elseif (!preg_match('/^1[3-9]\d{9}$/', $phone)) {
            $message = '请输入正确的手机号';
            $messageType = 'error';
        } else {
            // 检查是否已有审核中的记录
            if ($verification && in_array((int)$verification['verify_status'], [0, 1])) {
                if ((int)$verification['verify_status'] === 1) {
                    $message = '您已完成实名认证，无需重复提交';
                } else {
                    $message = '您的认证正在审核中，请耐心等待';
                }
                $messageType = 'error';
            } else {
                // 插入或更新认证记录
                // BBS用户已通过登录验证，直接设为已认证状态 (verify_status=1)
                if ($verification) {
                    // 更新已有记录（之前被拒绝的）
                    $pdo->prepare("UPDATE ll_cash_user_verification SET 
                        real_name = ?, id_card = ?, phone = ?, verify_status = 1, 
                        verify_method = 'bbs', verified_at = NOW(), submitted_at = NOW(), updated_at = NOW()
                        WHERE id = ?")->execute([$realName, $idCard, $phone, $verification['id']]);
                } else {
                    // 新建认证记录
                    $pdo->prepare("INSERT INTO ll_cash_user_verification 
                        (user_id, real_name, id_card, phone, verify_status, verify_method, verified_at, submitted_at, created_at, updated_at)
                        VALUES (?, ?, ?, ?, 1, 'bbs', NOW(), NOW(), NOW(), NOW())")
                        ->execute([$userId, $realName, $idCard, $phone]);
                }
                
                // 同步更新ll_useregs表中的手机号（如果还没绑定）
                if (empty($user['ll_shouji'])) {
                    $pdo->prepare("UPDATE ll_useregs SET ll_shouji = ? WHERE id = ?")->execute([$phone, $userId]);
                }
                
                $message = '实名认证提交成功！现在可以参与现金任务了。';
                
                // 刷新认证状态
                $stmt = $pdo->prepare("SELECT * FROM ll_cash_user_verification WHERE user_id = ? ORDER BY id DESC LIMIT 1");
                $stmt->execute([$userId]);
                $verification = $stmt->fetch(PDO::FETCH_ASSOC) ?: null;
                $verifyStatus = $verification ? (int)$verification['verify_status'] : -1;
                
                // 刷新用户数据
                $stmt = $pdo->prepare("SELECT * FROM ll_useregs WHERE id = ?");
                $stmt->execute([$userId]);
                $user = $stmt->fetch();
            }
        }
    }

    // 签到
    if ($action === 'signin') {
        if ($todaySign) {
            $message = '今日已签到！';
            $messageType = 'error';
        } else {
            // 计算连续签到
            $yesterday = date('Y-m-d', strtotime('-1 day'));
            $stmt = $pdo->prepare("SELECT ll_liandai FROM ll_qiandao WHERE ll_useid = ? AND DATE(ll_retime) = ? ORDER BY id DESC LIMIT 1");
            $stmt->execute([$userId, $yesterday]);
            $lastRecord = $stmt->fetch();
            $liandai = $lastRecord ? (int)$lastRecord['ll_liandai'] + 1 : 1;

            // 计算奖励
            $reward = 10;
            if ($liandai >= 7) $reward = 20;
            if ($liandai >= 30) $reward = 50;

            // 插入签到记录
            $pdo->prepare("INSERT INTO ll_qiandao (ll_useid, ll_jinbi, ll_liandai, ll_retime) VALUES (?, ?, ?, NOW())")
                ->execute([$userId, $reward, $liandai]);

            // 更新用户金币和经验
            $pdo->prepare("UPDATE ll_useregs SET ll_mm = COALESCE(ll_mm, 0) + ?, ll_jy = COALESCE(ll_jy, 0) + 1 WHERE id = ?")
                ->execute([$reward, $userId]);

            $message = '签到成功！获得' . " {$reward} " . '金币，连续签到' . " {$liandai} " . '天';
            $stats['sign_days'] = $liandai;

            // 刷新用户数据
            $stmt = $pdo->prepare("SELECT * FROM ll_useregs WHERE id = ?");
            $stmt->execute([$userId]);
            $user = $stmt->fetch();

            // 更新签到状态
            $todaySign = ['ll_liandai' => $liandai, 'll_jinbi' => $reward];
        }
    }

    // 每日任务上报
    if ($action === 'do_task' && is_logged_in()) {
        $taskId = $_POST['task_id'] ?? '';
        $tasks = [
            'download' => ['name' => '下载游戏', 'reward' => 5],
            'comment' => ['name' => '发表评论', 'reward' => 3],
            'forum' => ['name' => '社区发帖', 'reward' => 5],
            'share' => ['name' => '分享游戏', 'reward' => 2]
        ];
        
        if (isset($tasks[$taskId])) {
            $task = $tasks[$taskId];
            $today = date('Y-m-d');
            
            // 检查是否已完成
            $stmt = $pdo->prepare('SELECT id FROM ll_task_log WHERE ll_useid = ? AND ll_task = ? AND DATE(ll_retime) = ?');
            $stmt->execute([$userId, $taskId, $today]);
            if (!$stmt->fetch()) {
                // 记录任务完成
                $pdo->prepare('INSERT INTO ll_task_log (ll_useid, ll_task, ll_reward, ll_retime) VALUES (?, ?, ?, NOW())')
                    ->execute([$userId, $taskId, $task['reward']]);
                // 增加金币
                $pdo->prepare('UPDATE ll_useregs SET ll_mm = COALESCE(ll_mm, 0) + ? WHERE id = ?')
                    ->execute([$task['reward'], $userId]);
                $message = '任务完成！获得' . " {$task['reward']} " . '金币';
                // 刷新用户数据
                $stmt = $pdo->prepare("SELECT * FROM ll_useregs WHERE id = ?");
                $stmt->execute([$userId]);
                $user = $stmt->fetch();
            }
        }
    }

    // 同意/拒绝好友请求
    if ($action === 'friend_action') {
        $fid = (int)($_POST['fid'] ?? 0);
        $type = $_POST['type'] ?? ''; // 'accept' or 'reject'

        if ($fid > 0) {
            if ($type === 'accept') {
                $pdo->prepare("UPDATE ll_friend SET ll_or = 1 WHERE id = ? AND ll_yourid = ?")->execute([$fid, $userId]);
                $message = '已同意好友请求！';
            } else {
                $pdo->prepare("DELETE FROM ll_friend WHERE id = ? AND ll_yourid = ?")->execute([$fid, $userId]);
                $message = '已拒绝好友请求！';
            }
        }
    }

    // 删除收藏
    if ($action === 'del_favorite') {
        $fid = (int)($_POST['fid'] ?? 0);
        if ($fid > 0) {
            $pdo->prepare("DELETE FROM ll_shouchang WHERE id = ? AND ll_useid = ?")->execute([$fid, $userId]);
            $message = '已取消收藏！';
        }
    }

    // 删除下载记录
    if ($action === 'del_download') {
        $did = (int)($_POST['did'] ?? 0);
        if ($did > 0) {
            $pdo->prepare("DELETE FROM ll_renwu WHERE id = ? AND ll_useid = ?")->execute([$did, $userId]);
            $message = '已删除下载记录！';
        }
    }
}

// ========== 获取各标签数据 ==========

// 每日任务 - 获取今日完成状态
$today = date('Y-m-d');
$taskList = [
    ['id' => 'signin', 'name' => '每日签到', 'reward' => 10, 'desc' => '每天签到领取金币', 'auto' => true],
    ['id' => 'download', 'name' => '下载游戏', 'reward' => 5, 'desc' => '下载一款游戏', 'auto' => false],
    ['id' => 'comment', 'name' => '发表评论', 'reward' => 3, 'desc' => '为游戏发表评论', 'auto' => false],
    ['id' => 'forum', 'name' => '社区发帖', 'reward' => 5, 'desc' => '在社区发表帖子', 'auto' => false],
    ['id' => 'share', 'name' => '分享游戏', 'reward' => 2, 'desc' => '分享一款游戏', 'auto' => false]
];

// 查询任务完成状态（从 ll_task_log）
$taskIds = array_filter(array_column($taskList, 'id'), fn($id) => $id !== 'signin');
$doneTasks = [];
if (!empty($taskIds)) {
    $placeholders = str_repeat('?,', count($taskIds) - 1) . '?';
    $stmt = $pdo->prepare("SELECT ll_task FROM ll_task_log WHERE ll_useid = ? AND DATE(ll_retime) = ? AND ll_task IN ($placeholders)");
    $stmt->execute(array_merge([$userId, $today], $taskIds));
    $doneTasks = array_column($stmt->fetchAll(), 'll_task');
}

// 检查签到（从 ll_qiandao 表）
$stmt = $pdo->prepare("SELECT id FROM ll_qiandao WHERE ll_useid = ? AND DATE(ll_retime) = ?");
$stmt->execute([$userId, $today]);
if ($stmt->fetch()) {
    $doneTasks[] = 'signin';
}

// 更新任务状态
foreach ($taskList as &$task) {
    $task['done'] = in_array($task['id'], $doneTasks);
}
unset($task);

// 我的帖子 - 支持最新/最热排序
if ($tab === 'topics') {
    $page = max(1, intval($_GET['page'] ?? 1));
    $pageSize = 10;
    $offset = ($page - 1) * $pageSize;
    $sortType = $_GET['sort'] ?? 'latest';
    $totalPages = max(1, ceil($stats['topics'] / $pageSize));

    // 根据排序类型选择查询
    if ($sortType === 'hot') {
        // 最热排序：按回复数+浏览数
        $stmt = $pdo->prepare("
            SELECT id, ll_biaoti, ll_rc, ll_rchf, ll_time1 
            FROM ll_lt 
            WHERE ll_useid = ? AND ll_or = 0 
            ORDER BY (COALESCE(ll_rchf, 0) + COALESCE(ll_rc, 0)) DESC, id DESC
            LIMIT ? OFFSET ?
        ");
        $stmt->execute([$userId, $pageSize, $offset]);
    } else {
        // 最新排序：按ID倒序
        $stmt = $pdo->prepare("
            SELECT id, ll_biaoti, ll_rc, ll_rchf, ll_time1 
            FROM ll_lt 
            WHERE ll_useid = ? AND ll_or = 0 
            ORDER BY id DESC 
            LIMIT ? OFFSET ?
        ");
        $stmt->execute([$userId, $pageSize, $offset]);
    }
    $topics = $stmt->fetchAll();
    
    // 批量获取回复数（IN 查询，10条记录很快）
    if (!empty($topics)) {
        $ids = array_column($topics, 'id');
        $placeholders = implode(',', array_fill(0, count($ids), '?'));
        $stmt = $pdo->prepare("SELECT ll_id, COUNT(*) as cnt FROM ll_lthf WHERE ll_id IN ($placeholders) GROUP BY ll_id");
        $stmt->execute($ids);
        $replyCounts = array_column($stmt->fetchAll(), 'cnt', 'll_id');
        foreach ($topics as &$t) {
            $t['reply_count'] = $replyCounts[$t['id']] ?? 0;
        }
        unset($t);
    }
    $myTopics = $topics;
}

// 我的收藏
if ($tab === 'favorites') {
    $stmt = $pdo->prepare("
        SELECT id, ll_id as topic_id, ll_biaoti, ll_logo, ll_retime
        FROM ll_shouchang WHERE ll_useid = ?
        ORDER BY id DESC LIMIT 20
    ");
    $stmt->execute([$userId]);
    $favorites = $stmt->fetchAll();
}

// 我的下载
if ($tab === 'downloads') {
    $page = max(1, intval($_GET['page'] ?? 1));
    $pageSize = 10;
    $offset = ($page - 1) * $pageSize;

    $stmt = $pdo->prepare("SELECT COUNT(*) FROM ll_renwu WHERE ll_useid = ?");
    $stmt->execute([$userId]);
    $totalDown = $stmt->fetchColumn();
    $totalPages = max(1, ceil($totalDown / $pageSize));

    $stmt = $pdo->prepare("
        SELECT r.id, r.ll_idd, r.ll_retime, w.ll_biaoti, w.ll_logo, w.ll_banben
        FROM ll_renwu r
        LEFT JOIN ll_wadyx w ON r.ll_idd = w.id
        WHERE r.ll_useid = ? AND r.ll_idd > 0
        ORDER BY r.ll_retime DESC LIMIT ? OFFSET ?
    ");
    $stmt->execute([$userId, $pageSize, $offset]);
    $downloads = $stmt->fetchAll();
}

// 我的评论
if ($tab === 'comments') {
    $page = max(1, intval($_GET['page'] ?? 1));
    $pageSize = 10;
    $offset = ($page - 1) * $pageSize;

    $stmt = $pdo->prepare("SELECT COUNT(*) FROM ll_adyxhf WHERE ll_useid = ? AND ll_pid = 0");
    $stmt->execute([$userId]);
    $totalComments = $stmt->fetchColumn();
    $totalPages = max(1, ceil($totalComments / $pageSize));

    $stmt = $pdo->prepare("
        SELECT c.id, c.ll_id, c.ll_idd, c.ll_text, c.ll_time, c.ll_zan,
               w.ll_biaoti, w.ll_logo
        FROM ll_adyxhf c
        LEFT JOIN ll_wadyx w ON c.ll_id = w.id
        WHERE c.ll_useid = ? AND c.ll_pid = 0 AND c.ll_status = 0
        ORDER BY c.ll_time DESC LIMIT ? OFFSET ?
    ");
    $stmt->execute([$userId, $pageSize, $offset]);
    $comments = $stmt->fetchAll();
}

// 我的回复 - 支持最新/点赞最多排序
if ($tab === 'replies') {
    $page = max(1, intval($_GET['page'] ?? 1));
    $pageSize = 10;
    $offset = ($page - 1) * $pageSize;
    $sortType = $_GET['sort'] ?? 'latest';

    $stmt = $pdo->prepare("SELECT COUNT(*) FROM ll_lthf WHERE ll_useid = ?");
    $stmt->execute([$userId]);
    $totalReplies = $stmt->fetchColumn();
    $totalPages = max(1, ceil($totalReplies / $pageSize));

    // 根据排序类型选择查询
    if ($sortType === 'hot') {
        // 点赞最多排序
        $stmt = $pdo->prepare("
            SELECT h.id, h.ll_id as topic_id, h.ll_text, h.ll_time, h.ll_zan,
                   t.ll_biaoti as topic_title
            FROM ll_lthf h
            LEFT JOIN ll_lt t ON h.ll_id = t.id
            WHERE h.ll_useid = ?
            ORDER BY h.ll_zan DESC, h.id DESC
            LIMIT ? OFFSET ?
        ");
    } else {
        // 最新排序
        $stmt = $pdo->prepare("
            SELECT h.id, h.ll_id as topic_id, h.ll_text, h.ll_time, h.ll_zan,
                   t.ll_biaoti as topic_title
            FROM ll_lthf h
            LEFT JOIN ll_lt t ON h.ll_id = t.id
            WHERE h.ll_useid = ?
            ORDER BY h.id DESC LIMIT ? OFFSET ?
        ");
    }
    $stmt->execute([$userId, $pageSize, $offset]);
    $myReplies = $stmt->fetchAll();
}

// 好友列表
if ($tab === 'friends') {
    // 已确认好友（双向查询：我发出的和我收到的都已确认）
    $stmt = $pdo->prepare("
        SELECT f.id, 
               CASE WHEN f.ll_myid = ? THEN f.ll_yourid ELSE f.ll_myid END as friend_id,
               u.ll_n_name, u.ll_name, u.ll_img, u.ll_dj
        FROM ll_friend f
        LEFT JOIN ll_useregs u ON u.id = CASE WHEN f.ll_myid = ? THEN f.ll_yourid ELSE f.ll_myid END
        WHERE (f.ll_myid = ? OR f.ll_yourid = ?) AND f.ll_or = 1
        ORDER BY f.id DESC
    ");
    $stmt->execute([$userId, $userId, $userId, $userId]);
    $friends = $stmt->fetchAll();

    // 待验证请求（我收到的请求）
    $stmt = $pdo->prepare("
        SELECT f.id, f.ll_myid as requester_id,
               u.ll_n_name, u.ll_name, u.ll_img
        FROM ll_friend f
        LEFT JOIN ll_useregs u ON f.ll_myid = u.id
        WHERE f.ll_yourid = ? AND f.ll_or = 0
        ORDER BY f.id DESC
    ");
    $stmt->execute([$userId]);
    $friendRequests = $stmt->fetchAll();
}

// 私信 - 按对话分组
if ($tab === 'messages') {
    $page = max(1, intval($_GET['page'] ?? 1));
    $pageSize = 20;
    $offset = ($page - 1) * $pageSize;

    // 获取与我有过私信的所有人（使用子查询获取最新消息）
    $stmt = $pdo->prepare("
        SELECT 
            c.partner_id,
            c.partner_name,
            c.partner_img,
            c.unread_count,
            c.msg_count,
            m.ll_text as last_msg,
            m.ll_time as last_time
        FROM (
            SELECT 
                partner_id,
                MAX(partner_name) as partner_name,
                MAX(partner_img) as partner_img,
                SUM(unread) as unread_count,
                COUNT(*) as msg_count
            FROM (
                SELECT 
                    m.ll_myid as partner_id,
                    COALESCE(u.ll_n_name, u.ll_name, '未知用户') as partner_name,
                    u.ll_img as partner_img,
                    CASE WHEN m.ll_reador = 0 THEN 1 ELSE 0 END as unread
                FROM ll_gestbook m
                LEFT JOIN ll_useregs u ON m.ll_myid = u.id
                WHERE m.ll_yourid = ?
                
                UNION ALL
                
                SELECT 
                    m.ll_yourid as partner_id,
                    COALESCE(u.ll_n_name, u.ll_name, '未知用户') as partner_name,
                    u.ll_img as partner_img,
                    0 as unread
                FROM ll_gestbook m
                LEFT JOIN ll_useregs u ON m.ll_yourid = u.id
                WHERE m.ll_myid = ?
            ) as all_msgs
            GROUP BY partner_id
        ) as c
        LEFT JOIN ll_gestbook m ON m.id = (
            SELECT id FROM ll_gestbook 
            WHERE (ll_myid = c.partner_id AND ll_yourid = ?) 
               OR (ll_myid = ? AND ll_yourid = c.partner_id)
            ORDER BY ll_time DESC LIMIT 1
        )
        ORDER BY last_time DESC
        LIMIT ? OFFSET ?
    ");
    $stmt->execute([$userId, $userId, $userId, $userId, $pageSize, $offset]);
    $conversations = $stmt->fetchAll();

    // 统计总对话数
    $stmt = $pdo->prepare("
        SELECT COUNT(DISTINCT partner_id) FROM (
            SELECT ll_myid as partner_id FROM ll_gestbook WHERE ll_yourid = ?
            UNION
            SELECT ll_yourid as partner_id FROM ll_gestbook WHERE ll_myid = ?
        ) as partners
    ");
    $stmt->execute([$userId, $userId]);
    $totalConversations = $stmt->fetchColumn();
    $totalPages = max(1, ceil($totalConversations / $pageSize));

    // 标记所有发给当前用户的私信为已读
    $pdo->prepare("UPDATE ll_gestbook SET ll_reador = 1 WHERE ll_yourid = ?")->execute([$userId]);
}

// 粉丝列表
if ($tab === 'fans') {
    $page = max(1, intval($_GET['page'] ?? 1));
    $pageSize = 20;
    $offset = ($page - 1) * $pageSize;

    $stmt = $pdo->prepare("SELECT COUNT(*) FROM ll_friend WHERE ll_yourid = ? AND ll_or = 1");
    $stmt->execute([$userId]);
    $totalFans = $stmt->fetchColumn();
    $totalPages = max(1, ceil($totalFans / $pageSize));

    $stmt = $pdo->prepare("
        SELECT f.id, f.ll_myid as fan_userid, u.ll_n_name, u.ll_name, u.ll_img, u.ll_dj
        FROM ll_friend f
        LEFT JOIN ll_useregs u ON f.ll_myid = u.id
        WHERE f.ll_yourid = ? AND f.ll_or = 1
        ORDER BY f.id DESC LIMIT ? OFFSET ?
    ");
    $stmt->execute([$userId, $pageSize, $offset]);
    $fans = $stmt->fetchAll();
}

// 关注的版块最新帖子
if ($tab === 'followforum') {
    $page = max(1, intval($_GET['page'] ?? 1));
    $pageSize = 10;
    $offset = ($page - 1) * $pageSize;

    // 获取我关注的版块对应的最新帖子
    $stmt = $pdo->prepare("
        SELECT COUNT(*) FROM ll_lt t
        INNER JOIN ll_follow f ON t.ll_idd = f.ll_idd AND f.ll_type = 1
        WHERE f.ll_useid = ? AND t.ll_or = 0
    ");
    $stmt->execute([$userId]);
    $totalForumPosts = $stmt->fetchColumn();
    $totalPages = max(1, ceil($totalForumPosts / $pageSize));

    $stmt = $pdo->prepare("
        SELECT t.id, t.ll_biaoti, t.ll_text, t.ll_rchf, t.ll_tongji, t.ll_retime,
               c.ll_title as board_name,
               (SELECT COUNT(*) FROM ll_lthf r WHERE r.ll_id = t.id) as reply_count
        FROM ll_lt t
        INNER JOIN ll_follow f ON t.ll_idd = f.ll_idd AND f.ll_type = 1
        LEFT JOIN ll_class c ON t.ll_idd = c.id
        WHERE f.ll_useid = ? AND t.ll_or = 0
        ORDER BY t.ll_retime DESC LIMIT ? OFFSET ?
    ");
    $stmt->execute([$userId, $pageSize, $offset]);
    $forumPosts = $stmt->fetchAll();
}
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="noindex,nofollow">
    <title><?php echo e('个人中心 - 7坛游戏社区'); ?></title>
    <link rel="stylesheet" href="<?php echo $baseUrl; ?>css/style.css">
    <link rel="stylesheet" href="<?php echo $baseUrl; ?>css/mobile-nav.css?v=20260919">
    <style>
    .user-profile-header {
        <?php if (!empty($user['ll_beijing'])): ?>
        background: linear-gradient(rgba(0,0,0,0.3), rgba(0,0,0,0.3)), url('<?php echo e($user['ll_beijing']); ?>') center/cover no-repeat;
        <?php else: ?>
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        <?php endif; ?>
        color: white;
        padding: 30px 20px;
        border-radius: 12px;
        margin-bottom: 20px;
    }
    .profile-top {
        display: flex;
        align-items: center;
        gap: 20px;
    }
    .profile-avatar {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        border: 3px solid white;
        object-fit: cover;
    }
    .profile-info h2 {
        margin: 0 0 5px 0;
        font-size: 22px;
    }
    .profile-info .username {
        opacity: 0.9;
        font-size: 14px;
    }
    .profile-level {
        display: inline-block;
        background: rgba(255,255,255,0.2);
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 13px;
        margin-top: 8px;
    }
    .profile-stats-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 10px;
        margin-top: 20px;
    }
    .stat-box {
        text-align: center;
        background: rgba(255,255,255,0.15);
        padding: 12px 8px;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s;
    }
    .stat-box:hover {
        background: rgba(255,255,255,0.25);
        transform: translateY(-2px);
    }
    .stat-box .num {
        font-size: 20px;
        font-weight: bold;
    }
    .stat-box .txt {
        font-size: 12px;
        opacity: 0.9;
        margin-top: 3px;
    }
    .tabs {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        padding: 15px 0;
        border-bottom: 2px solid #eee;
        margin-bottom: 20px;
    }
    .tab-btn {
        padding: 8px 16px;
        border-radius: 20px;
        text-decoration: none;
        color: #666;
        font-size: 14px;
        transition: all 0.2s;
    }
    .tab-btn:hover, .tab-btn.active {
        background: #667eea;
        color: white;
    }
    .tab-btn .badge {
        background: #ff4757;
        color: white;
        padding: 2px 6px;
        border-radius: 10px;
        font-size: 11px;
        margin-left: 5px;
    }
    .sub-tabs {
        display: flex;
        gap: 8px;
    }
    .sub-tab {
        padding: 6px 14px;
        border-radius: 15px;
        text-decoration: none;
        color: #666;
        font-size: 13px;
        background: #f0f0f0;
        transition: all 0.2s;
    }
    .sub-tab:hover {
        background: #e0e0e0;
    }
    .sub-tab.active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    .edit-form {
        background: #f8f9fa;
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    .edit-form h4 {
        margin: 0 0 15px 0;
        color: #333;
    }
    .form-row {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 15px;
    }
    .form-row label {
        width: 80px;
        color: #666;
    }
    .form-row input[type="text"],
    .form-row input[type="date"] {
        flex: 1;
        padding: 8px 12px;
        border: 1px solid #ddd;
        border-radius: 4px;
        font-size: 14px;
    }
    .form-row select {
        flex: 1;
        padding: 8px 12px;
        border: 1px solid #ddd;
        border-radius: 4px;
        font-size: 14px;
    }
    .game-card {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 10px;
        display: flex;
        gap: 12px;
        align-items: center;
        margin-bottom: 10px;
    }
    .game-card img {
        width: 60px;
        height: 60px;
        border-radius: 8px;
        object-fit: cover;
    }
    .game-card .info {
        flex: 1;
    }
    .game-card .name {
        font-weight: bold;
        color: #333;
        margin-bottom: 5px;
    }
    .game-card .meta {
        font-size: 12px;
        color: #999;
    }
    .message-item {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
        display: flex;
        gap: 12px;
        text-decoration: none;
        color: inherit;
        transition: all 0.2s;
    }
    .message-item:hover {
        background: #e8f4ff;
        transform: translateX(5px);
    }
    .message-item.unread {
        background: #e8f4ff;
        border-left: 3px solid #667eea;
    }
    .message-item img {
        width: 40px;
        height: 40px;
        border-radius: 50%;
    }
    /* 对话列表样式 */
    .conversation-item {
        display: flex;
        align-items: center;
        padding: 15px 20px;
        border-bottom: 1px solid #eee;
        text-decoration: none;
        color: inherit;
        transition: background 0.2s;
    }
    .conversation-item:hover {
        background: #f8f9fa;
    }
    .conversation-item.unread {
        background: #f0f7ff;
    }
    .conversation-item.unread .conv-name {
        font-weight: 600;
    }
    .conv-avatar {
        width: 50px;
        height: 50px;
        border-radius: 50%;
        object-fit: cover;
        margin-right: 15px;
        flex-shrink: 0;
    }
    .conv-content {
        flex: 1;
        min-width: 0;
    }
    .conv-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 5px;
    }
    .conv-name {
        font-weight: 500;
        color: #333;
    }
    .conv-time {
        font-size: 12px;
        color: #999;
    }
    .conv-preview {
        font-size: 13px;
        color: #666;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .conv-badge {
        background: #e8e8e8;
        color: #666;
        font-size: 11px;
        padding: 2px 6px;
        border-radius: 10px;
    }
    .conv-unread-dot {
        width: 8px;
        height: 8px;
        background: #ff4757;
        border-radius: 50%;
        flex-shrink: 0;
    }
    .friend-item {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .friend-item a {
        display: flex;
        align-items: center;
        gap: 12px;
        flex: 1;
        text-decoration: none;
        color: inherit;
    }
    .friend-item a:hover {
        color: #667eea;
    }
    .friend-item img {
        width: 50px;
        height: 50px;
        border-radius: 50%;
    }
    .friend-item .name {
        flex: 1;
        font-weight: bold;
    }
    .friend-item .level {
        font-size: 12px;
        color: #999;
    }
    .friend-request {
        background: #fff3e0;
        border-left: 3px solid #ff9800;
    }
    .btn-sm {
        padding: 5px 12px;
        border-radius: 4px;
        font-size: 12px;
        border: none;
        cursor: pointer;
    }
    .btn-primary {
        background: #667eea;
        color: white;
    }
    .btn-danger {
        background: #ff4757;
        color: white;
    }
    .btn-success {
        background: #27ae60;
        color: white;
    }
    .sign-btn {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        border: none;
        padding: 12px 30px;
        border-radius: 25px;
        font-size: 16px;
        cursor: pointer;
        margin-top: 15px;
    }
    .sign-btn:disabled {
        background: #ccc;
        cursor: not-allowed;
    }
    .sign-info {
        margin-top: 10px;
        font-size: 13px;
        color: rgba(255,255,255,0.9);
    }
    .user-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
        gap: 15px;
        padding: 10px 0;
    }
    .user-card {
        text-align: center;
        text-decoration: none;
        color: #333;
        transition: transform 0.2s;
    }
    .user-card:hover {
        transform: translateY(-3px);
    }
    .user-card img {
        width: 60px;
        height: 60px;
        border-radius: 50%;
        object-fit: cover;
        border: 2px solid #eee;
        margin-bottom: 8px;
    }
    .user-card .name {
        font-size: 13px;
        color: #333;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .user-card .level {
        font-size: 11px;
        color: #888;
        margin-top: 2px;
    }
    .topic-preview {
        color: #666;
        font-size: 12px;
        margin-top: 5px;
        line-height: 1.4;
    }
    /* 每日任务样式 */
    .task-list {
        display: flex;
        flex-direction: column;
        gap: 12px;
    }
    .task-item {
        display: flex;
        align-items: center;
        padding: 15px;
        background: #f8f9fa;
        border-radius: 10px;
        transition: all 0.3s;
    }
    .task-item.done {
        background: #e8f5e9;
    }
    .task-item:hover {
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .task-icon {
        font-size: 28px;
        margin-right: 15px;
    }
    .task-info {
        flex: 1;
    }
    .task-name {
        font-weight: 600;
        color: #333;
        margin-bottom: 4px;
    }
    .task-desc {
        font-size: 13px;
        color: #888;
    }
    .task-reward {
        font-size: 16px;
        font-weight: 600;
        color: #f39c12;
        margin: 0 20px;
    }
    .task-done-tag {
        background: #27ae60;
        color: white;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 13px;
    }
    .task-summary {
        margin-top: 25px;
        padding: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        color: white;
    }
    .task-progress {
        margin-bottom: 12px;
    }
    .task-progress strong {
        font-size: 18px;
    }
    .progress-bar {
        height: 8px;
        background: rgba(255,255,255,0.3);
        border-radius: 4px;
        margin-top: 8px;
        overflow: hidden;
    }
    .progress-fill {
        height: 100%;
        background: white;
        border-radius: 4px;
        transition: width 0.5s ease;
    }
    .task-rewards {
        font-size: 14px;
        opacity: 0.9;
    }
    .task-rewards strong {
        font-size: 18px;
    }
    @media (max-width: 768px) {
        .profile-stats-grid {
            grid-template-columns: repeat(3, 1fr);
        }
    }
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
<script>window.UC_I18N = <?php echo json_encode(array(
  'playing' => '播放中', 'paused' => '已暂停',
  'clickPlay' => '点击播放按钮开启音乐',
  'loading' => '加载中...', 'noMore' => '没有更多了', 'more' => '上拉加载更多...',
  'justNow' => '刚刚', 'minAgo' => '分钟前', 'hourAgo' => '小时前', 'dayAgo' => '天前',
  'unknownTopic' => '未知帖子', 'reply' => '回复', 'views' => '浏览',
  'pwdShort' => '新密码长度不能少于6位', 'pwdMismatch' => '两次输入的新密码不一致',
  'selected' => '已选择文件，点击下方「保存头像」按钮即可上传',
  'confirmClearBg' => '确定要清除背景图片吗？', 'confirmClearBgm' => '确定要清除背景音乐吗？',
  'confirmUnfav' => '确定取消收藏？', 'confirmDel' => '确定删除？',
), JSON_UNESCAPED_UNICODE); ?>;</script>
    <header class="header">
        <div class="container">
            <div class="header-content">
                <a href="/" class="logo">
                    <span class="logo-icon">🎮</span>
                    <span class="logo-text"><?php echo e('7坛游戏'); ?></span>
                </a>
                <nav class="nav">
                    <a href="https://www.7tan.com/"><?php echo e('首页'); ?></a>
                    <a href="https://www.7tan.com/ai-tool/"><?php echo e('AI工具'); ?></a>
                    <a href="user.php" class="active"><?php echo e('个人中心'); ?></a>
                    <a href="logout.php"><?php echo e('退出'); ?></a>
                </nav>
            </div>
        </div>
    </header>

    <main class="main">
        <div class="container">
            <?php if ($message): ?>
            <div style="background: <?php echo $messageType === 'error' ? '#ff4757' : '#27ae60'; ?>; color: white; padding: 12px 20px; border-radius: 8px; margin-bottom: 20px;">
                <?php echo e($message); ?>
            </div>
            <?php endif; ?>

            <!-- 用户信息头部 -->
            <div class="user-profile-header">
                <div class="profile-top">
                    <img src="<?php echo e($user['ll_img'] ?: '/images/logo.png'); ?>" alt="" class="profile-avatar" onerror="this.onerror=null;this.src='/images/logo.png';">
                    <div class="profile-info">
                        <h2><?php echo e($user['ll_n_name'] ?: $user['ll_name']); ?></h2>
                        <div class="username">@<?php echo e($user['ll_name']); ?></div>
                        <div class="profile-level">Lv.<?php echo $level; ?> <?php echo e($levelName); ?></div>
                    </div>
                </div>
                <div class="profile-stats-grid">
                    <div class="stat-box" onclick="location.href='?tab=topics'">
                        <div class="num"><?php echo $stats['topics']; ?></div>
                        <div class="txt"><?php echo e('帖子'); ?></div>
                    </div>
                    <div class="stat-box" onclick="location.href='?tab=replies'">
                        <div class="num"><?php echo $stats['replies']; ?></div>
                        <div class="txt"><?php echo e('回复'); ?></div>
                    </div>
                    <div class="stat-box" onclick="location.href='?tab=favorites'">
                        <div class="num"><?php echo $stats['favorites']; ?></div>
                        <div class="txt"><?php echo e('收藏'); ?></div>
                    </div>
                    <div class="stat-box" onclick="location.href='?tab=downloads'">
                        <div class="num"><?php echo $stats['downloads']; ?></div>
                        <div class="txt"><?php echo e('下载'); ?></div>
                    </div>
                    <div class="stat-box" onclick="location.href='?tab=friends'">
                        <div class="num"><?php echo $stats['friends']; ?></div>
                        <div class="txt"><?php echo e('好友'); ?></div>
                    </div>
                </div>
            </div>

            <!-- 标签导航 -->
            <div class="tabs">
                <a href="?tab=profile" class="tab-btn <?php echo $tab === 'profile' ? 'active' : ''; ?>">📋 <?php echo e('个人资料'); ?></a>
                <a href="?tab=edit" class="tab-btn <?php echo $tab === 'edit' ? 'active' : ''; ?>">✏️ <?php echo e('编辑资料'); ?></a>
                <a href="?tab=signin" class="tab-btn <?php echo $tab === 'signin' ? 'active' : ''; ?>">
                📅 <?php echo e('签到'); ?>
                <?php if (!$todaySign): ?><span class="badge">!</span><?php elseif ($todaySign): ?><span class="badge"><?php echo e('已签'); ?></span><?php endif; ?>
            </a>
            <a href="?tab=tasks" class="tab-btn <?php echo $tab === 'tasks' ? 'active' : ''; ?>">🎯 <?php echo e('每日任务'); ?></a>
                <a href="?tab=verify" class="tab-btn <?php echo $tab === 'verify' ? 'active' : ''; ?>">
                    🪪 <?php echo e('实名认证'); ?>
                    <?php if ($verifyStatus === -1): ?><span class="badge" style="background:#f39c12;"><?php echo e('未认证'); ?></span>
                    <?php elseif ($verifyStatus === 0): ?><span class="badge" style="background:#3498db;"><?php echo e('审核中'); ?></span>
                    <?php elseif ($verifyStatus === 1): ?><span class="badge" style="background:#27ae60;"><?php echo e('已认证'); ?></span>
                    <?php elseif ($verifyStatus === 2): ?><span class="badge" style="background:#e74c3c;"><?php echo e('已拒绝'); ?></span>
                    <?php endif; ?>
                </a>
                <a href="/task/wallet.php" class="tab-btn">💵 <?php echo e('现金任务'); ?></a>
                <a href="?tab=downloads" class="tab-btn <?php echo $tab === 'downloads' ? 'active' : ''; ?>">📥 <?php echo e('下载记录'); ?></a>
                <a href="?tab=comments" class="tab-btn <?php echo $tab === 'comments' ? 'active' : ''; ?>">🎮 <?php echo e('游戏评论'); ?></a>
                <a href="?tab=friends" class="tab-btn <?php echo $tab === 'friends' ? 'active' : ''; ?>">
                    👥 <?php echo e('好友列表'); ?>
                    <?php if (count($friendRequests ?? []) > 0): ?><span class="badge"><?php echo count($friendRequests); ?></span><?php endif; ?>
                </a>
                <a href="?tab=fans" class="tab-btn <?php echo $tab === 'fans' ? 'active' : ''; ?>">
                    👕 <?php echo e('粉丝'); ?>
                    <?php if ($stats['fans'] > 0): ?><span class="badge"><?php echo $stats['fans']; ?></span><?php endif; ?>
                </a>
                <a href="?tab=messages" class="tab-btn <?php echo $tab === 'messages' ? 'active' : ''; ?>">
                    ✉️ <?php echo e('私信'); ?>
                    <?php if ($stats['unread_msg'] > 0): ?><span class="badge"><?php echo $stats['unread_msg']; ?></span><?php endif; ?>
                </a>
                <a href="?tab=followforum" class="tab-btn <?php echo $tab === 'followforum' ? 'active' : ''; ?>">
                    📌 <?php echo e('关注版块'); ?>
                    <?php if ($stats['follow_boards'] > 0): ?><span class="badge"><?php echo $stats['follow_boards']; ?></span><?php endif; ?>
                </a>
            </div>

            <!-- 个人资料（只读显示） -->
            <?php if ($tab === 'profile'): ?>
            <div class="panel">
                <div class="panel-header">
                    <h3>👤 <?php echo e('基本信息'); ?></h3>
                </div>
                <div class="panel-body">
                    <!-- 用户信息卡片 -->
                    <div style="display: flex; align-items: flex-start; gap: 30px; padding: 20px; background: #f8f9fa; border-radius: 12px; margin-bottom: 20px;">
                        <img src="<?php echo e($user['ll_img'] ?: '/images/logo.png'); ?>" 
                             style="width: 120px; height: 120px; border-radius: 50%; object-fit: cover; border: 4px solid #fff; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                        <div style="flex: 1;">
                            <h2 style="margin: 0 0 10px; color: #333;"><?php echo e($user['ll_n_name'] ?: '未设置昵称'); ?></h2>
                            <p style="margin: 0 0 8px; color: #666;"><?php echo e($user['ll_sign'] ?: '这个人很懒，什么都没写~'); ?></p>
                            <div style="display: flex; gap: 20px; margin-top: 15px; flex-wrap: wrap;">
                                <span style="color: #f39c12;">⭐ Lv.<?php echo $level; ?> <?php echo e($levelName); ?></span>
                                <span style="color: #27ae60;">💰 <?php echo number_format($user['ll_mm'] ?? 0); ?> <?php echo e('金币'); ?></span>
                                <?php if (!empty($user['ll_sex'])): ?>
                                <span>⚧ <?php echo e($user['ll_sex']); ?></span>
                                <?php endif; ?>
                            </div>
                        </div>
                    </div>
                    
                    <!-- 详细信息列表 -->
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 15px;">
                        <div style="padding: 15px; background: #fff; border-radius: 8px; border: 1px solid #eee;">
                            <div style="color: #999; font-size: 12px; margin-bottom: 5px;"><?php echo e('用户名'); ?></div>
                            <div style="color: #333; font-weight: 500;"><?php echo e($user['ll_name']); ?></div>
                        </div>
                        <div style="padding: 15px; background: #fff; border-radius: 8px; border: 1px solid #eee;">
                            <div style="color: #999; font-size: 12px; margin-bottom: 5px;"><?php echo e('注册时间'); ?></div>
                            <div style="color: #333; font-weight: 500;"><?php echo e($user['ll_firsttime']); ?></div>
                        </div>
                        <div style="padding: 15px; background: #fff; border-radius: 8px; border: 1px solid #eee;">
                            <div style="color: #999; font-size: 12px; margin-bottom: 5px;"><?php echo e('生日'); ?></div>
                            <div style="color: #333; font-weight: 500;"><?php echo e(substr($user['ll_birthday'] ?? '', 0, 10)) ?: '未设置'; ?></div>
                        </div>
                        <div style="padding: 15px; background: #fff; border-radius: 8px; border: 1px solid #eee;">
                            <div style="color: #999; font-size: 12px; margin-bottom: 5px;"><?php echo e('手机'); ?></div>
                            <div style="color: #333; font-weight: 500;"><?php if (!empty($user['ll_shouji'])) { echo e(substr($user['ll_shouji'], 0, 3) . '****' . substr($user['ll_shouji'], -4)); } else { echo '<span style="color: #999;">' . e('未绑定') . '</span>'; } ?></div>
                        </div>
                    </div>
                    
                    <!-- 统计数据 -->
                    <div style="margin-top: 25px;">
                        <h4 style="color: #333; margin-bottom: 15px;">📊 <?php echo e('我的数据'); ?></h4>
                        <div style="display: flex; gap: 15px; flex-wrap: wrap;">
                            <div style="flex: 1; min-width: 100px; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; text-align: center; color: #fff;">
                                <div style="font-size: 28px; font-weight: bold;"><?php echo number_format($stats['topics']); ?></div>
                                <div style="font-size: 12px; opacity: 0.9;"><?php echo e('发帖数'); ?></div>
                            </div>
                            <div style="flex: 1; min-width: 100px; padding: 20px; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); border-radius: 12px; text-align: center; color: #fff;">
                                <div style="font-size: 28px; font-weight: bold;"><?php echo number_format($stats['replies']); ?></div>
                                <div style="font-size: 12px; opacity: 0.9;"><?php echo e('回帖数'); ?></div>
                            </div>
                            <div style="flex: 1; min-width: 100px; padding: 20px; background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); border-radius: 12px; text-align: center; color: #fff;">
                                <div style="font-size: 28px; font-weight: bold;"><?php echo number_format($stats['favorites']); ?></div>
                                <div style="font-size: 12px; opacity: 0.9;"><?php echo e('收藏数'); ?></div>
                            </div>
                            <div style="flex: 1; min-width: 100px; padding: 20px; background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); border-radius: 12px; text-align: center; color: #fff;">
                                <div style="font-size: 28px; font-weight: bold;"><?php echo number_format($stats['comments']); ?></div>
                                <div style="font-size: 12px; opacity: 0.9;"><?php echo e('评论数'); ?></div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- 背景音乐播放器 -->
                    <?php if (!empty($user['ll_bgm'])):
                        $bgmExt = strtolower(pathinfo($user['ll_bgm'], PATHINFO_EXTENSION));
                        $mimeType = match($bgmExt) {
                            'mp3' => 'audio/mpeg',
                            'wav' => 'audio/wav',
                            'ogg' => 'audio/ogg',
                            'm4a' => 'audio/mp4',
                            default => 'audio/mpeg'
                        };
                    ?>
                    <div class="panel" style="margin-top: 20px;">
                        <div class="panel-header">
                            <h3>🎵 <?php echo e('我的背景音乐'); ?></h3>
                        </div>
                        <div class="panel-body">
                            <audio id="bgmPlayerProfile" loop style="width: 100%; height: 40px;">
                                <source src="<?php echo e($user['ll_bgm']); ?>" type="<?php echo $mimeType; ?>">
                            </audio>
                            <div style="margin-top: 10px;">
                                <button type="button" onclick="playBgmP()" class="btn-sm btn-success" id="playBtnP">▶ <?php echo e('播放音乐'); ?></button>
                                <button type="button" onclick="pauseBgmP()" class="btn-sm btn-secondary" id="pauseBtnP" style="display:none;">⏸ <?php echo e('暂停'); ?></button>
                                <span id="bgmStatusP" style="margin-left: 10px; color: #666;"></span>
                            </div>
                            <script>
                            var bgmP = document.getElementById('bgmPlayerProfile');
                            bgmP.volume = 0.5;
                            bgmP.addEventListener('play', function() {
                                document.getElementById('playBtnP').style.display = 'none';
                                document.getElementById('pauseBtnP').style.display = 'inline-block';
                                document.getElementById('bgmStatusP').textContent = '🎵 ' + (window.UC_I18N ? UC_I18N.playing : '');
                            });
                            bgmP.addEventListener('pause', function() {
                                document.getElementById('playBtnP').style.display = 'inline-block';
                                document.getElementById('pauseBtnP').style.display = 'none';
                                document.getElementById('bgmStatusP').textContent = '⏸ ' + (window.UC_I18N ? UC_I18N.paused : '');
                            });
                            bgmP.addEventListener('ended', function() { this.currentTime = 0; this.play(); });
                            function playBgmP() { bgmP.play().then(function(){}).catch(function(e){}); }
                            function pauseBgmP() { bgmP.pause(); }
                            // 点击页面任意位置自动播放
                            document.addEventListener('click', function() { playBgmP(); }, {once: true});
                            </script>
                        </div>
                    </div>
                    <?php endif; ?>
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <a href="?tab=edit" class="btn btn-primary" style="padding: 12px 40px; font-size: 16px;">✏️ <?php echo e('编辑我的资料'); ?></a>
                    </div>
                </div>
            </div>
            <?php endif; ?>

            <!-- 编辑资料 -->
            <?php if ($tab === 'edit'): ?>
            <div class="panel">
                <div class="panel-header">
                    <h3>✏️ <?php echo e('编辑资料'); ?></h3>
                </div>
                <div class="panel-body">
                    <!-- 返回按钮 -->
                    <div style="margin-bottom: 20px;">
                        <a href="?tab=profile" style="color: #666; text-decoration: none;">← <?php echo e('返回个人资料'); ?></a>
                    </div>
                    
                    <!-- 修改头像 -->
                    <div class="edit-form">
                        <h4>🎨 <?php echo e('修改头像'); ?></h4>
                        <form method="post" enctype="multipart/form-data">
                            <input type="hidden" name="action" value="update_avatar">
                            <div style="display: flex; align-items: flex-start; gap: 20px; flex-wrap: wrap;">
                                <!-- 当前头像预览 -->
                                <div style="text-align: center;">
                                    <img src="<?php echo e($user['ll_img'] ?: '/images/logo.png'); ?>" 
                                         id="avatarPreview" 
                                         style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover; border: 3px solid #ddd;">
                                    <p style="margin: 10px 0 5px; color: #666; font-size: 12px;"><?php echo e('当前头像'); ?></p>
                                </div>
                                <!-- 上传选项 -->
                                <div style="flex: 1; min-width: 280px;">
                                    <div style="margin-bottom: 15px;">
                                        <label style="display: block; margin-bottom: 8px; font-weight: bold;">📤 <?php echo e('上传头像图片'); ?></label>
                                        <input type="file" name="avatar_file" id="avatarFile" accept="image/jpeg,image/png,image/gif,image/webp" 
                                               style="padding: 8px; border: 1px solid #ddd; border-radius: 4px; width: 100%;">
                                        <p style="margin: 5px 0 0; color: #888; font-size: 12px;"><?php echo e('支持 JPG/PNG/GIF/WebP，不超过 2MB'); ?></p>
                                    </div>
                                    <div style="margin-bottom: 15px; text-align: center; color: #999;">— <?php echo e('或'); ?> —</div>
                                    <div>
                                        <label style="display: block; margin-bottom: 8px; font-weight: bold;">🔗 <?php echo e('输入头像URL'); ?></label>
                                        <input type="text" name="avatar" id="avatarUrl" value="<?php echo e($user['ll_img'] ?? ''); ?>" 
                                               placeholder="<?php echo e('输入图片URL地址'); ?>" style="width: 100%;">
                                    </div>
                                    <button type="submit" class="btn btn-primary" style="margin-top: 15px;">💾 <?php echo e('保存头像'); ?></button>
                                </div>
                            </div>
                        </form>
                        <!-- 头像预览JS -->
                        <script>
                        document.getElementById('avatarFile').addEventListener('change', function(e) {
                            var file = e.target.files[0];
                            if (file) {
                                // 预览头像
                                var reader = new FileReader();
                                reader.onload = function(e) {
                                    document.getElementById('avatarPreview').src = e.target.result;
                                };
                                reader.readAsDataURL(file);
                                // 清空URL输入框（避免冲突，优先使用上传文件）
                                document.getElementById('avatarUrl').value = '';
                                // 显示提示
                                var tip = document.getElementById('avatarUploadTip');
                                if (tip) tip.remove();
                                var p = document.createElement('p');
                                p.id = 'avatarUploadTip';
                                p.style.cssText = 'margin: 5px 0 0; color: #4CAF50; font-size: 12px;';
                                p.textContent = '✅ 已选择文件，点击下方"保存头像"按钮即可上传';
                                document.getElementById('avatarFile').parentNode.appendChild(p);
                            }
                        });
                        </script>
                    </div>

                    <!-- 修改昵称 -->
                    <div class="edit-form">
                        <h4>✏️ <?php echo e('修改昵称'); ?></h4>
                        <form method="post">
                            <input type="hidden" name="action" value="update_nickname">
                            <div class="form-row">
                                <label><?php echo e('昵称:'); ?></label>
                                <input type="text" name="nickname" value="<?php echo e($user['ll_n_name'] ?? ''); ?>" placeholder="<?php echo e('最多20个字符'); ?>" maxlength="20">
                                <button type="submit" class="btn-sm btn-primary"><?php echo e('保存'); ?></button>
                            </div>
                        </form>
                    </div>

                    <!-- 修改个人签名 -->
                    <div class="edit-form">
                        <h4>📝 <?php echo e('个人签名/简介'); ?></h4>
                        <form method="post">
                            <input type="hidden" name="action" value="update_sign">
                            <div class="form-row" style="flex-wrap: wrap;">
                                <label style="width: 100%; margin-bottom: 8px;"><?php echo e('签名:'); ?></label>
                                <textarea name="sign" placeholder="<?php echo e('介绍一下自己吧~'); ?>" style="width: 100%; max-width: 400px; height: 80px; padding: 10px; border: 1px solid #ddd; border-radius: 4px; resize: vertical;" maxlength="100"><?php echo e($user['ll_sign'] ?? ''); ?></textarea>
                                <button type="submit" class="btn-sm btn-primary" style="margin-top: 10px;"><?php echo e('保存'); ?></button>
                            </div>
                        </form>
                    </div>

                    <!-- 修改性别 -->
                    <div class="edit-form">
                        <h4>⚧ <?php echo e('修改性别'); ?></h4>
                        <form method="post">
                            <input type="hidden" name="action" value="update_sex">
                            <div class="form-row">
                                <label><?php echo e('性别:'); ?></label>
                                <select name="sex">
                                    <option value=""><?php echo e('未设置'); ?></option>
                                    <option value="男" <?php echo ($user['ll_sex'] ?? '') === '男' ? 'selected' : ''; ?>><?php echo e('男'); ?></option>
                                    <option value="女" <?php echo ($user['ll_sex'] ?? '') === '女' ? 'selected' : ''; ?>><?php echo e('女'); ?></option>
                                </select>
                                <button type="submit" class="btn-sm btn-primary"><?php echo e('保存'); ?></button>
                            </div>
                        </form>
                    </div>

                    <!-- 修改生日 -->
                    <div class="edit-form">
                        <h4>🎂 <?php echo e('修改生日'); ?></h4>
                        <form method="post">
                            <input type="hidden" name="action" value="update_birthday">
                            <div class="form-row">
                                <label><?php echo e('生日:'); ?></label>
                                <input type="date" name="birthday" value="<?php echo e(substr($user['ll_birthday'] ?? '', 0, 10)); ?>">
                                <button type="submit" class="btn-sm btn-primary"><?php echo e('保存'); ?></button>
                            </div>
                        </form>
                    </div>

                    <!-- 修改登录密码 -->
                    <div class="edit-form">
                        <h4>🔐 <?php echo e('修改登录密码'); ?></h4>
                        <form method="post" onsubmit="return validatePasswordForm(this);">
                            <input type="hidden" name="action" value="update_password">
                            <div style="max-width: 400px;">
                                <div class="form-row" style="flex-wrap: wrap; gap: 10px;">
                                    <label style="width: 100%; margin-bottom: 5px;"><?php echo e('原密码:'); ?></label>
                                    <input type="password" name="old_password" id="oldPwd" placeholder="<?php echo e('请输入原密码'); ?>" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px;" required>
                                </div>
                                <div class="form-row" style="flex-wrap: wrap; gap: 10px; margin-top: 15px;">
                                    <label style="width: 100%; margin-bottom: 5px;"><?php echo e('新密码:'); ?></label>
                                    <input type="password" name="new_password" id="newPwd" placeholder="<?php echo e('请输入新密码(6-20位)'); ?>" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px;" required minlength="6" maxlength="20">
                                </div>
                                <div class="form-row" style="flex-wrap: wrap; gap: 10px; margin-top: 15px;">
                                    <label style="width: 100%; margin-bottom: 5px;"><?php echo e('确认新密码:'); ?></label>
                                    <input type="password" name="confirm_password" id="confirmPwd" placeholder="<?php echo e('请再次输入新密码'); ?>" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px;" required minlength="6" maxlength="20">
                                </div>
                                <div style="margin-top: 15px;">
                                    <button type="submit" class="btn btn-primary">💾 <?php echo e('修改密码'); ?></button>
                                </div>
                            </div>
                        </form>
                        <script>
                        function validatePasswordForm(form) {
                            var newPwd = form.new_password.value;
                            var confirmPwd = form.confirm_password.value;
                            if (newPwd.length < 6) {
                                alert(window.UC_I18N ? UC_I18N.pwdShort : '');
                                return false;
                            }
                            if (newPwd !== confirmPwd) {
                                alert(window.UC_I18N ? UC_I18N.pwdMismatch : '');
                                return false;
                            }
                            return true;
                        }
                        </script>
                    </div>

                    <!-- 手机绑定 -->
                    <div class="edit-form">
                        <h4>📱 <?php echo e('手机绑定'); ?></h4>
                        <?php if (!empty($user['ll_shouji'])): ?>
                        <div style="display: flex; align-items: center; gap: 15px;">
                            <span style="color: #27ae60;">✅ <?php echo e('已绑定手机'); ?>：<?php echo substr($user['ll_shouji'], 0, 3) . '****' . substr($user['ll_shouji'], -4); ?></span>
                            <button type="button" class="btn-sm btn-secondary" onclick="document.getElementById('bindPhoneForm').style.display='block';this.style.display='none';"><?php echo e('更换手机'); ?></button>
                        </div>
                        <div id="bindPhoneForm" style="display: none; margin-top: 15px;">
                            <form method="post">
                                <input type="hidden" name="action" value="bind_phone">
                                <div class="form-row">
                                    <label><?php echo e('新手机:'); ?></label>
                                    <input type="text" name="phone" placeholder="<?php echo e('请输入新手机号'); ?>" maxlength="11">
                                    <button type="submit" class="btn-sm btn-primary"><?php echo e('绑定'); ?></button>
                                </div>
                            </form>
                        </div>
                        <?php else: ?>
                        <form method="post">
                            <input type="hidden" name="action" value="bind_phone">
                            <div class="form-row">
                                <label><?php echo e('手机号:'); ?></label>
                                <input type="text" name="phone" placeholder="<?php echo e('请输入手机号'); ?>" maxlength="11">
                                <button type="submit" class="btn-sm btn-primary"><?php echo e('绑定'); ?></button>
                            </div>
                        </form>
                        <?php endif; ?>
                    </div>

                    <!-- 背景图片 -->
                    <div class="edit-form">
                        <h4>🖼️ <?php echo e('个人背景图片'); ?></h4>
                        <?php if (!empty($user['ll_beijing'])): ?>
                        <div style="margin-bottom: 15px;">
                            <img src="<?php echo e($user['ll_beijing']); ?>" style="width: 100%; max-height: 150px; object-fit: cover; border-radius: 8px;">
                        </div>
                        <?php endif; ?>
                        <form method="post" enctype="multipart/form-data">
                            <input type="hidden" name="action" value="update_background">
                            <div class="form-row" style="flex-wrap: wrap; gap: 10px;">
                                <input type="file" name="background_file" accept="image/*" style="flex: 1; min-width: 200px;">
                                <button type="submit" class="btn-sm btn-primary"><?php echo e('上传'); ?></button>
                            </div>
                            <div style="margin-top: 10px; color: #999; font-size: 12px;"><?php echo e('支持 JPG/PNG/GIF/WebP，最大 5MB'); ?></div>
                            <?php if (!empty($user['ll_beijing'])): ?>
                            <div style="margin-top: 10px;">
                                <form method="post" style="display:inline;">
                                    <input type="hidden" name="action" value="clear_bg">
                                    <button type="submit" class="btn-sm btn-danger" onclick="return confirm(window.UC_I18N ? UC_I18N.confirmClearBg : '');"><?php echo e('清除背景'); ?></button>
                                </form>
                            </div>
                            <?php endif; ?>
                        </form>
                    </div>

                    <!-- 背景音乐 -->
                    <div class="edit-form">
                        <h4>🎵 <?php echo e('背景音乐'); ?></h4>
                        <?php if (!empty($user['ll_bgm'])): 
                            $bgmExt = strtolower(pathinfo($user['ll_bgm'], PATHINFO_EXTENSION));
                            $mimeType = match($bgmExt) {
                                'mp3' => 'audio/mpeg',
                                'wav' => 'audio/wav',
                                'ogg' => 'audio/ogg',
                                'm4a' => 'audio/mp4',
                                default => 'audio/mpeg'
                            };
                        ?>
                        <div style="margin-bottom: 15px;">
                            <audio id="bgmPlayer" loop style="width: 100%; height: 40px;">
                                <source src="<?php echo e($user['ll_bgm']); ?>" type="<?php echo $mimeType; ?>">
                                <?php echo e('您的浏览器不支持音频播放'); ?>
                            </audio>
                            <div style="margin-top: 8px; font-size: 12px; color: #666;">
                                <button type="button" onclick="playBgm()" class="btn-sm btn-success" id="playBtn">▶ <?php echo e('播放音乐'); ?></button>
                                <button type="button" onclick="pauseBgm()" class="btn-sm btn-secondary" id="pauseBtn" style="display:none;">⏸ <?php echo e('暂停'); ?></button>
                                <span id="bgmStatus" style="margin-left: 10px; color: #999;"></span>
                            </div>
                        </div>
                        <script>
                        var bgm = document.getElementById('bgmPlayer');
                        var playBtn = document.getElementById('playBtn');
                        var pauseBtn = document.getElementById('pauseBtn');
                        var status = document.getElementById('bgmStatus');
                        
                        bgm.volume = 0.5;
                        bgm.addEventListener('play', function() {
                            playBtn.style.display = 'none';
                            pauseBtn.style.display = 'inline-block';
                            status.textContent = '🎵 ' + (window.UC_I18N ? UC_I18N.playing : '');
                        });
                        
                        bgm.addEventListener('pause', function() {
                            playBtn.style.display = 'inline-block';
                            pauseBtn.style.display = 'none';
                            status.textContent = '⏸ ' + (window.UC_I18N ? UC_I18N.paused : '');
                        });
                        
                        bgm.addEventListener('ended', function() {
                            bgm.currentTime = 0;
                            bgm.play();
                        });
                        
                        function playBgm() {
                            bgm.play().then(function() {
                                playBtn.style.display = 'none';
                                pauseBtn.style.display = 'inline-block';
                                status.textContent = '🎵 ' + (window.UC_I18N ? UC_I18N.playing : '');
                            }).catch(function(e) {
                                status.textContent = window.UC_I18N ? UC_I18N.clickPlay : '';
                            });
                        }
                        
                        function pauseBgm() {
                            bgm.pause();
                        }
                        // 点击页面任意位置自动播放
                        document.addEventListener('click', function() { playBgm(); }, {once: true});
                        </script>
                        <?php endif; ?>
                        <form method="post" enctype="multipart/form-data">
                            <input type="hidden" name="action" value="update_bgm">
                            <div class="form-row" style="flex-wrap: wrap; gap: 10px;">
                                <input type="file" name="bgm_file" accept="audio/mp3,audio/mpeg,audio/wav,audio/ogg,.mp3,.wav,.ogg,.m4a" style="flex: 1; min-width: 200px;">
                                <button type="submit" class="btn-sm btn-primary"><?php echo e('上传'); ?></button>
                            </div>
                            <div style="margin-top: 10px; color: #999; font-size: 12px;"><?php echo e('支持 MP3/WAV/OGG/M4A，最大 10MB'); ?></div>
                        </form>
                        <?php if (!empty($user['ll_bgm'])): ?>
                        <div style="margin-top: 10px;">
                            <form method="post" style="display:inline;">
                                <input type="hidden" name="action" value="clear_bgm">
                                <button type="submit" class="btn-sm btn-danger" onclick="return confirm(window.UC_I18N ? UC_I18N.confirmClearBgm : '');"><?php echo e('清除音乐'); ?></button>
                            </form>
                        </div>
                        <?php endif; ?>
                    </div>
                </div>
            </div>
            <?php endif; ?>

            <!-- 实名认证 -->
            <?php if ($tab === 'verify'): ?>
            <div class="panel">
                <div class="panel-header">
                    <h3>🪪 <?php echo e('实名认证'); ?></h3>
                </div>
                <div class="panel-body">
                    <?php if ($verifyStatus === 1): ?>
                        <!-- 已认证 -->
                        <div style="text-align: center; padding: 40px;">
                            <div style="font-size: 60px; margin-bottom: 20px;">✅</div>
                            <h2><?php echo e('已通过实名认证'); ?></h2>
                            <p style="color: #666; margin: 15px 0;">
                                <?php echo e('姓名'); ?>：<strong><?php echo e($verification['real_name'] ?? ''); ?></strong><br>
                                <?php echo e('身份证'); ?>：<strong><?php echo e(substr($verification['id_card'] ?? '', 0, 3) . '****' . substr($verification['id_card'] ?? '', -4)); ?></strong><br>
                                <?php echo e('手机'); ?>：<strong><?php echo e(substr($verification['phone'] ?? '', 0, 3) . '****' . substr($verification['phone'] ?? '', -4)); ?></strong>
                            </p>
                            <p style="color: #27ae60;"><?php echo e('您现在可以参与现金任务了！'); ?></p>
                        </div>
                    <?php elseif ($verifyStatus === 0): ?>
                        <!-- 审核中 -->
                        <div style="text-align: center; padding: 40px;">
                            <div style="font-size: 60px; margin-bottom: 20px;">⏳</div>
                            <h2><?php echo e('认证审核中'); ?></h2>
                            <p style="color: #666; margin: 15px 0;">
                                <?php echo e('姓名'); ?>：<strong><?php echo e($verification['real_name'] ?? ''); ?></strong><br>
                                <?php echo e('提交时间'); ?>：<strong><?php echo e($verification['submitted_at'] ?? ''); ?></strong>
                            </p>
                            <p style="color: #f39c12;"><?php echo e('您的认证信息正在审核中，请耐心等待。'); ?></p>
                        </div>
                    <?php elseif ($verifyStatus === 2): ?>
                        <!-- 已拒绝 -->
                        <div style="text-align: center; padding: 40px;">
                            <div style="font-size: 60px; margin-bottom: 20px;">❌</div>
                            <h2><?php echo e('认证未通过'); ?></h2>
                            <?php if (!empty($verification['reject_reason'])): ?>
                            <p style="color: #e74c3c; margin: 15px 0;"><?php echo e('拒绝原因'); ?>：<?php echo e($verification['reject_reason']); ?></p>
                            <?php endif; ?>
                            <p style="color: #666;"><?php echo e('您可以重新提交认证信息。'); ?></p>
                        </div>
                        <!-- 重新提交表单 -->
                        <div class="edit-form" style="margin-top: 20px;">
                            <h4><?php echo e('重新提交认证'); ?></h4>
                            <form method="post">
                                <input type="hidden" name="action" value="submit_verification">
                                <div style="display: grid; gap: 15px; max-width: 400px;">
                                    <div>
                                        <label style="display: block; margin-bottom: 5px; font-weight: bold;"><?php echo e('真实姓名'); ?></label>
                                        <input type="text" name="real_name" required maxlength="20" 
                                               placeholder="<?php echo e('请输入真实姓名'); ?>" style="width: 100%;">
                                    </div>
                                    <div>
                                        <label style="display: block; margin-bottom: 5px; font-weight: bold;"><?php echo e('身份证号码'); ?></label>
                                        <input type="text" name="id_card" required maxlength="18" 
                                               placeholder="<?php echo e('请输入18位身份证号码'); ?>" style="width: 100%;">
                                    </div>
                                    <div>
                                        <label style="display: block; margin-bottom: 5px; font-weight: bold;"><?php echo e('手机号码'); ?></label>
                                        <input type="text" name="phone" required maxlength="11" 
                                               placeholder="<?php echo e('请输入手机号码'); ?>" style="width: 100%;">
                                    </div>
                                    <button type="submit" class="btn btn-primary"><?php echo e('提交认证'); ?></button>
                                </div>
                            </form>
                        </div>
                    <?php else: ?>
                        <!-- 未认证 - 提交表单 -->
                        <div style="margin-bottom: 20px; padding: 15px; background: #fff3cd; border-radius: 8px; border: 1px solid #ffc107;">
                            <strong>⚠️ <?php echo e('提示'); ?>：</strong><?php echo e('参与现金任务需要完成实名认证。您的信息仅用于身份验证，不会被公开。'); ?>
                        </div>
                        <div class="edit-form">
                            <h4><?php echo e('提交实名认证'); ?></h4>
                            <form method="post">
                                <input type="hidden" name="action" value="submit_verification">
                                <div style="display: grid; gap: 15px; max-width: 400px;">
                                    <div>
                                        <label style="display: block; margin-bottom: 5px; font-weight: bold;"><?php echo e('真实姓名'); ?></label>
                                        <input type="text" name="real_name" required maxlength="20" 
                                               placeholder="<?php echo e('请输入真实姓名'); ?>" style="width: 100%;">
                                    </div>
                                    <div>
                                        <label style="display: block; margin-bottom: 5px; font-weight: bold;"><?php echo e('身份证号码'); ?></label>
                                        <input type="text" name="id_card" required maxlength="18" 
                                               placeholder="<?php echo e('请输入18位身份证号码'); ?>" style="width: 100%;">
                                    </div>
                                    <div>
                                        <label style="display: block; margin-bottom: 5px; font-weight: bold;"><?php echo e('手机号码'); ?></label>
                                        <input type="text" name="phone" required maxlength="11" 
                                               placeholder="<?php echo e('请输入手机号码'); ?>" style="width: 100%;"
                                               value="<?php echo e($user['ll_shouji'] ?? ''); ?>">
                                    </div>
                                    <button type="submit" class="btn btn-primary"><?php echo e('提交认证'); ?></button>
                                </div>
                            </form>
                        </div>
                    <?php endif; ?>
                </div>
            </div>
            <?php endif; ?>

            <!-- 每日签到 -->
            <?php if ($tab === 'signin'): ?>
            <div class="panel">
                <div class="panel-header">
                    <h3>🎁 <?php echo e('每日签到'); ?></h3>
                </div>
                <div class="panel-body" style="text-align: center; padding: 40px;">
                    <?php if ($todaySign): ?>
                        <div style="font-size: 60px; margin-bottom: 20px;">✅</div>
                        <h2><?php echo e('今日已签到'); ?></h2>
                        <p style="color: #666; margin: 15px 0;"><?php echo e('连续签到'); ?> <strong style="color: #667eea;"><?php echo $todaySign['ll_liandai']; ?></strong> <?php echo e('天'); ?></p>
                        <p style="color: #666;"><?php echo e('本次获得'); ?> <strong style="color: #f39c12;"><?php echo $todaySign['ll_jinbi']; ?></strong> <?php echo e('金币'); ?></p>
                    <?php else: ?>
                        <div style="font-size: 60px; margin-bottom: 20px;">🎁</div>
                        <h2><?php echo e('每日签到领金币'); ?></h2>
                        <p style="color: #666;"><?php echo e('连续签到额外奖励：7天=20金币，30天=50金币'); ?></p>
                        <form method="post">
                            <input type="hidden" name="action" value="signin">
                            <button type="submit" class="sign-btn"><?php echo e('立即签到'); ?></button>
                        </form>
                    <?php endif; ?>
                    <div class="sign-info">
                        <?php echo e('历史最高连续签到'); ?>: <strong><?php echo $stats['sign_days']; ?></strong> <?php echo e('天'); ?>
                    </div>
                </div>
            </div>
            <?php endif; ?>

            <!-- 每日任务 -->
            <?php if ($tab === 'tasks'): ?>
            <div class="panel">
                <div class="panel-header">
                    <h3>🎯 <?php echo e('每日任务'); ?></h3>
                </div>
                <div class="panel-body" style="padding: 20px;">
                    <p style="color: #666; margin-bottom: 20px;"><?php echo e('每日完成任务可获得金币奖励，凌晨0点重置'); ?></p>
                    <div class="task-list">
                        <?php foreach ($taskList as $task): ?>
                        <div class="task-item <?php echo $task['done'] ? 'done' : ''; ?>">
                            <div class="task-icon"><?php echo $task['done'] ? '✅' : '⬜'; ?></div>
                            <div class="task-info">
                                <div class="task-name"><?php echo e($task['name']); ?></div>
                                <div class="task-desc"><?php echo e($task['desc']); ?></div>
                            </div>
                            <div class="task-reward">
                                +<?php echo $task['reward']; ?> 💰
                            </div>
                            <div class="task-action">
                                <?php if ($task['done']): ?>
                                    <span class="task-done-tag"><?php echo e('已完成'); ?></span>
                                <?php elseif ($task['id'] === 'signin'): ?>
                                    <a href="?tab=signin" class="btn-sm btn-primary"><?php echo e('去签到'); ?></a>
                                <?php elseif ($task['id'] === 'forum'): ?>
                                    <a href="post.php" class="btn-sm btn-primary"><?php echo e('去发帖'); ?></a>
                                <?php elseif ($task['id'] === 'download'): ?>
                                    <a href="/" class="btn-sm btn-primary"><?php echo e('去下载'); ?></a>
                                <?php elseif ($task['id'] === 'comment'): ?>
                                    <a href="/" class="btn-sm btn-primary"><?php echo e('去评论'); ?></a>
                                <?php elseif ($task['id'] === 'share'): ?>
                                    <a href="/" class="btn-sm btn-primary"><?php echo e('去分享'); ?></a>
                                <?php endif; ?>
                            </div>
                        </div>
                        <?php endforeach; ?>
                    </div>
                    <?php
                    $completedCount = count(array_filter($taskList, fn($t) => $t['done']));
                    $totalReward = array_sum(array_column($taskList, 'reward'));
                    $earnedReward = array_sum(array_column(array_filter($taskList, fn($t) => $t['done']), 'reward'));
                    ?>
                    <div class="task-summary">
                        <div class="task-progress">
                            <?php echo e('今日进度'); ?>: <strong><?php echo $completedCount; ?>/<?php echo count($taskList); ?></strong>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: <?php echo round($completedCount / count($taskList) * 100); ?>%"></div>
                            </div>
                        </div>
                        <div class="task-rewards">
                            <?php echo e('今日可获'); ?>: <strong><?php echo $totalReward; ?></strong> <?php echo e('金币'); ?> | 
                            <?php echo e('已获得'); ?>: <strong style="color: #f39c12;"><?php echo $earnedReward; ?></strong> <?php echo e('金币'); ?>
                        </div>
                    </div>
                </div>
            </div>
            <?php endif; ?>

            <!-- 我的帖子 -->
            <?php if ($tab === 'topics'): ?>
            <?php 
            // 获取子排序类型：latest 或 hot
            $sortType = $_GET['sort'] ?? 'latest';
            ?>
            <div class="panel">
                <div class="panel-header" style="display: flex; justify-content: space-between; align-items: center;">
                    <h3>📝 <?php echo e('我的帖子'); ?> (<?php echo $stats['topics']; ?>)</h3>
                    <div class="sub-tabs">
                        <a href="?tab=topics&sort=latest" class="sub-tab <?php echo $sortType === 'latest' ? 'active' : ''; ?>">📋 <?php echo e('最新'); ?></a>
                        <a href="?tab=topics&sort=hot" class="sub-tab <?php echo $sortType === 'hot' ? 'active' : ''; ?>">🔥 <?php echo e('最热'); ?></a>
                    </div>
                </div>
                <div class="panel-body">
                    <?php if (empty($myTopics)): ?>
                    <div class="empty-tip"><?php echo e('暂无帖子'); ?>，<a href="post.php"><?php echo e('发布第一个'); ?></a></div>
                    <?php else: ?>
                    <ul class="topic-list" id="topics-list">
                        <?php foreach ($myTopics as $topic): ?>
                        <li class="topic-item">
                            <a href="<?php echo bbsUrl('topic', $topic['id']); ?>" class="topic-title"><?php echo e($topic['ll_biaoti']); ?></a>
                            <div class="topic-meta">
                                <span><?php echo $sortType === 'hot' ? '<span style="color: #e74c3c;">🔥</span> ' . (int)($topic['ll_rchf'] ?? 0) : (int)($topic['reply_count'] ?? 0); ?> <?php echo e('回复'); ?></span>
                                <span><?php echo (int)($topic['ll_rc'] ?? 0); ?> <?php echo e('浏览'); ?></span>
                                <span><?php echo formatTime($topic['ll_time1']); ?></span>
                            </div>
                        </li>
                        <?php endforeach; ?>
                    </ul>
                    <?php if ($stats['topics'] > $pageSize): ?>
                    <div id="loading-tip" style="text-align: center; padding: 20px; color: #888;">
                        <span id="load-text"><?php echo e('上拉加载更多...'); ?></span>
                    </div>
                    <?php endif; ?>
                    <?php endif; ?>
                </div>
            </div>
            <?php endif; ?>



            <!-- 我的收藏 -->
            <?php if ($tab === 'favorites'): ?>
            <div class="panel">
                <div class="panel-header">
                    <h3>⭐ <?php echo e('我的收藏'); ?> (<?php echo $stats['favorites']; ?>)</h3>
                </div>
                <div class="panel-body">
                    <?php if (empty($favorites)): ?>
                    <div class="empty-tip"><?php echo e('暂无收藏'); ?></div>
                    <?php else: ?>
                    <?php foreach ($favorites as $fav): ?>
                    <div class="game-card">
                        <img src="<?php echo e($fav['ll_logo'] ? '../' . $fav['ll_logo'] : '/images/logo.png'); ?>" onerror="this.onerror=null;this.src='/images/logo.png';">
                        <div class="info">
                            <div class="name"><?php echo e($fav['ll_biaoti']); ?></div>
                            <div class="meta"><?php echo e('收藏于'); ?> <?php echo formatTime($fav['ll_retime']); ?></div>
                        </div>
                        <a href="<?php echo bbsUrl('topic', $fav['topic_id']); ?>" class="btn-sm btn-primary"><?php echo e('查看'); ?></a>
                        <form method="post" style="display:inline;">
                            <input type="hidden" name="action" value="del_favorite">
                            <input type="hidden" name="fid" value="<?php echo $fav['id']; ?>">
                            <button type="submit" class="btn-sm btn-danger" onclick="return confirm(window.UC_I18N ? UC_I18N.confirmUnfav : '')"><?php echo e('删除'); ?></button>
                        </form>
                    </div>
                    <?php endforeach; ?>
                    <?php endif; ?>
                </div>
            </div>
            <?php endif; ?>

            <!-- 下载记录 -->
            <?php if ($tab === 'downloads'): ?>
            <div class="panel">
                <div class="panel-header">
                    <h3>📥 <?php echo e('下载记录'); ?> (<?php echo $stats['downloads']; ?>)</h3>
                </div>
                <div class="panel-body">
                    <?php if (empty($downloads)): ?>
                    <div class="empty-tip"><?php echo e('暂无下载记录'); ?></div>
                    <?php else: ?>
                    <?php foreach ($downloads as $down): ?>
                    <div class="game-card">
                        <img src="<?php echo e($down['ll_logo'] ? '../' . $down['ll_logo'] : '/images/logo.png'); ?>" onerror="this.onerror=null;this.src='/images/logo.png';">
                        <div class="info">
                            <div class="name"><?php echo e($down['ll_biaoti']); ?></div>
                            <div class="meta"><?php echo e('版本'); ?>: <?php echo e($down['ll_banben']); ?> | <?php echo e('下载于'); ?> <?php echo formatTime($down['ll_retime']); ?></div>
                        </div>
                        <form method="post" style="display:inline;">
                            <input type="hidden" name="action" value="del_download">
                            <input type="hidden" name="did" value="<?php echo $down['id']; ?>">
                            <button type="submit" class="btn-sm btn-danger" onclick="return confirm(window.UC_I18N ? UC_I18N.confirmDel : '')"><?php echo e('删除'); ?></button>
                        </form>
                    </div>
                    <?php endforeach; ?>
                    <?php if ($totalPages > 1): ?>
                    <div class="pagination">
                        <?php for ($i = 1; $i <= min($totalPages, 5); $i++): ?>
                            <a href="?tab=downloads&page=<?php echo $i; ?>"><?php echo $i; ?></a>
                        <?php endfor; ?>
                    </div>
                    <?php endif; ?>
                    <?php endif; ?>
                </div>
            </div>
            <?php endif; ?>

            <!-- 我的评论 -->
            <?php if ($tab === 'comments'): ?>
            <div class="panel">
                <div class="panel-header">
                    <h3>🎮 <?php echo e('我的游戏评论'); ?> (<?php echo $stats['comments']; ?>)</h3>
                </div>
                <div class="panel-body">
                    <?php if (empty($comments)): ?>
                    <div class="empty-tip"><?php echo e('暂无游戏评论'); ?></div>
                    <?php else: ?>
                    <?php foreach ($comments as $comment): ?>
                    <div class="game-card">
                        <img src="<?php echo e($comment['ll_logo'] ? '../' . $comment['ll_logo'] : '/images/logo.png'); ?>" onerror="this.onerror=null;this.src='/images/logo.png';">
                        <div class="info">
                            <div class="name"><?php echo e($comment['ll_biaoti']); ?></div>
                            <div class="meta">💬 <?php echo e(mb_substr(strip_tags($comment['ll_text']), 0, 50)); ?>...</div>
                            <div class="meta">👍 <?php echo $comment['ll_zan']; ?> | <?php echo formatTime($comment['ll_time']); ?></div>
                        </div>
                    </div>
                    <?php endforeach; ?>
                    <?php if ($totalPages > 1): ?>
                    <div class="pagination">
                        <?php for ($i = 1; $i <= min($totalPages, 5); $i++): ?>
                            <a href="?tab=comments&page=<?php echo $i; ?>"><?php echo $i; ?></a>
                        <?php endfor; ?>
                    </div>
                    <?php endif; ?>
                    <?php endif; ?>
                </div>
            </div>
            <?php endif; ?>

            <!-- 我的回复 -->
            <?php if ($tab === 'replies'): ?>
            <?php 
            $replySort = $_GET['sort'] ?? 'latest';
            ?>
            <div class="panel">
                <div class="panel-header" style="display: flex; justify-content: space-between; align-items: center;">
                    <h3>💬 <?php echo e('我的社区回复'); ?> (<?php echo $stats['replies']; ?>)</h3>
                    <div class="sub-tabs">
                        <a href="?tab=replies&sort=latest" class="sub-tab <?php echo $replySort === 'latest' ? 'active' : ''; ?>">📋 <?php echo e('最新'); ?></a>
                        <a href="?tab=replies&sort=hot" class="sub-tab <?php echo $replySort === 'hot' ? 'active' : ''; ?>">👍 <?php echo e('点赞最多'); ?></a>
                    </div>
                </div>
                <div class="panel-body">
                    <?php if (empty($myReplies)): ?>
                    <div class="empty-tip"><?php echo e('暂无社区回复'); ?></div>
                    <?php else: ?>
                    <div id="replies-list">
                    <?php foreach ($myReplies as $reply): ?>
                    <div class="reply-item" style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                        <a href="<?php echo bbsUrl('topic', $reply['topic_id']); ?>" style="color: #667eea; font-weight: bold; text-decoration: none;">
                            <?php echo e($reply['topic_title'] ?? '未知帖子'); ?>
                        </a>
                        <p style="color: #666; margin: 10px 0; line-height: 1.5;">
                            <?php echo e(mb_substr(strip_tags($reply['ll_text']), 0, 100)); ?>...
                        </p>
                        <div style="font-size: 12px; color: #999;">
                            <?php if ($replySort === 'hot'): ?>
                            <span style="color: #e74c3c;">👍 <?php echo (int)$reply['ll_zan']; ?></span> |
                            <?php endif; ?>
                            <?php echo formatTime($reply['ll_time']); ?>
                        </div>
                    </div>
                    <?php endforeach; ?>
                    </div>
                    <?php if ($stats['replies'] > 10): ?>
                    <div id="loading-tip-replies" style="text-align: center; padding: 20px; color: #888;">
                        <span id="load-text-replies"><?php echo e('上拉加载更多...'); ?></span>
                    </div>
                    <?php endif; ?>
                    <?php endif; ?>
                </div>
            </div>
            <?php endif; ?>

            <!-- 好友列表 -->
            <?php if ($tab === 'friends'): ?>
            <style>
            .friends-container {
                display: flex;
                gap: 20px;
            }
            .friends-main {
                flex: 1;
            }
            .friends-sidebar {
                width: 300px;
            }
            @media (max-width: 768px) {
                .friends-container {
                    flex-direction: column;
                }
                .friends-sidebar {
                    width: 100%;
                }
            }
            </style>
            <div class="friends-container">
                <!-- 左侧：我的好友 -->
                <div class="friends-main">
                    <div class="panel">
                        <div class="panel-header">
                            <h3>👥 <?php echo e('我的好友'); ?> (<?php echo count($friends); ?>)</h3>
                        </div>
                        <div class="panel-body">
                            <?php if (empty($friends)): ?>
                            <div class="empty-tip"><?php echo e('暂无好友，快去社区认识新朋友吧！'); ?></div>
                            <?php else: ?>
                            <?php foreach ($friends as $friend): ?>
                            <div class="friend-item">
                                <a href="profile.php?id=<?php echo $friend['friend_id']; ?>">
                                    <img src="<?php echo e($friend['ll_img'] ?: '/images/logo.png'); ?>" onerror="this.onerror=null;this.src='/images/logo.png';">
                                    <div class="name">
                                        <?php echo e($friend['ll_n_name'] ?: $friend['ll_name'] ?: '用户' . $friend['friend_id']); ?>
                                        <div class="level">Lv.<?php echo $friend['ll_dj'] ?? 0; ?></div>
                                    </div>
                                </a>
                            </div>
                            <?php endforeach; ?>
                            <?php endif; ?>
                        </div>
                    </div>
                </div>
                <!-- 右侧：待验证好友请求 -->
                <div class="friends-sidebar">
                    <?php if (!empty($friendRequests)): ?>
                    <div class="panel">
                        <div class="panel-header">
                            <h3>⏳ <?php echo e('待验证好友请求'); ?> (<?php echo count($friendRequests); ?>)</h3>
                        </div>
                        <div class="panel-body">
                            <?php foreach ($friendRequests as $req): ?>
                            <div class="friend-item friend-request">
                                <a href="profile.php?id=<?php echo $req['requester_id']; ?>">
                                    <img src="<?php echo e($req['ll_img'] ?: '/images/logo.png'); ?>" onerror="this.onerror=null;this.src='/images/logo.png';">
                                    <div class="name">
                                        <?php echo e($req['ll_n_name'] ?: $req['ll_name'] ?: '用户' . $req['requester_id']); ?>
                                    </div>
                                </a>
                                <form method="post" style="display:inline;">
                                    <input type="hidden" name="action" value="friend_action">
                                    <input type="hidden" name="fid" value="<?php echo $req['id']; ?>">
                                    <input type="hidden" name="type" value="accept">
                                    <button type="submit" class="btn-sm btn-success"><?php echo e('同意'); ?></button>
                                </form>
                                <form method="post" style="display:inline;">
                                    <input type="hidden" name="action" value="friend_action">
                                    <input type="hidden" name="fid" value="<?php echo $req['id']; ?>">
                                    <input type="hidden" name="type" value="reject">
                                    <button type="submit" class="btn-sm btn-danger"><?php echo e('拒绝'); ?></button>
                                </form>
                            </div>
                            <?php endforeach; ?>
                        </div>
                    </div>
                    <?php endif; ?>
                </div>
            </div>
            <?php endif; ?>

            <!-- 私信 - 对话列表 -->
            <?php if ($tab === 'messages'): ?>
            <div class="panel">
                <div class="panel-header">
                    <h3>✉️ <?php echo e('私信对话'); ?> (<?php echo $totalConversations; ?>)</h3>
                </div>
                <div class="panel-body" style="padding: 0;">
                    <?php if (empty($conversations)): ?>
                    <div class="empty-tip" style="padding: 40px;"><?php echo e('暂无私信记录'); ?></div>
                    <?php else: ?>
                        <?php foreach ($conversations as $conv): 
                            $convLink = 'message.php?to=' . intval($conv['partner_id']);
                            $convImg = $conv['partner_img'] ?: '/bbs/images/default-avatar.png';
                            $convName = e((($conv['partner_name'] ?? '') === '' || ($conv['partner_name'] ?? '') === '未知用户') ? '未知用户' : $conv['partner_name']);
                            $convText = e(mb_substr($conv['last_msg'], 0, 40));
                            $convTime = formatTime($conv['last_time']);
                            $convUnread = $conv['unread_count'] > 0;
                        ?>
                        <a href="<?php echo $convLink; ?>" class="conversation-item <?php echo $convUnread ? 'unread' : ''; ?>">
                            <img src="<?php echo htmlspecialchars($convImg); ?>" onerror="this.onerror=null;this.src='/bbs/images/default-avatar.png';" class="conv-avatar">
                            <div class="conv-content">
                                <div class="conv-header">
                                    <span class="conv-name"><?php echo $convName; ?></span>
                                    <span class="conv-time"><?php echo $convTime; ?></span>
                                </div>
                                <div class="conv-preview">
                                    <?php echo $convText; ?>
                                    <?php if ($conv['msg_count'] > 1): ?>
                                    <span class="conv-badge"><?php echo $conv['msg_count']; ?> <?php echo e('条消息'); ?></span>
                                    <?php endif; ?>
                                    <?php if ($convUnread): ?>
                                    <span class="conv-unread-dot"></span>
                                    <?php endif; ?>
                                </div>
                            </div>
                        </a>
                        <?php endforeach; ?>
                        <?php if ($totalPages > 1): ?>
                        <div class="pagination">
                            <?php for ($i = 1; $i <= min($totalPages, 5); $i++): ?>
                                <a href="?tab=messages&amp;page=<?php echo $i; ?>"><?php echo $i; ?></a>
                            <?php endfor; ?>
                        </div>
                        <?php endif; ?>
                    <?php endif; ?>
                </div>
            </div>
            <?php endif; ?>

            <!-- 粉丝列表 -->
            <?php if ($tab === 'fans'): ?>
            <div class="panel">
                <div class="panel-header">
                    <h3>👕 <?php echo e('我的粉丝'); ?> (<?php echo $totalFans; ?>)</h3>
                </div>
                <div class="panel-body">
                    <?php if (empty($fans)): ?>
                    <div class="empty-tip"><?php echo e('暂无粉丝'); ?></div>
                    <?php else: ?>
                    <div class="user-grid">
                        <?php foreach ($fans as $fan): ?>
                        <a href="userinfo.php?id=<?php echo $fan['fan_userid']; ?>" class="user-card">
                            <img src="<?php echo e($fan['ll_img'] ?: '/images/logo.png'); ?>" onerror="this.onerror=null;this.src='/images/logo.png';">
                            <div class="name"><?php echo e($fan['ll_n_name'] ?: $fan['ll_name'] ?: '用户' . $fan['fan_userid']); ?></div>
                            <div class="level">Lv.<?php echo (int)($fan['ll_dj'] ?? 0); ?></div>
                        </a>
                        <?php endforeach; ?>
                    </div>
                    <?php if ($totalPages > 1): ?>
                    <div class="pagination">
                        <?php for ($i = 1; $i <= min($totalPages, 5); $i++): ?>
                            <a href="?tab=fans&page=<?php echo $i; ?>"><?php echo $i; ?></a>
                        <?php endfor; ?>
                    </div>
                    <?php endif; ?>
                    <?php endif; ?>
                </div>
            </div>
            <?php endif; ?>

            <!-- 关注的版块最新帖子 -->
            <?php if ($tab === 'followforum'): ?>
            <div class="panel">
                <div class="panel-header">
                    <h3>📌 <?php echo e('关注的版块'); ?> (<?php echo $totalForumPosts; ?>)</h3>
                </div>
                <div class="panel-body">
                    <?php if (empty($forumPosts)): ?>
                    <div class="empty-tip"><?php echo e('暂未关注任何版块'); ?></div>
                    <?php else: ?>
                    <ul class="topic-list">
                        <?php foreach ($forumPosts as $post): ?>
                        <li class="topic-item">
                            <a href="<?php echo bbsUrl('topic', $post['id']); ?>" class="topic-title">
                                [<?php echo e($post['board_name']); ?>] <?php echo e($post['ll_biaoti']); ?>
                            </a>
                            <div class="topic-meta">
                                <span><?php echo (int)($post['reply_count'] ?? 0); ?> <?php echo e('回复'); ?></span>
                                <span><?php echo (int)($post['ll_tongji'] ?? 0); ?> <?php echo e('浏览'); ?></span>
                                <span><?php echo formatTime($post['ll_retime']); ?></span>
                            </div>
                            <?php if (!empty($post['ll_text'])): ?>
                            <div class="topic-preview"><?php echo e(mb_substr(strip_tags($post['ll_text']), 0, 80)); ?>...</div>
                            <?php endif; ?>
                        </li>
                        <?php endforeach; ?>
                    </ul>
                    <?php if ($totalPages > 1): ?>
                    <div class="pagination">
                        <?php for ($i = 1; $i <= min($totalPages, 5); $i++): ?>
                            <a href="?tab=followforum&page=<?php echo $i; ?>"><?php echo $i; ?></a>
                        <?php endfor; ?>
                    </div>
                    <?php endif; ?>
                    <?php endif; ?>
                </div>
            </div>
            <?php endif; ?>

        </div>
    </main>

    <footer class="footer">
        <div class="container">
            <p>&copy; 2009 <a href="/" title="7坛游戏社区" class="footer-brand"><?php echo e('7坛游戏社区'); ?></a> All Rights Reserved</p>
            <?php include __DIR__ . '/_footer_seo.php'; ?>
        </div>
    </footer>

    <!-- 下拉自动加载更多帖子（支持最新/最热） -->
    <script>
    let topicsPage = 1;
    let topicsLoading = false;
    let topicsHasMore = true;
    let currentSort = 'latest';

    function getCurrentSort() {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('sort') || 'latest';
    }

    function loadMoreTopics() {
        if (topicsLoading || !topicsHasMore) return;
        const sortType = getCurrentSort();
        topicsLoading = true;
        topicsPage++;
        const loadText = document.getElementById('load-text');
        if (loadText) loadText.textContent = window.UC_I18N ? UC_I18N.loading : '';
        
        fetch('user.php?ajax=topics&page=' + topicsPage + '&sort=' + sortType)
            .then(r => r.json())
            .then(res => {
                if (res.code === 200 && res.data.length > 0) {
                    const list = document.getElementById('topics-list');
                    if (list) {
                        res.data.forEach(t => {
                            const li = document.createElement('li');
                            li.className = 'topic-item';
                            const replyText = sortType === 'hot' 
                                ? `<span style="color: #e74c3c;">🔥</span> ${t.ll_rchf || 0}`
                                : `${t.reply_count || 0}`;
                            li.innerHTML = `
                                <a href="/bbs/${t.id}/" class="topic-title">${escapeHtml(t.ll_biaoti)}</a>
                                <div class="topic-meta">
                                    <span>${replyText} ${window.UC_I18N ? UC_I18N.reply : ''}</span>
                                    <span>${t.ll_rc || 0} ${window.UC_I18N ? UC_I18N.views : ''}</span>
                                    <span>${formatTimeStr(t.ll_time1)}</span>
                                </div>
                            `;
                            list.appendChild(li);
                        });
                    }
                    topicsHasMore = res.hasMore;
                    if (loadText) loadText.textContent = topicsHasMore ? (window.UC_I18N ? UC_I18N.more : '') : (window.UC_I18N ? UC_I18N.noMore : '');
                } else {
                    topicsHasMore = false;
                    if (loadText) loadText.textContent = window.UC_I18N ? UC_I18N.noMore : '';
                }
                topicsLoading = false;
            })
            .catch(() => {
                topicsLoading = false;
                topicsPage--;
                if (loadText) loadText.textContent = window.UC_I18N ? UC_I18N.more : '';
            });
    }

    // 监听滚动事件，下拉自动加载
    window.addEventListener('scroll', function() {
        const scrollTop = document.documentElement.scrollTop || document.body.scrollTop;
        const scrollHeight = document.documentElement.scrollHeight || document.body.scrollHeight;
        const clientHeight = document.documentElement.clientHeight;
        
        // 当滚动到底部附近（距离底部100px）时自动加载
        if (scrollTop + clientHeight >= scrollHeight - 100) {
            const urlParams = new URLSearchParams(window.location.search);
            const tab = urlParams.get('tab');
            if (tab === 'topics' && topicsHasMore && !topicsLoading) {
                loadMoreTopics();
            } else if (tab === 'replies' && repliesHasMore && !repliesLoading) {
                loadMoreReplies();
            }
        }
    });

    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function formatTimeStr(timeStr) {
        if (!timeStr) return '';
        const d = new Date(timeStr);
        const now = new Date();
        const diff = (now - d) / 1000;
        if (diff < 60) return window.UC_I18N ? UC_I18N.justNow : '';
        if (diff < 3600) return Math.floor(diff/60) + (window.UC_I18N ? UC_I18N.minAgo : '');
        if (diff < 86400) return Math.floor(diff/3600) + (window.UC_I18N ? UC_I18N.hourAgo : '');
        if (diff < 604800) return Math.floor(diff/86400) + (window.UC_I18N ? UC_I18N.dayAgo : '');
        return d.toLocaleDateString();
    }

    // ========== 我的回复 无限滚动 ==========
    let repliesPage = 1;
    let repliesLoading = false;
    let repliesHasMore = true;
    let currentReplySort = 'latest';

    function getCurrentReplySort() {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('sort') || 'latest';
    }

    function loadMoreReplies() {
        if (repliesLoading || !repliesHasMore) return;
        const sortType = getCurrentReplySort();
        repliesLoading = true;
        repliesPage++;
        const loadText = document.getElementById('load-text-replies');
        if (loadText) loadText.textContent = window.UC_I18N ? UC_I18N.loading : '';
        
        fetch('user.php?ajax=replies&page=' + repliesPage + '&sort=' + sortType)
            .then(r => r.json())
            .then(res => {
                if (res.code === 200 && res.data.length > 0) {
                    const list = document.getElementById('replies-list');
                    if (list) {
                        res.data.forEach(r => {
                            const div = document.createElement('div');
                            div.className = 'reply-item';
                            div.style = 'background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 10px;';
                            const topicTitle = r.topic_title || (window.UC_I18N ? UC_I18N.unknownTopic : '');
                            const textContent = r.ll_text ? r.ll_text.replace(/<[^>]+>/g, '').substring(0, 100) + '...' : '';
                            const zanHtml = sortType === 'hot' ? `<span style="color: #e74c3c;">👍 ${r.ll_zan || 0}</span> | ` : '';
                            div.innerHTML = `
                                <a href="/bbs/${r.topic_id}/" style="color: #667eea; font-weight: bold; text-decoration: none;">
                                    ${escapeHtml(topicTitle)}
                                </a>
                                <p style="color: #666; margin: 10px 0; line-height: 1.5;">
                                    ${escapeHtml(textContent)}
                                </p>
                                <div style="font-size: 12px; color: #999;">
                                    ${zanHtml}${formatTimeStr(r.ll_time)}
                                </div>
                            `;
                            list.appendChild(div);
                        });
                    }
                    repliesHasMore = res.hasMore;
                    if (loadText) loadText.textContent = repliesHasMore ? (window.UC_I18N ? UC_I18N.more : '') : (window.UC_I18N ? UC_I18N.noMore : '');
                } else {
                    repliesHasMore = false;
                    if (loadText) loadText.textContent = window.UC_I18N ? UC_I18N.noMore : '';
                }
                repliesLoading = false;
            })
            .catch(() => {
                repliesLoading = false;
                repliesPage--;
                if (loadText) loadText.textContent = window.UC_I18N ? UC_I18N.more : '';
            });
    }
    </script>
    
    <!-- 返回顶部 -->
    <button class="back-to-top" id="backToTop" title="<?php echo e('返回顶部'); ?>">↑</button>
    <script>
    window.addEventListener('scroll', function() {
        var btn = document.getElementById('backToTop');
        if (window.pageYOffset > 300) {
            btn.classList.add('show');
        } else {
            btn.classList.remove('show');
        }
    });
    document.getElementById('backToTop').addEventListener('click', function() {
        window.scrollTo({top: 0, behavior: 'smooth'});
    });
    </script>
<?php $mobileNavActive = 'my'; include __DIR__ . '/mobile_nav.php'; ?>
</body>
</html>

