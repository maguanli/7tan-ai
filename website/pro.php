<?php
// ============================================================
// 购买专业版页面（独立版，JWT Cookie 认证）
// 位置: /pro.php
// 无需依赖网站框架，通过 api/pro/* 接口交互
// ============================================================

// 1. 构建基础 URL（用于服务端 curl 调用自身 API）
$is_https = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') || ($_SERVER['SERVER_PORT'] ?? 80) == 443;
$base_url = ($is_https ? 'https' : 'http') . '://' . ($_SERVER['HTTP_HOST'] ?? 'localhost');

// 2. 从 Cookie 读取 Token
$token = $_COOKIE['auth_token'] ?? '';
$user = null;
$is_pro = false;
$pro_expires = 0;

if ($token) {
    // 调用 verify 接口验证身份
    $ch = curl_init();
    curl_setopt_array($ch, [
        CURLOPT_URL            => $base_url . '/api/auth/verify.php',
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER     => ["Authorization: Bearer $token"],
        CURLOPT_TIMEOUT        => 10,
    ]);
    $resp = curl_exec($ch);
    curl_close($ch);
    if ($resp) {
        $data = json_decode($resp, true);
        if (($data['code'] ?? -1) === 0) {
            $user = $data['data'];
        }
    }
}

// 3. 如果已登录，查询 Pro 状态
if ($user) {
    $ch = curl_init();
    curl_setopt_array($ch, [
        CURLOPT_URL            => $base_url . '/api/pro/status.php',
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER     => ["Authorization: Bearer $token"],
        CURLOPT_TIMEOUT        => 10,
    ]);
    $resp = curl_exec($ch);
    curl_close($ch);
    if ($resp) {
        $status = json_decode($resp, true);
        if (($status['code'] ?? -1) === 0) {
            $is_pro      = ($status['data']['level'] ?? 'free') === 'pro';
            $pro_expires = $status['data']['pro_expires'] ?? 0;
        }
    }
}

// 4. 当前时间（用于剩余天数计算）
$now = time();

// 5. 套餐定义
$plans = [
    ['key' => 'monthly',     'name' => '月付',   'months' => 1,  'price' => 50,  'per_month' => 50,  'save' => 0,   'badge' => ''],
    ['key' => 'quarterly',   'name' => '季付',   'months' => 3,  'price' => 120, 'per_month' => 40,  'save' => 30,  'badge' => '⭐ 推荐'],
    ['key' => 'semi_annual', 'name' => '半年付', 'months' => 6,  'price' => 200, 'per_month' => 33,  'save' => 100, 'badge' => '🔥 最火'],
    ['key' => 'annual',      'name' => '年付',   'months' => 12, 'price' => 350, 'per_month' => 29,  'save' => 250, 'badge' => '👑 最省'],
];

