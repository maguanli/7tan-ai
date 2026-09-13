<?php
// ============================================================
// JWT 工具类（RS256 / HS256 双模式）
// 默认 RS256：客户端用 RSA 公钥离线验签，服务端用 RSA 私钥签发
// 兼容 HS256：未配置 RSA 密钥时自动回退（开发/过渡期用）
// 位置: /lib/jwt_helper.php
// ============================================================

class JWTException extends Exception {}

/**
 * JWT 编码（HS256）
 */
function jwt_encode(array $payload, string $secret): string
{
    $header = base64url_encode(json_encode(['alg' => 'HS256', 'typ' => 'JWT']));
    $payload_json = base64url_encode(json_encode($payload));
    $signature = base64url_encode(
        hash_hmac('sha256', "$header.$payload_json", $secret, true)
    );
    return "$header.$payload_json.$signature";
}

/**
 * JWT 解码 + 验证（HS256）
 */
function jwt_decode(string $token, string $secret): array
{
    $parts = explode('.', $token);
    if (count($parts) !== 3) {
        throw new JWTException('Token 格式错误');
    }

    [$header_b64, $payload_b64, $signature_b64] = $parts;

    // 验证签名
    $expected_sig = base64url_encode(
        hash_hmac('sha256', "$header_b64.$payload_b64", $secret, true)
    );

    if (!hash_equals($expected_sig, $signature_b64)) {
        throw new JWTException('签名验证失败');
    }

    $payload = json_decode(base64url_decode($payload_b64), true);
    if (!$payload) {
        throw new JWTException('Payload 解析失败');
    }

    // 检查过期
    if (isset($payload['exp']) && $payload['exp'] < time()) {
        throw new JWTException('Token 已过期');
    }

    return $payload;
}

/**
 * JWT 解码（跳过过期检查，refresh 用）
 */
function jwt_decode_skip_expiry(string $token, string $secret): array
{
    $parts = explode('.', $token);
    if (count($parts) !== 3) {
        throw new JWTException('Token 格式错误');
    }

    [$header_b64, $payload_b64, $signature_b64] = $parts;

    $expected_sig = base64url_encode(
        hash_hmac('sha256', "$header_b64.$payload_b64", $secret, true)
    );

    if (!hash_equals($expected_sig, $signature_b64)) {
        throw new JWTException('签名验证失败');
    }

    $payload = json_decode(base64url_decode($payload_b64), true);
    if (!$payload) {
        throw new JWTException('Payload 解析失败');
    }

    return $payload;
}

// ============================================================
// RS256 编解码（RSA-PKCS1v15 + SHA-256）
// ============================================================

/**
 * JWT 编码（RS256）
 * @param array  $payload          Payload 数组
 * @param string $private_key_pem  RSA 私钥 PEM
 * @return string JWT Token
 */
function jwt_encode_rs256(array $payload, string $private_key_pem): string
{
    $header = base64url_encode(json_encode(['alg' => 'RS256', 'typ' => 'JWT']));
    $payload_b64 = base64url_encode(json_encode($payload));
    $data = "$header.$payload_b64";
    openssl_sign($data, $signature, $private_key_pem, 'sha256WithRSAEncryption');
    if (!$signature) {
        throw new JWTException('RSA 签名失败: ' . openssl_error_string());
    }
    return "$header.$payload_b64." . base64url_encode($signature);
}

/**
 * JWT 解码 + 验证（RS256）
 */
function jwt_decode_rs256(string $token, string $public_key_pem): array
{
    $parts = explode('.', $token);
    if (count($parts) !== 3) {
        throw new JWTException('Token 格式错误');
    }
    [$header_b64, $payload_b64, $signature_b64] = $parts;
    $data = "$header_b64.$payload_b64";
    $signature = base64url_decode($signature_b64);
    $result = openssl_verify($data, $signature, $public_key_pem, 'sha256WithRSAEncryption');
    if ($result !== 1) {
        throw new JWTException('签名验证失败');
    }
    $payload = json_decode(base64url_decode($payload_b64), true);
    if (!$payload) {
        throw new JWTException('Payload 解析失败');
    }
    if (isset($payload['exp']) && $payload['exp'] < time()) {
        throw new JWTException('Token 已过期');
    }
    return $payload;
}

