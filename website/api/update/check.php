<?php
/**
 * 7Tan 软件更新检查接口
 *
 * GET/POST /api/update/check.php
 *   参数: ver=当前版本&platform=windows&channel=stable
 *   读取: ../../updates/version.json（版本清单）
 *   返回: {"code":0,"has_update":true/false,"latest":{...} 或 null}
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

$manifest = __DIR__ . '/../../updates/version.json';
if (!file_exists($manifest)) {
    echo json_encode(['code' => 0, 'has_update' => false, 'latest' => null], JSON_UNESCAPED_UNICODE);
    exit;
}

$data = json_decode(file_get_contents($manifest), true);
if (!is_array($data) || empty($data['versions'])) {
    echo json_encode(['code' => 0, 'has_update' => false, 'latest' => null], JSON_UNESCAPED_UNICODE);
    exit;
}

$ver      = isset($_GET['ver']) ? trim($_GET['ver']) : (isset($_POST['ver']) ? trim($_POST['ver']) : '');
$platform = isset($_GET['platform']) ? trim($_GET['platform']) : (isset($_POST['platform']) ? trim($_POST['platform']) : 'windows');
$channel  = isset($_GET['channel']) ? trim($_GET['channel']) : (isset($_POST['channel']) ? trim($_POST['channel']) : 'stable');

// 平台名归一化: win32/win64 → windows, linux → linux, darwin/mac → macos
$platform = strtolower($platform);
if (strpos($platform, 'win') === 0) { $platform = 'windows'; }
elseif (strpos($platform, 'linux') === 0) { $platform = 'linux'; }
elseif (strpos($platform, 'darwin') === 0 || strpos($platform, 'mac') === 0) { $platform = 'macos'; }

// 选择匹配 platform + channel 的最高版本
$latest = null;
foreach ($data['versions'] as $v) {
    $v = (array)$v;
    if (($v['channel'] ?? 'stable') !== $channel) continue;
    if (($v['platform'] ?? 'windows') !== $platform) continue;
    if ($latest === null || version_compare($v['version'], $latest['version'], '>')) {
        $latest = $v;
    }
}

$has_update = false;
if ($latest !== null && $ver !== '') {
    // 客户端版本为空时视为需要更新（首次安装旧版）
    $has_update = version_compare($latest['version'], $ver, '>');
}

echo json_encode([
    'code'       => 0,
    'has_update' => $has_update,
    'latest'     => $latest,
], JSON_UNESCAPED_UNICODE);
