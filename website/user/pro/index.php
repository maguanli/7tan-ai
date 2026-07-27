<?php
// ============================================================
// B5c: 购买专业版页面（前端）
// 位置: /user/pro/index.php
// 需要放在网站已有的用户认证框架内（如 Session 登录）
// ============================================================

// 假设网站已有 $current_user 变量（通过 Session 获取）
// 如果没有，请根据网站实际框架调整
if (empty($current_user)) {
    header('Location: /login?redirect=/user/pro');
    exit;
}

$uid           = $current_user['id'];
$username      = $current_user['username'];
$pro_activated = (int)($current_user['pro_activated'] ?? 0);
$pro_expires   = (int)($current_user['pro_expires']   ?? 0);
$now           = time();
$is_pro        = ($pro_activated === 1 && $pro_expires > $now);

// 查询余额
$db      = get_db_connection();
$stmt    = $db->prepare('SELECT balance FROM user_balance WHERE user_id = :uid LIMIT 1');
$stmt->execute([':uid' => $uid]);
$balance = (float)($stmt->fetchColumn() ?: 0);

// 套餐定义
$plans = [
    ['key' => 'monthly',     'name' => '月付',   'months' => 1,  'price' => 50,  'per_month' => 50,  'save' => 0,   'badge' => ''],
    ['key' => 'quarterly',   'name' => '季付',   'months' => 3,  'price' => 120, 'per_month' => 40,  'save' => 30,  'badge' => '⭐ 推荐'],
    ['key' => 'semi_annual', 'name' => '半年付', 'months' => 6,  'price' => 200, 'per_month' => 33,  'save' => 100, 'badge' => '🔥 最火'],
    ['key' => 'annual',      'name' => '年付',   'months' => 12, 'price' => 350, 'per_month' => 29,  'save' => 250, 'badge' => '👑 最省'],
];
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>购买专业版 - 7Tan</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }
        .container { max-width: 900px; margin: 0 auto; padding: 40px 20px; }
        h1 { text-align: center; font-size: 28px; margin-bottom: 8px; color: #f1f5f9; }
        .subtitle { text-align: center; color: #94a3b8; margin-bottom: 40px; }

        /* 当前状态卡片 */
        .status-card {
            background: linear-gradient(135deg, #1e293b, #1a2332);
            border: 1px solid #334155;
            border-radius: 16px;
            padding: 24px 32px;
            margin-bottom: 32px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 16px;
        }
        .status-card.pro { border-color: #f59e0b; background: linear-gradient(135deg, #1e1b0f, #1a180a); }
        .status-info { display: flex; align-items: center; gap: 12px; }
        .status-icon { font-size: 36px; }
        .status-title { font-size: 18px; font-weight: 600; }
        .status-detail { color: #94a3b8; font-size: 14px; margin-top: 4px; }
        .status-expiry { color: #f59e0b; font-weight: 600; }
        .status-expiry.soon { color: #f97316; }
        .status-expiry.expired { color: #ef4444; }
        .balance-badge {
            background: #1e293b;
            border: 1px solid #475569;
            border-radius: 12px;
            padding: 12px 20px;
            text-align: center;
        }
        .balance-amount { font-size: 28px; font-weight: 700; color: #22c55e; }
        .balance-label { font-size: 13px; color: #94a3b8; margin-top: 2px; }
        .balance-action { display: inline-block; margin-top: 8px; font-size: 13px; color: #60a5fa; text-decoration: none; }
        .balance-action:hover { text-decoration: underline; }

        /* 套餐选择 */
        .plan-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }
        .plan-card {
            background: #1e293b;
            border: 2px solid #334155;
            border-radius: 16px;
            padding: 24px 20px;
            cursor: pointer;
            transition: all 0.2s;
            position: relative;
            text-align: center;
        }
        .plan-card:hover { border-color: #475569; transform: translateY(-2px); }
        .plan-card.selected { border-color: #3b82f6; background: #1e293b; box-shadow: 0 0 20px rgba(59,130,246,0.2); }
        .plan-badge {
            position: absolute;
            top: -12px;
            left: 50%;
            transform: translateX(-50%);
            background: #3b82f6;
            color: #fff;
            font-size: 12px;
            font-weight: 600;
            padding: 2px 12px;
            border-radius: 20px;
            white-space: nowrap;
        }
        .plan-name { font-size: 20px; font-weight: 700; margin-bottom: 8px; color: #f1f5f9; }
        .plan-price { font-size: 36px; font-weight: 800; color: #fff; }
        .plan-price span { font-size: 16px; font-weight: 400; color: #94a3b8; }
        .plan-per-month { font-size: 14px; color: #94a3b8; margin-top: 4px; }
        .plan-save { font-size: 13px; color: #22c55e; margin-top: 8px; }
        .plan-radio { margin-top: 12px; }

        /* 购买按钮 */
        .buy-section { text-align: center; }
        .btn-buy {
            display: inline-block;
            background: linear-gradient(135deg, #3b82f6, #2563eb);
            color: #fff;
            font-size: 18px;
            font-weight: 700;
            padding: 16px 48px;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-buy:hover { background: linear-gradient(135deg, #2563eb, #1d4ed8); transform: translateY(-1px); box-shadow: 0 8px 24px rgba(59,130,246,0.3); }
        .btn-buy:disabled { background: #475569; cursor: not-allowed; transform: none; box-shadow: none; }
        .buy-hint { color: #94a3b8; font-size: 14px; margin-top: 12px; }
        .buy-hint a { color: #60a5fa; }

        /* 消息提示 */
        .toast {
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            padding: 14px 28px;
            border-radius: 10px;
            font-weight: 600;
            z-index: 1000;
            display: none;
            animation: slideDown 0.3s ease;
        }
        .toast.success { background: #22c55e; color: #fff; }
        .toast.error { background: #ef4444; color: #fff; }
        @keyframes slideDown { from { opacity: 0; transform: translateX(-50%) translateY(-20px); } to { opacity: 1; transform: translateX(-50%) translateY(0); } }
    </style>
</head>
<body>
<div class="container">
    <h1>🚀 升级专业版</h1>
    <p class="subtitle">解锁所有高级功能，提升工作效率</p>

    <!-- 当前状态 -->
    <div class="status-card <?= $is_pro ? 'pro' : '' ?>">
        <div class="status-info">
            <span class="status-icon"><?= $is_pro ? '👑' : '👤' ?></span>
            <div>
                <div class="status-title">
                    <?php if ($is_pro): ?>
                        专业版会员
                    <?php else: ?>
                        免费版
                    <?php endif; ?>
                </div>
                <?php if ($is_pro): ?>
                    <?php
                        $remaining = max(0, (int)(($pro_expires - $now) / 86400));
                        $expiry_class = $remaining <= 7 ? 'soon' : '';
                    ?>
                    <div class="status-detail">
                        <?= $remaining ?> 天后到期
                        <span class="status-expiry <?= $expiry_class ?>">(<?= date('Y-m-d', $pro_expires) ?>)</span>
                    </div>
                <?php else: ?>
                    <div class="status-detail">升级解锁全部功能</div>
                <?php endif; ?>
            </div>
        </div>
        <div class="balance-badge">
            <div class="balance-amount">¥<?= number_format($balance, 2) ?></div>
            <div class="balance-label">账户余额</div>
            <a href="/user/recharge" class="balance-action">💰 充值</a>
        </div>
    </div>

    <!-- 套餐选择 -->
    <div class="plan-grid" id="planGrid">
        <?php foreach ($plans as $i => $p): ?>
        <div class="plan-card <?= $p['key'] === 'semi_annual' ? 'selected' : '' ?>"
             data-plan="<?= $p['key'] ?>"
             data-price="<?= $p['price'] ?>"
             onclick="selectPlan(this)">
            <?php if ($p['badge']): ?>
            <div class="plan-badge"><?= $p['badge'] ?></div>
            <?php endif; ?>
            <div class="plan-name"><?= $p['name'] ?></div>
            <div class="plan-price">¥<?= $p['price'] ?><span>/<?= $p['months'] ?>个月</span></div>
            <div class="plan-per-month">≈¥<?= $p['per_month'] ?>/月</div>
            <?php if ($p['save'] > 0): ?>
            <div class="plan-save">省 ¥<?= $p['save'] ?></div>
            <?php endif; ?>
            <div class="plan-radio">
                <input type="radio" name="plan" value="<?= $p['key'] ?>" <?= $p['key'] === 'semi_annual' ? 'checked' : '' ?>>
            </div>
        </div>
        <?php endforeach; ?>
    </div>

    <!-- 购买按钮 -->
    <div class="buy-section">
        <button class="btn-buy" id="btnBuy" onclick="purchase()">
            立即购买 — ¥<span id="btnPrice">200</span>
        </button>
        <p class="buy-hint">
            余额不足？<a href="/user/recharge">先去充值 →</a>
        </p>
    </div>
</div>

<div class="toast" id="toast"></div>

<script>
let selectedPlan = 'semi_annual';
let selectedPrice = 200;

function selectPlan(card) {
    document.querySelectorAll('.plan-card').forEach(c => c.classList.remove('selected'));
    card.classList.add('selected');
    selectedPlan = card.dataset.plan;
    selectedPrice = parseInt(card.dataset.price);
    card.querySelector('input[type=radio]').checked = true;
    document.getElementById('btnPrice').textContent = selectedPrice;
}

document.querySelectorAll('input[name=plan]').forEach(radio => {
    radio.addEventListener('change', function() {
        const card = this.closest('.plan-card');
        selectPlan(card);
    });
});

async function purchase() {
    const btn = document.getElementById('btnBuy');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '处理中...';

    try {
        const resp = await fetch('/api/pro/purchase.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ plan: selectedPlan })
        });
        const data = await resp.json();

        if (data.code === 0) {
            showToast('🎉 购买成功！专业版已激活', 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showToast('❌ ' + data.message, 'error');
            btn.disabled = false;
            btn.textContent = originalText;
        }
    } catch (err) {
        showToast('❌ 网络错误，请重试', 'error');
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

function showToast(msg, type) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = 'toast ' + type;
    t.style.display = 'block';
    setTimeout(() => t.style.display = 'none', 3000);
}
</script>
</body>
</html>
