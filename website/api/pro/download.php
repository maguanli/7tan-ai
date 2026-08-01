<?php
// ============================================================
// B5c: 专业版源码包下载 API（鉴权发放）
// POST /api/pro/download.php
// body: {"token":"...", "package":"full"|"update"}
//
// 文件存放: D:\workspace\pro_packages\<uid>\  （web 根之外，不可直接访问）
//   full   → 7tan-pro-src-*.zip      专业完整包（源码+_python+水印）
//   update → 7tan-pro-update-*.zip   专业增量包（仅源码+水印）
//
// 校验链路: JWT 登录 → 有效专业版订阅(或管理员) → 用户目录存在包 → 流式下载
// 安全: uid 强制 int（无目录穿越）、glob 固定前缀、订阅过期拒绝
// ============================================================

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['code' => -1, 'message' => '仅支持 POST']);
    exit;
}

require_once __DIR__ . '/../../config/database.php';
require_once __DIR__ . '/../../lib/jwt_helper.php';
require_once __DIR__ . '/../../lib/auth_middleware.php';

if (!defined('JWT_SECRET')) { http_response_code(500); echo json_encode(['code'=>-1,'message'=>'Server config error: JWT_SECRET']); exit; }
$JWT_SECRET = JWT_SECRET;

// ========== 1. 登录校验 ==========
$user = require_login($JWT_SECRET);
$uid  = (int)$user['uid'];
if ($uid <= 0) {
    http_response_code(401);
    echo json_encode(['code' => -1, 'message' => 'Token 数据异常']);
    exit;
}

// ========== 2. 输入校验 ==========
$input   = json_decode(file_get_contents('php://input'), true);
$package = $input['package'] ?? 'full';
if (!in_array($package, ['full', 'update'], true)) {
    http_response_code(400);
    echo json_encode(['code' => -1, 'message' => '无效的包类型，可选 full/update'], JSON_UNESCAPED_UNICODE);
    exit;
}

// ========== 3. 订阅校验（管理员直通） ==========
$db  = get_db_connection();
$now = time();

$ADMIN_UIDS = defined('ADMIN_UIDS') ? explode(',', ADMIN_UIDS) : [1];
$is_admin   = in_array($uid, $ADMIN_UIDS);

$sub = null;
if (!$is_admin) {
    $stmt = $db->prepare(
        'SELECT id, expires_at FROM user_pro_subscriptions
         WHERE user_id = :uid AND status = 1 AND expires_at > :now
         ORDER BY expires_at DESC LIMIT 1'
    );
    $stmt->execute([':uid' => $uid, ':now' => $now]);
    $sub = $stmt->fetch(PDO::FETCH_ASSOC);

    if (!$sub) {
        http_response_code(403);
        echo json_encode(['code' => -1, 'message' => '专业版已过期或未开通，无法下载源码包'], JSON_UNESCAPED_UNICODE);
        exit;
    }
}

// ========== 4. 定位文件（web 根之外的 pro_packages\<uid>\） ==========
$pkgs_root = dirname(__DIR__, 2) . DIRECTORY_SEPARATOR . 'pro_packages';
$user_dir  = $pkgs_root . DIRECTORY_SEPARATOR . $uid;
$pattern   = $package === 'full'
    ? $user_dir . DIRECTORY_SEPARATOR . '7tan-pro-src-*.zip'
    : $user_dir . DIRECTORY_SEPARATOR . '7tan-pro-update-*.zip';

$files = glob($pattern);
if (!$files) {
    http_response_code(404);
    echo json_encode(['code' => -1, 'message' => '未找到可下载的包，请联系管理员'], JSON_UNESCAPED_UNICODE);
    exit;
}

// 取最新文件
usort($files, function ($a, $b) { return filemtime($b) - filemtime($a); });
$file     = $files[0];
$filename = basename($file);

// ========== 5. 下载日志 ==========
@file_put_contents(__DIR__ . '/downloads.log',
    json_encode([
        't'       => date('c'),
        'uid'     => $uid,
        'package' => $package,
        'file'    => $filename,
        'ip'      => $_SERVER['REMOTE_ADDR'] ?? '',
        'size'    => filesize($file),
    ], JSON_UNESCAPED_UNICODE) . PHP_EOL,
    FILE_APPEND | LOCK_EX
);

// ========== 6. 流式输出（大文件，关闭缓冲） ==========
set_time_limit(3600);
while (ob_get_level() > 0) { ob_end_clean(); }
header('Content-Type: application/zip');
header('Content-Disposition: attachment; filename="' . $filename . '"');
header('Content-Length: ' . filesize($file));
header('X-Accel-Buffering: no');
readfile($file);
exit;