/**
 * JWT 解码 RS256（跳过过期检查，refresh 用）
 */
function jwt_decode_rs256_skip_expiry(string $token, string $public_key_pem): array
{
    $parts = explode('.', $token);
    if (count($parts) !== 3) {
        throw new JWTException('Token 格式错误');
    }
    [$header_b64, $payload_b64, $signature_b64] = $parts;
    $data = "$header_b64.$payload_b64";
    $signature = base64url_decode($signature_b64);
    $result = openssl_verify($data, $signature, $public_key_pem, 'sha256WithRSAEncryption');
    if ($result !== 1) {
        throw new JWTException('签名验证失败');
    }
    $payload = json_decode(base64url_decode($payload_b64), true);
    if (!$payload) {
        throw new JWTException('Payload 解析失败');
    }
    return $payload;
}

// ============================================================
// 智能编解码：自动选择 RS256（优先）或 HS256（回退）
// ============================================================

/**
 * 智能编码：有 RSA 私钥用 RS256，否则用 HS256
 */
function jwt_encode_auto(array $payload, string $secret_or_key): string
{
    // 检测是否为 RSA 私钥
    if (strpos($secret_or_key, '-----BEGIN RSA PRIVATE KEY-----') !== false
        || strpos($secret_or_key, '-----BEGIN PRIVATE KEY-----') !== false) {
        return jwt_encode_rs256($payload, $secret_or_key);
    }
    return jwt_encode($payload, $secret_or_key);
}

/**
 * 智能解码：自动识别 RS256/HS256
 */
function jwt_decode_auto(string $token, string $secret_or_key): array
{
    $parts = explode('.', $token);
    if (count($parts) !== 3) {
        throw new JWTException('Token 格式错误');
    }
    $header = json_decode(base64url_decode($parts[0]), true);
    $alg = $header['alg'] ?? 'HS256';
    if ($alg === 'RS256') {
        return jwt_decode_rs256($token, $secret_or_key);
    }
    return jwt_decode($token, $secret_or_key);
}

/**
 * 智能解码（跳过过期检查）
 */
function jwt_decode_auto_skip_expiry(string $token, string $secret_or_key): array
{
    $parts = explode('.', $token);
    if (count($parts) !== 3) {
        throw new JWTException('Token 格式错误');
    }
    $header = json_decode(base64url_decode($parts[0]), true);
    $alg = $header['alg'] ?? 'HS256';
    if ($alg === 'RS256') {
        return jwt_decode_rs256_skip_expiry($token, $secret_or_key);
    }
    return jwt_decode_skip_expiry($token, $secret_or_key);
}

// ============================================================
// Base64URL 编解码
// ============================================================

function base64url_encode(string $data): string
{
    return rtrim(strtr(base64_encode($data), '+/', '-_'), '=');
}

function base64url_decode(string $data): string
{
    $remainder = strlen($data) % 4;
    if ($remainder) {
        $data .= str_repeat('=', 4 - $remainder);
    }
    return base64_decode(strtr($data, '-_', '+/'));
}

// ============================================================
// RSA Pro License 签发
// 格式: base64url(RSA-SHA256签名).base64url(JSON payload)
// 客户端用 RSA 公钥离线验签，无需网络即可确认 PRO 身份
// ============================================================

/**
 * 签发 RSA 签名的 Pro License
 * @param int    $uid          用户 ID
 * @param int    $pro_expires  PRO 到期时间（Unix 时间戳）
 * @param string $private_key  RSA 私钥 PEM
 * @return string Pro License 字符串
 */
function sign_pro_license(int $uid, int $pro_expires, string $private_key): string
{
    $payload = json_encode([
        'uid'         => $uid,
        'level'       => 'pro',
        'pro_expires' => $pro_expires,
        'issued_at'   => time(),
    ]);
    
    $payload_b64 = base64url_encode($payload);
    
    // RSA-SHA256 签名
    openssl_sign($payload_b64, $signature, $private_key, 'sha256WithRSAEncryption');
    if (!$signature) {
        throw new \RuntimeException('RSA 签名失败: ' . openssl_error_string());
    }
    
    return base64url_encode($signature) . '.' . $payload_b64;
}
