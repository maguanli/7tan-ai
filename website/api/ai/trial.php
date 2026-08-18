<?php

// ============================================================

// C2: 试用 AI 代理 API（防薅羊毛 — 服务端计次）

// POST /api/ai/trial.php

//

// 工作流:

//   1. 客户端发 {token, model, messages}

//   2. 服务端验 JWT → 查 trial_ai_count → 代理转发 DeepSeek → 扣次 → 返回结果

//

// 羊毛防护:

//   - trial_ai_count 存在 MySQL，删不掉

//   - 每请求扣 1，到 0 自动拒绝

//   - PRO 用户也走此端点但 skip 扣次（PRO 用自己 Key 不走这里，但兜底）

//   - 30 秒超时 + 被 DeepSeek 限流时返回友好错误

// ============================================================



header('Content-Type: application/json; charset=utf-8');

header('Access-Control-Allow-Origin: *');

header('Access-Control-Allow-Methods: POST, OPTIONS');

header('Access-Control-Allow-Headers: Content-Type');



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



// ============================================================

// 解析请求

// ============================================================

$input = json_decode(file_get_contents('php://input'), true);

if (!$input) {

    http_response_code(400);

    echo json_encode(['code' => -1, 'message' => '请求格式错误']);

    exit;

}



$token    = $input['token']    ?? '';

$model    = $input['model']    ?? TRIAL_MODEL;



// ============================================================

// 模型名映射：客户端可能传 "DeepSeek-V4-Flash-0731" 等产品名，

// DeepSeek 官方 API 只认 deepseek-v4-flash / deepseek-v4-pro，

// 统一映射为官方 ID，避免 400 Model Not Exist

// ============================================================

$MODEL_ALIASES = [

    'deepseek-v4-flash-0731' => 'deepseek-v4-flash',

    'deepseek-v4-flash'      => 'deepseek-v4-flash',

    'deepseek-chat'          => 'deepseek-v4-flash',

    'deepseek-v4-pro'        => 'deepseek-v4-pro',

    'deepseek-reasoner'      => 'deepseek-v4-pro',

];

$model_key = strtolower(trim((string)$model));

$model     = $MODEL_ALIASES[$model_key] ?? 'deepseek-v4-flash';

$messages = $input['messages'] ?? [];



if (empty($token)) {

    http_response_code(401);

    echo json_encode(['code' => -1, 'message' => '缺少认证令牌']);

    exit;

}



if (empty($messages) || !is_array($messages)) {

    http_response_code(400);

    echo json_encode(['code' => -1, 'message' => 'messages 不能为空']);

    exit;

}



// ============================================================

// 验证 JWT

// ============================================================

if (!defined('JWT_SECRET')) { http_response_code(500); echo json_encode(['code'=>-1,'message'=>'Server config error: JWT_SECRET']); exit; }

$JWT_SECRET = JWT_SECRET;



try {

    $payload = jwt_decode_auto($token, $JWT_SECRET);

} catch (JWTException $e) {

    http_response_code(401);

    echo json_encode(['code' => -1, 'message' => '令牌无效: ' . $e->getMessage()]);

    exit;

}



$uid      = (int)($payload['uid'] ?? 0);

$level    = $payload['level'] ?? 'free';

$is_pro   = ($level === 'pro');



// ============================================================

// 检查试用次数（PRO 跳过，free 用户需要 trial_ai_count > 0）

// ============================================================

$db = get_db_connection();



if (!$is_pro) {

    // 从数据库读取最新 trial_ai_count（不信任 JWT 里的值，防伪造）

    try {

        $stmt = $db->prepare('SELECT trial_ai_count FROM ll_useregs WHERE id = :uid LIMIT 1');

        $stmt->execute([':uid' => $uid]);

        $row = $stmt->fetch(PDO::FETCH_ASSOC);

        $trials_left = ($row && isset($row['trial_ai_count'])) ? (int)$row['trial_ai_count'] : 0;

    } catch (PDOException $e) {

        // trial_ai_count 列尚不存在 → 回退（等执行 migration.sql 后恢复正常）

        $trials_left = 0;

    }



    if ($trials_left <= 0) {

        http_response_code(402);  // Payment Required

        echo json_encode([

            'code'    => -1,

            'message' => 'AI 试用次数已用完（共 3 次）。请在软件设置中填入你自己的 DeepSeek API Key，或在 7tan.com 升级完整版。',

            'data'    => [

                'trials_left' => 0,

                'action'      => 'upgrade_or_add_key',

            ],

        ]);

        exit;

    }

} else {

    $trials_left = -1; // PRO 用户不限次

}



// ============================================================

