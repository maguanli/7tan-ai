<?php



// ============================================================



// B4: Refresh Token



// GET /api/auth/refresh.php



// Re-issues JWT with latest pro_expires after renewal



// ============================================================







header('Content-Type: application/json; charset=utf-8');



header('Access-Control-Allow-Origin: *');



header('Access-Control-Allow-Methods: GET, POST, OPTIONS');



header('Access-Control-Allow-Headers: Content-Type, Authorization');







if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {



    http_response_code(200);



    exit;



}







require_once __DIR__ . '/../../config/database.php';



require_once __DIR__ . '/../../lib/jwt_helper.php';







$JWT_SECRET = defined('JWT_SECRET') ? JWT_SECRET : 'change-me-to-a-random-64-char-string';







// ============================================================



// Extract Token (4 sources)



// ============================================================



// P1-5: 统一读取请求体（php://input 只能读一次）

$_RAW_BODY = file_get_contents('php://input');

$request_body = json_decode($_RAW_BODY ?: '', true);

if (!is_array($request_body)) { $request_body = []; }



$token = '';







// 1. Authorization header (including Apache REDIRECT_ variant)



$auth_header = $_SERVER['HTTP_AUTHORIZATION'] ?? $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ?? '';



if (!empty($auth_header) && preg_match('/Bearer\s+(.+)/i', $auth_header, $m)) {



    $token = $m[1];



}







// 2. GET param



if (empty($token) && !empty($_GET['token'])) {



    $token = $_GET['token'];



}







// 3. POST JSON body



if (empty($token) && !empty($request_body['token'])) {



    $token = $request_body['token'];



}







// 4. POST form



if (empty($token) && !empty($_POST['token'])) {



    $token = $_POST['token'];



}







if (empty($token)) {



    http_response_code(401);



    echo json_encode(['code' => -1, 'message' => 'Missing Token']);



    exit;



}







// ============================================================



// Decode old Token (skip expiry check)



// ============================================================



try {



    $payload = jwt_decode_auto_skip_expiry($token, $JWT_SECRET);



} catch (JWTException $e) {



    http_response_code(401);



    echo json_encode(['code' => -1, 'message' => 'Token invalid: ' . $e->getMessage()], JSON_UNESCAPED_UNICODE);



    exit;



} catch (\Throwable $e) {



    http_response_code(401);



    echo json_encode(['code' => -1, 'message' => 'Token parse error: ' . $e->getMessage()], JSON_UNESCAPED_UNICODE);



    exit;



}







$uid = (int)($payload['uid'] ?? 0);



$db = get_db_connection();







try {



    // ============================================================



    // Query user info (ll_useregs)



    // ============================================================



    $stmt = $db->prepare('SELECT id, ll_name FROM ll_useregs WHERE id = :uid LIMIT 1');



    $stmt->execute([':uid' => $uid]);



    $user = $stmt->fetch(PDO::FETCH_ASSOC);







    if (!$user) {



        http_response_code(401);



        echo json_encode(['code' => -1, 'message' => 'User not found']);



        exit;



    }







    // ============================================================



    // Query latest pro subscription status



    // ============================================================



    $now = time();



    $stmt = $db->prepare(



        'SELECT id, plan, months, amount, activated_at, expires_at



         FROM user_pro_subscriptions



         WHERE user_id = :uid AND status = 1 AND expires_at > :now



         ORDER BY expires_at DESC



         LIMIT 1'



    );



    $stmt->execute([':uid' => $uid, ':now' => $now]);



    $sub = $stmt->fetch(PDO::FETCH_ASSOC);







    if ($sub) {



        $pro_activated = 1;



        $pro_expires   = (int)$sub['expires_at'];



        $is_pro        = ($pro_expires > $now);



    } else {



        $pro_activated = 0;



        $pro_expires   = 0;



        $is_pro        = false;



    }



} catch (\PDOException $e) {



    http_response_code(500);



    echo json_encode(['code' => -1, 'message' => 'Database error'], JSON_UNESCAPED_UNICODE);



    exit;



} catch (\Throwable $e) {



    http_response_code(500);



    echo json_encode(['code' => -1, 'message' => 'Server error: ' . $e->getMessage()], JSON_UNESCAPED_UNICODE);



    exit;



}







// ============================================================



// P1-5: Token 设备绑定校验（分级：完整版强制 / 免费版宽松 / 旧客户端放行）



// ============================================================



$token_device = (string)($payload['device_id'] ?? '');



$cur_device = trim((string)($_SERVER['HTTP_X_DEVICE_ID'] ?? ($_GET['device_id'] ?? ($request_body['device_id'] ?? ''))));



if ($token_device !== '' && $cur_device !== '' && $token_device !== $cur_device) {



    if ($is_pro) {



        // 完整版：设备不匹配 → 拒绝刷新，强制重新登录（防共享/转卖）



        http_response_code(401);



        echo json_encode(['code' => -1, 'message' => '设备已变更，请重新登录'], JSON_UNESCAPED_UNICODE);



        exit;



    }



    // 免费版：宽松放行（记录日志供排查，不阻断使用）



    error_log("[P1-5] 免费用户设备变化 uid={$uid} token_dev={$token_device} cur_dev={$cur_device} ip=" . ($_SERVER['REMOTE_ADDR'] ?? ''));



}



// 旧 token 无 device_id 或客户端未携带 → 放行（向后兼容）



// ============================================================



// Issue new JWT



// ============================================================



$new_token = jwt_encode_auto([



    'uid'           => (int)$user['id'],



    'username'      => $user['ll_name'],



    'level'         => $is_pro ? 'pro' : 'free',



    'pro_activated' => $pro_activated,



    'pro_expires'   => $pro_expires,



    'device_id'     => $token_device,   // P1-5: 保留设备绑定



    'iat'           => $now,



    'exp'           => $now + 86400 * 30,



], $JWT_SECRET);







// ============================================================



// 签发 PRO License（购买/续费后刷新即获得离线授权凭证）



// ============================================================



$pro_license = null;



if ($is_pro) {



    $pk_path = defined('RSA_PRIVATE_KEY_PATH') ? RSA_PRIVATE_KEY_PATH : '';



    if ($pk_path && file_exists($pk_path)) {



        $pk = file_get_contents($pk_path);



        $license_data = json_encode([



            'uid'         => (int)$user['id'],



            'level'       => 'pro',



            'pro_expires' => $pro_expires,



            'issued_at'   => $now,



        ]);



        $sig = '';



        if (openssl_sign($license_data, $sig, $pk, 'sha256WithRSAEncryption')) {



            // 格式: base64url(signature).base64url(payload)



            $pro_license = base64url_encode($sig) . '.' . base64url_encode($license_data);



        }



    }



}



// ============================================================



// Response



// ============================================================



echo json_encode([



    'code'    => 0,



    'message' => 'Token refreshed',



    'data'    => [



        'token'         => $new_token,



        'pro_license'   => $pro_license,



        'level'         => $is_pro ? 'pro' : 'free',



        'pro_activated' => $pro_activated,



        'pro_expires'   => $pro_expires,



        'pro_expires_at'=> $pro_expires > 0 ? date('Y-m-d H:i:s', $pro_expires) : null,



    ],



], JSON_UNESCAPED_UNICODE);



