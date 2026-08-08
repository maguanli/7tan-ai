<?php
header('Content-Type: text/html; charset=UTF-8');
// ============================================================
// 购买完整版页面
// 位置: /pro.php
// 前端 JS 驱动验证，支持 BBS 登录 + auth_token Cookie 双通道
// ============================================================
?><!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>7Tan 完整版 - 7坛游戏社区</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #1a1a2e; color: #eee; min-height: 100vh; }
        .navbar { width: 100%; max-width: 1100px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; }
        .nav-logo { font-size: 22px; font-weight: bold; color: #ff6b35; }
        .nav-logo span { color: #ccc; }
        .nav-links { display: flex; gap: 20px; }
        .nav-links a { color: #aaa; text-decoration: none; font-size: 14px; }
        .nav-links a:hover { color: #ff6b35; }
        .container { max-width: 900px; margin: 0 auto; padding: 20px 24px 60px; }
        .page-title { font-size: 28px; margin-bottom: 6px; }
        .page-subtitle { color: #888; margin-bottom: 28px; }
        .login-prompt { text-align: center; padding: 60px 20px; background: #16213e; border-radius: 12px; }
        .login-prompt h2 { margin-bottom: 12px; color: #ff6b35; }
        .login-prompt p { color: #888; margin-bottom: 16px; }
        .login-prompt a { display: inline-block; padding: 12px 32px; background: #ff6b35; color: #fff; border-radius: 8px; text-decoration: none; font-weight: 600; }
        .login-prompt a:hover { background: #e55a2b; }
        .plan-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .plan-card { background: #16213e; border: 2px solid transparent; border-radius: 12px; padding: 24px; text-align: center; cursor: pointer; transition: all 0.2s; }
        .plan-card:hover { border-color: #ff6b3540; }
        .plan-card.selected { border-color: #ff6b35; background: #1a2744; }
        .plan-card .plan-name { font-size: 18px; font-weight: 600; margin-bottom: 8px; }
        .plan-card .plan-price { font-size: 28px; color: #ff6b35; font-weight: bold; margin-bottom: 8px; }
        .plan-card .plan-price small { font-size: 14px; color: #888; }
        .plan-card .plan-desc { color: #888; font-size: 13px; }
        .buy-btn { width: 100%; padding: 16px; background: #ff6b35; color: #fff; border: none; border-radius: 10px; font-size: 18px; font-weight: 600; cursor: pointer; }
        .buy-btn:hover { background: #e55a2b; }
        .buy-btn:disabled { background: #555; cursor: not-allowed; }
        .msg { text-align: center; padding: 12px; margin-top: 12px; border-radius: 8px; display: none; }
        .msg.success { background: #1b5e20; color: #a5d6a7; display: block; }
        .msg.error { background: #5e1b1b; color: #ef9a9a; display: block; }
        .status-card { background: #16213e; border-radius: 12px; padding: 24px; margin-bottom: 24px; display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
        .status-badge { display: inline-block; padding: 6px 16px; border-radius: 20px; font-size: 13px; font-weight: 600; }
        .status-pro { background: #ff6b3520; color: #ff6b35; }
        .status-free { background: #8883; color: #aaa; }
        .toggle-renew-btn { background: transparent; border: 2px solid #ff6b35; color: #ff6b35; padding: 10px 24px; border-radius: 8px; cursor: pointer; font-size: 15px; font-weight: 600; width: 100%; }
        .toggle-renew-btn:hover { background: #ff6b3520; }
        .renew-section { background: #16213e; border-radius: 12px; padding: 20px; margin-top: 16px; }
        .charge-btn { display: inline-block; padding: 8px 18px; background: #ff6b35; color: #fff; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 14px; margin-right: 12px; }
        .charge-btn:hover { background: #e55a2b; }
    </style>
</head>
<body>
<div style="border-bottom:1px solid #ffffff0a;">
    <nav class="navbar">
        <a href="/" class="nav-logo" style="text-decoration:none;">7Tan<span>.com</span></a>
        <div class="nav-links">
            <a href="/">首页</a>
            <a href="/game/">安卓游戏</a>
            <a href="/bbs/">社区</a>
            <a href="/pro.php" style="color:#ff6b35;font-weight:600;">💰 完整版</a>
        </div>
    </nav>
</div>
<div class="container">
    <h1 class="page-title">🚀 7Tan 完整版</h1>
    <p class="page-subtitle">解锁全部 AI 功能，效率翻倍，软件可以修改自己进行升级进化，功能强大。</p>
    <div id="app"></div>
</div>
<script>
// ========== 配置 ==========
const PLANS = [
    { id: 'monthly', name: '月付', price: 50, months: 1, label: '',      desc: '适合短期使用' },
    { id: 'quarterly', name: '季付', price: 120, months: 3, label: '⭐ 推荐', desc: '平均每月仅 ¥40，省 20%' },
    { id: 'semi_annual', name: '半年付', price: 200, months: 6, label: '🔥 最火', desc: '平均每月仅 ¥33.3，省 33%' },
    { id: 'annual', name: '年付', price: 350, months: 12, label: '👑 最省', desc: '平均每月仅 ¥29.2，省 42%' }
];

let selectedPlan = PLANS[0].id;
let selectedMonths = PLANS[0].months;
let selectedPrice = PLANS[0].price;
let purchasing = false;

function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function renderPlans() {
    return PLANS.map((p, i) => `
        <div class="plan-card${i === 0 ? ' selected' : ''}" data-plan="${p.id}" data-months="${p.months}" data-price="${p.price}" onclick="selectPlan(this)">
            <div class="plan-name">${p.name} ${p.label}</div>
            <div class="plan-price">¥${p.price}<small>/${p.months}个月</small></div>
            <div class="plan-desc">${p.desc}</div>
        </div>
    `).join('');
}

function selectPlan(el) {
    document.querySelectorAll('.plan-card').forEach(c => c.classList.remove('selected'));
    el.classList.add('selected');
    selectedPlan = el.dataset.plan;
    selectedMonths = parseInt(el.dataset.months);
    selectedPrice = parseInt(el.dataset.price);
    const btn = document.getElementById('buyBtn');
    if (btn) btn.textContent = '💰 立即购买 ¥' + selectedPrice;
    const renewBtn = document.getElementById('renewBtn');
    if (renewBtn) renewBtn.textContent = '🔄 续费会员 ¥' + selectedPrice;
}

async function doBuy() {
    if (purchasing) return;
    const msg = document.getElementById('msg');
    const btn = document.getElementById('buyBtn');
    if (!msg || !btn) return;
    purchasing = true;
    btn.disabled = true;
    btn.textContent = '处理中...';
    msg.className = 'msg';
    msg.style.display = 'none';
    try {
        const body = JSON.stringify({ action: 'buy', plan: selectedPlan, months: selectedMonths });
        const resp = await fetch('/api/pro/purchase.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body
        });
        const data = await resp.json();
        if (data.code === 0) {
            msg.style.display = '';
            msg.className = 'msg success';
            msg.textContent = '✅ ' + (data.message || '购买成功') + '，页面即将刷新...';
            setTimeout(() => location.reload(), 2000);
        } else {
            msg.style.display = '';
            msg.className = 'msg error';
            if (data.recharge_url) {
                msg.innerHTML = '❌ ' + escHtml(data.message || '购买失败') + '<br><br><a href="' + escHtml(data.recharge_url) + '" style="display:inline-block;padding:10px 24px;background:#ff6b35;color:#fff;border-radius:6px;text-decoration:none;font-weight:600;">💰 去充值</a>';
            } else {
                msg.textContent = '❌ ' + (data.message || '购买失败');
            }
        }
    } catch (e) {
        msg.style.display = '';
        msg.className = 'msg error';
        msg.textContent = '网络错误：' + e.message;
    } finally {
        purchasing = false;
        btn.disabled = false;
        btn.textContent = '💰 立即购买 ¥' + selectedPrice;
    }
}

function toggleRenew() {
    const section = document.getElementById('renewSection');
    const toggleBtn = document.getElementById('toggleRenewBtn');
    if (!section || !toggleBtn) return;
    if (section.style.display === 'none' || section.style.display === '') {
        section.style.display = 'block';
        toggleBtn.textContent = '🔽 收起续费';
    } else {
        section.style.display = 'none';
        toggleBtn.textContent = '💳 续费会员';
    }
}

async function doRenew() {
    if (purchasing) return;
    const msg = document.getElementById('msg');
    const btn = document.getElementById('renewBtn');
    if (!msg || !btn) return;
    purchasing = true;
    btn.disabled = true;
    btn.textContent = '处理中...';
    msg.className = 'msg';
    msg.style.display = 'none';
    try {
        const body = JSON.stringify({ action: 'renew', plan: selectedPlan, months: selectedMonths });
        const resp = await fetch('/api/pro/purchase.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body
        });
        const data = await resp.json();
        if (data.code === 0) {
            msg.style.display = '';
            msg.className = 'msg success';
            msg.textContent = '✅ ' + (data.message || '续费成功') + '，页面即将刷新...';
            setTimeout(() => location.reload(), 2000);
        } else {
            msg.style.display = '';
            msg.className = 'msg error';
            if (data.recharge_url) {
                msg.innerHTML = '❌ ' + escHtml(data.message || '续费失败') + '<br><br><a href="' + escHtml(data.recharge_url) + '" style="display:inline-block;padding:10px 24px;background:#ff6b35;color:#fff;border-radius:6px;text-decoration:none;font-weight:600;">💰 去充值</a>';
            } else {
                msg.textContent = '❌ ' + (data.message || '续费失败');
            }
        }
    } catch (e) {
        msg.style.display = '';
        msg.className = 'msg error';
        msg.textContent = '网络错误：' + e.message;
    } finally {
        purchasing = false;
        btn.disabled = false;
        btn.textContent = '🔄 续费会员 ¥' + selectedPrice;
    }
}

async function init() {
    const app = document.getElementById('app');
    const plansHtml = renderPlans();

    try {
        const resp = await fetch('/api/pro/status.php', { credentials: 'include' });
        const json = await resp.json();
        const d = json.data || {};

        if (json.code === 0 && d.pro_activated === 1) {
            app.innerHTML = '<div class="status-card"><span class="status-badge status-pro">✅ 完整版</span><span style="color:#aaa;">' + escHtml(d.username || '') + '</span><span style="margin-left:auto;display:flex;align-items:center;gap:8px;"><a href="https://www.7tan.com/task/wallet.php" class="charge-btn">💰 充值</a>到期时间：' + escHtml(d.pro_expires_at || '') + ' (剩余 ' + (d.remaining_days || 0) + ' 天)</span></div><div class="renew-section" id="renewSection" style="display:none;"><h3 style="text-align:center;margin:16px 0 12px;color:#ff6b35;">🔄 续费会员</h3><p style="text-align:center;color:#888;font-size:13px;margin-bottom:16px;">续费时长将叠加到现有到期时间上</p><div class="plan-grid" id="planGrid">' + plansHtml + '</div><button class="buy-btn" id="renewBtn" onclick="doRenew()">🔄 续费会员 ¥' + selectedPrice + '</button></div><div class="msg" id="msg"></div><div style="text-align:center;padding:16px;"><button class="toggle-renew-btn" id="toggleRenewBtn" onclick="toggleRenew()">💳 续费会员</button></div><p style="text-align:center;color:#888;padding:10px;">🎉 您已是完整版用户，享受全部 AI 功能</p>';
        } else if (json.code === 0) {
            app.innerHTML = '<p style="text-align:center;color:#888;padding:16px;">登录身份：' + escHtml(d.username || '') + ' | <a href="/api/logout.php" style="color:#ff6b35;">退出</a></p><div class="plan-grid">' + plansHtml + '</div><div class="msg" id="msg"></div><button class="buy-btn" id="buyBtn" onclick="doBuy()">💰 立即购买 ¥' + selectedPrice + '</button>';
        } else {
            app.innerHTML = '<div class="login-prompt"><h2>请先登录</h2><p>登录后才能查看完整版方案</p><a href="/bbs/login.php?redirect=/pro.php">立即登录</a></div>';
        }
    } catch (e) {
        app.innerHTML = '<div class="login-prompt"><h2>加载失败</h2><p>' + escHtml(e.message) + '</p><a href="javascript:location.reload()">重试</a></div>';
    }
}

init();
</script>
</body>
</html>