// 代理转发 DeepSeek API

// ============================================================

// ============================================================

// 获取 DeepSeek API Key：唯一来源为数据库 ll_api_keys 表（api-keys.php 后台管理）。

// 不允许任何配置文件常量回退——Key 只能通过后台更换，防止绕过。

// ============================================================

function get_trial_deepseek_config(PDO $db): array {

    // 唯一来源：数据库 ll_api_keys 表（api-keys.php 后台管理）

    // 不允许回退到配置文件常量——取不到直接返回空，由调用方报错

    try {

        $stmt = $db->prepare(

            "SELECT api_key, api_url FROM ll_api_keys WHERE provider='deepseek' AND is_active=1 ORDER BY id ASC LIMIT 1"

        );

        $stmt->execute();

        $row = $stmt->fetch(PDO::FETCH_ASSOC);

    } catch (PDOException $e) {

        // ll_api_keys 表不可用 → 返回空，调用方报错（不允许回退）

        return ['key' => '', 'endpoint' => ''];

    }

    if (!$row || empty($row['api_key']) || strpos($row['api_key'], 'your-') === 0) {

        return ['key' => '', 'endpoint' => ''];

    }

    $url = !empty($row['api_url']) ? rtrim($row['api_url'], '/') : '';

    // 数据库存的是完整端点（.../chat/completions）或 base_url，统一归一化为完整端点

    if ($url && substr($url, -17) !== '/chat/completions') {

        $url .= '/chat/completions';

    }

    if (!$url) {

        $url = 'https://api.deepseek.com/v1/chat/completions';

    }

    return ['key' => $row['api_key'], 'endpoint' => $url];

}



$ds       = get_trial_deepseek_config($db);

$api_key  = $ds['key'];

$endpoint = $ds['endpoint'];



if (empty($api_key) || strpos($api_key, 'your-') === 0) {

    http_response_code(500);

    echo json_encode(['code' => -1, 'message' => '服务端 DeepSeek API Key 未配置（ll_api_keys 表无可用记录），请在 https://img.7tan.cn/api-keys.php 后台配置']);

    exit;

}



$request_body = json_encode([

    'model'    => $model,

    'messages' => $messages,

    'stream'   => false,

], JSON_UNESCAPED_UNICODE);



$ch = curl_init($endpoint);

curl_setopt_array($ch, [

    CURLOPT_POST           => true,

    CURLOPT_POSTFIELDS     => $request_body,

    CURLOPT_HTTPHEADER     => [

        'Content-Type: application/json',

        'Authorization: Bearer ' . $api_key,

    ],

    CURLOPT_RETURNTRANSFER => true,

    CURLOPT_TIMEOUT        => 60,

    CURLOPT_CONNECTTIMEOUT => 10,

]);



$response_body = curl_exec($ch);

$http_code     = curl_getinfo($ch, CURLINFO_HTTP_CODE);

$curl_error    = curl_error($ch);

curl_close($ch);



// ============================================================

// 处理 DeepSeek 响应

// ============================================================

if ($curl_error) {

    http_response_code(502);

    echo json_encode([

        'code'    => -1,

        'message' => 'AI 服务连接失败，请稍后重试',

        'detail'  => $curl_error,

    ]);

    exit;

}



$ai_response = json_decode($response_body, true);



if ($http_code !== 200 || !$ai_response) {

    $err_msg = $ai_response['error']['message'] ?? "DeepSeek 返回 HTTP {$http_code}";

    http_response_code(502);

    echo json_encode(['code' => -1, 'message' => 'AI 调用失败: ' . $err_msg]);

    exit;

}



// ============================================================

// 扣减试用次数（DB 级别，防止并发：UPDATE ... WHERE trial_ai_count > 0）

// ============================================================

if (!$is_pro) {

    try {

        $stmt = $db->prepare(

            'UPDATE ll_useregs SET trial_ai_count = trial_ai_count - 1 WHERE id = :uid AND trial_ai_count > 0'

        );

        $stmt->execute([':uid' => $uid]);

    } catch (PDOException $e) {

        // 列不存在时忽略（等 migration 后恢复）

    }

    $new_count = $trials_left - 1;

} else {

    $new_count = -1;

}



// ============================================================

// 响应（透传 DeepSeek 返回内容 + 剩余次数）

// ============================================================

echo json_encode([

    'code'    => 0,

    'message' => 'ok',

    'data'    => [

        'choices'      => $ai_response['choices'] ?? [],

        'usage'        => $ai_response['usage'] ?? null,

        'model'        => $ai_response['model'] ?? $model,

        'trials_left'  => $new_count,

    ],

], JSON_UNESCAPED_UNICODE);

