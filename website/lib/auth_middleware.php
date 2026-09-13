<?php
// ============================================================
// 登录验证中间件
// 所有需要登录的 API 统一调用 require_login()
// 支持：Authorization header / Cookie auth_token / GET token
// 位置: /lib/auth_middleware.php
// ============================================================

/**
 * 从请求中提取 Token 并验证，返回用户信息
 *
 * Token 获取优先级：Authorization header > Cookie auth_token > GET token
 *
 * @param string $jwt_secret  JWT 密钥
 * @return array  ['uid'=>int, 'username'=>string]
 * @throws Exception 401 未登录或 Token 无效
 */
function require_login(string $jwt_secret): array
{
    // 获取 Token（优先级：Authorization header > Cookie > GET 参数）
    $token = '';
    $auth_header = $_SERVER['HTTP_AUTHORIZATION'] ?? $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ?? '';
    if (preg_match('/Bearer\s+(.+)/i', $auth_header, $m)) {
        $token = $m[1];
    }
    if ($token === '' && !empty($_COOKIE['auth_token'])) {
        $token = $_COOKIE['auth_token'];
    }
    if ($token === '' && !empty($_GET['token'])) {
        $token = $_GET['token'];
    }
    if ($token === '') {
        http_response_code(401);
        echo json_encode(['code' => -1, 'message' => '请先登录'], JSON_UNESCAPED_UNICODE);
        exit;
    }

    // 验证
    try {
        $payload = jwt_decode_auto($token, $jwt_secret);
    } catch (Exception $e) {
        http_response_code(401);
        echo json_encode(['code' => -1, 'message' => 'Token 无效或已过期，请重新登录'], JSON_UNESCAPED_UNICODE);
        exit;
    }

    $uid = (int)($payload['uid'] ?? 0);
    if ($uid <= 0) {
        http_response_code(401);
        echo json_encode(['code' => -1, 'message' => 'Token 数据异常'], JSON_UNESCAPED_UNICODE);
        exit;
    }

    return [
        'uid'      => $uid,
        'username' => $payload['username'] ?? '',
    ];
}