$now = time();
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>购买专业版 - 7坛游戏社区</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
            color: #e0e0e0;
            min-height: 100vh;
        }
        .navbar {
            background: rgba(15,15,26,0.95);
            border-bottom: 1px solid #2a2a4a;
            padding: 14px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            backdrop-filter: blur(10px);
        }
        .nav-logo { font-size: 20px; font-weight: 700; }
        .nav-logo span { color: #ff6b35; }
        .nav-links a { color: #a0a0c0; text-decoration: none; margin-left: 24px; font-size: 14px; transition: color .2s; }
        .nav-links a:hover { color: #fff; }
        .container { max-width: 960px; margin: 0 auto; padding: 40px 20px; }
        .page-title { text-align: center; margin-bottom: 8px; font-size: 28px; font-weight: 700; }
        .page-subtitle { text-align: center; color: #8888aa; margin-bottom: 36px; font-size: 15px; }

        /* 当前状态卡片 */
        .status-card {
            background: linear-gradient(135deg, #1e1e3a, #252550);
            border: 1px solid #3a3a60;
            border-radius: 16px;
            padding: 24px 32px;
            margin-bottom: 36px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 16px;
        }
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
            padding: 6px 16px;
            border-radius: 20px;
            font-weight: 600;
        }
        .status-pro { background: #1a3a1a; color: #4caf50; border: 1px solid #2e5a2e; }
        .status-free { background: #2a2a1a; color: #ff9800; border: 1px solid #4a3a1a; }
        .status-info { color: #aaa; font-size: 14px; }
        .status-info strong { color: #fff; }

        /* 套餐卡片 */
        .plan-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 32px; }
        .plan-card {
            background: #1a1a30;
            border: 2px solid #2a2a4a;
            border-radius: 16px;
            padding: 28px 20px;
            text-align: center;
            cursor: pointer;
            transition: all .25s;
            position: relative;
        }
        .plan-card:hover { border-color: #ff6b35; transform: translateY(-4px); box-shadow: 0 8px 32px rgba(255,107,53,0.15); }
        .plan-card.selected { border-color: #ff6b35; background: #1f1f3a; box-shadow: 0 0 0 1px #ff6b35; }
        .plan-badge { position: absolute; top: -12px; left: 50%; transform: translateX(-50%); background: #ff6b35; color: #fff; padding: 4px 14px; border-radius: 12px; font-size: 12px; font-weight: 600; white-space: nowrap; }
        .plan-name { font-size: 18px; font-weight: 700; margin-bottom: 4px; }
        .plan-months { color: #888; font-size: 13px; margin-bottom: 12px; }
        .plan-price { font-size: 36px; font-weight: 800; color: #ff6b35; }
        .plan-price sub { font-size: 16px; font-weight: 400; color: #888; }
        .plan-per-month { color: #888; font-size: 12px; margin-top: 2px; }
        .plan-save { color: #4caf50; font-size: 12px; margin-top: 4px; min-height: 18px; }

        /* 按钮 */
        .btn-buy {
            display: block;
            width: 100%;
            max-width: 400px;
            margin: 0 auto;
            padding: 16px 32px;
            font-size: 18px;
            font-weight: 700;
            color: #fff;
            background: linear-gradient(135deg, #ff6b35, #ff8c42);
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all .25s;
            text-align: center;
        }
        .btn-buy:hover { transform: translateY(-2px); box-shadow: 0 6px 24px rgba(255,107,53,0.4); }
        .btn-buy:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

        /* 消息区 */
        .msg { text-align: center; margin-top: 20px; font-size: 14px; min-height: 24px; }
        .msg-success { color: #4caf50; }
        .msg-error { color: #f44336; }
        .msg-info { color: #ff9800; }

        /* 登录提示 */
        .login-prompt {
            text-align: center;
            padding: 60px 20px;
            background: #1a1a30;
            border-radius: 16px;
            border: 1px solid #2a2a4a;
        }
        .login-prompt h2 { margin-bottom: 12px; }
        .login-prompt a { color: #ff6b35; font-weight: 600; text-decoration: none; }
        .login-prompt a:hover { text-decoration: underline; }
    </style>
</head>
<body>

<div class="navbar">
    <div class="nav-logo">7<span>坛</span>游戏社区</div>
    <div class="nav-links">
        <a href="https://www.7tan.com/">首页</a>
        <a href="https://www.7tan.com/android/">安卓游戏</a>
        <a href="https://www.7tan.com/bbs/">社区</a>
    </div>
</div>

<div class="container">

<?php if (!$user): ?>
    <!-- 未登录 -->
    <div class="login-prompt">
        <h2>🔐 请先登录</h2>
        <p style="color:#888;margin-bottom:16px;">登录后才能购买专业版</p>
        <a href="/login?redirect=/pro.php">点击登录</a>
    </div>

<?php else: ?>
    <h1 class="page-title">🚀 7Tan 专业版</h1>
    <p class="page-subtitle">解锁全部 AI 功能，效率翻倍</p>

    <!-- 当前状态 -->
    <div class="status-card">
        <div>
            <span class="status-badge <?= $is_pro ? 'status-pro' : 'status-free' ?>">
                <?= $is_pro ? '✅ 专业版' : '🆓 免费版' ?>
            </span>
            <span style="margin-left:12px;color:#ccc;"><?= htmlspecialchars($user['username'] ?? '') ?></span>
        </div>
        <div class="status-info">
            <?php if ($is_pro): ?>
                到期时间：<strong><?= date('Y-m-d H:i', $pro_expires) ?></strong>
                &nbsp;(剩余 <strong><?= ceil(($pro_expires - $now) / 86400) ?></strong> 天)
            <?php else: ?>
                当前为免费版，购买后解锁全部功能
            <?php endif; ?>
        </div>
    </div>

    <!-- 套餐选择 -->
    <div class="plan-grid" id="planGrid">
        <?php foreach ($plans as $i => $p): ?>
        <div class="plan-card <?= $p['key'] === 'semi_annual' ? 'selected' : '' ?>"
             data-plan="<?= $p['key'] ?>"
             data-months="<?= $p['months'] ?>"
             data-price="<?= $p['price'] ?>"
             onclick="selectPlan(this)">
            <?php if ($p['badge']): ?>
                <div class="plan-badge"><?= $p['badge'] ?></div>
            <?php endif; ?>
            <div class="plan-name"><?= $p['name'] ?></div>
            <div class="plan-months"><?= $p['months'] ?> 个月</div>
            <div class="plan-price">¥<?= $p['price'] ?><sub>.00</sub></div>
            <div class="plan-per-month">≈ ¥<?= $p['per_month'] ?>/月</div>
            <div class="plan-save"><?= $p['save'] > 0 ? "省 ¥{$p['save']}" : '' ?></div>
        </div>
        <?php endforeach; ?>
    </div>

    <!-- 购买按钮 -->
    <button class="btn-buy" id="btnBuy" onclick="doPurchase()">
        💳 立即购买 ¥<span id="priceDisplay">200</span>
    </button>
    <div class="msg" id="msg"></div>

<?php endif; ?>
</div>

<script>
let selectedPlan = 'semi_annual';
let selectedPrice = 200;
let selectedMonths = 6;
let purchasing = false;

function selectPlan(el) {
    document.querySelectorAll('.plan-card').forEach(c => c.classList.remove('selected'));
    el.classList.add('selected');
    selectedPlan  = el.dataset.plan;
    selectedPrice = parseInt(el.dataset.price);
    selectedMonths = parseInt(el.dataset.months);
    document.getElementById('priceDisplay').textContent = selectedPrice;
}

async function doPurchase() {
    if (purchasing) return;
    const btn = document.getElementById('btnBuy');
    const msg = document.getElementById('msg');

    if (!confirm(`确认购买 ${selectedMonths} 个月专业版？\n金额：¥${selectedPrice}.00`)) return;

    purchasing = true;
    btn.disabled = true;
    btn.textContent = '⏳ 处理中...';
    msg.className = 'msg msg-info';
    msg.textContent = '正在处理订单...';

    try {
        const resp = await fetch('/api/pro/purchase.php', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer <?= htmlspecialchars($token) ?>'
            },
            body: JSON.stringify({ plan: selectedPlan })
        });
        const data = await resp.json();
        if (data.code === 0) {
            msg.className = 'msg msg-success';
            msg.textContent = '🎉 ' + data.message + '，页面即将刷新...';
            setTimeout(() => location.reload(), 2000);
        } else {
            msg.className = 'msg msg-error';
            msg.textContent = '❌ ' + (data.message || '购买失败');
        }
    } catch (e) {
        msg.className = 'msg msg-error';
        msg.textContent = '❌ 网络错误：' + e.message;
    } finally {
        purchasing = false;
        btn.disabled = false;
        btn.textContent = '💳 立即购买 ¥' + selectedPrice;
    }
}
</script>

</body>
</html>
