<?php
// ============================================================
// JWT 工具类（RS256 / HS256 双模式）
// 客户端用 RSA 公钥离线验签，服务端用 HS256 签发
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
