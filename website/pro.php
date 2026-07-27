<?php
// ============================================================
// 购买专业版页面
// 位置: /pro.php
// 前端 JS 驱动验证，支持 BBS 登录 + auth_token Cookie 双通道
// ============================================================
?><!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>7Tan 专业版 - 7坛游戏社区</title>
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
        .login-prompt a:hover { background: #e85d2c; }
        .status-card { background: #16213e; border-radius: 12px; padding: 20px 24px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
        .status-badge { padding: 4px 14px; border-radius: 20px; font-size: 13px; font-weight: 600; }
        .status-pro { background: #ff6b35; color: #fff; }
        .status-free { background: #333; color: #aaa; }
        .status-info { color: #888; font-size: 14px; }
        .plan-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .plan-card { background: #16213e; border-radius: 12px; padding: 24px; text-align: center; cursor: pointer; border: 2px solid transparent; transition: all 0.2s; position: relative; }
        .plan-card:hover { border-color: #444; }
        .plan-card.selected { border-color: #ff6b35; background: #1e2a4a; }
        .plan-badge { position: absolute; top: -10px; right: -10px; background: #ff6b35; color: #fff; font-size: 12px; padding: 3px 10px; border-radius: 12px; font-weight: 600; }
        .plan-name { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
        .plan-months { color: #888; font-size: 13px; margin-bottom: 12px; }
        .plan-price { font-size: 32px; font-weight: bold; color: #ff6b35; }
        .plan-price sub { font-size: 16px; color: #888; }
        .plan-per-month { color: #666; font-size: 12px; margin-top: 4px; }
        .buy-btn { width: 100%; padding: 14px; background: #ff6b35; color: #fff; border: none; border-radius: 10px; font-size: 18px; font-weight: 600; cursor: pointer; }
        .buy-btn:disabled { background: #555; cursor: not-allowed; }
        .buy-btn:hover:not(:disabled) { background: #e85d2c; }
        .msg { margin-top: 12px; padding: 12px; border-radius: 8px; display: none; }
        .msg-success { background: #0d3b1a; color: #4ade80; }
        .msg-error { background: #3b0d0d; color: #f87171; }
        .loading { text-align: center; padding: 60px; color: #888; }
        .loading .spinner { display: inline-block; width: 36px; height: 36px; border: 3px solid #333; border-top-color: #ff6b35; border-radius: 50%; animation: spin 0.8s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
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
    <div id="app">
        <div class="loading"><div class="spinner"></div><p style="margin-top:16px;">加载中...</p></div>
    </div>
</div>

<script>
// ============================================================
// 全局状态
// ============================================================
let userData = null;
let selectedPlan = 'semi_annual';
let selectedMonths = 6;
let selectedPrice = 99;
let purchasing = false;

const plans = [
    { key: 'monthly',     name: '月度',    months: 1,  price: 19,  perMonth: 19,  badge: '' },
    { key: 'quarterly',   name: '季度',    months: 3,  price: 49,  perMonth: 16, badge: '' },
    { key: 'semi_annual', name: '半年',    months: 6,  price: 99,  perMonth: 17, badge: '🔥推荐' },
    { key: 'annual',      name: '年度',    months: 12, price: 179, perMonth: 15, badge: '💎超值' },
];

// ============================================================
// 初始化
// ============================================================
async function init() {
    try {
        const resp = await fetch('/api/auth/verify.php', { credentials: 'include' });
        const data = await resp.json();

        if (data.code === 0 && data.data) {
            userData = data.data;
            // 如果服务器返回了 token，写入 Cookie
            if (data.data.token) {
                document.cookie = 'auth_token=' + data.data.token + '; path=/; max-age=2592000; SameSite=Lax';
            }
            renderLoggedIn();
        } else {
            renderLoginPrompt();
        }
    } catch (e) {
        renderLoginPrompt();
    }
}

// ============================================================
// 渲染：已登录
// ============================================================
function renderLoggedIn() {
    const u = userData;
    const isPro = u.level === 'pro';
    const expiresDate = u.pro_expires > 0 ? new Date(u.pro_expires * 1000).toLocaleString('zh-CN') : '';
    const remainingDays = u.pro_expires > 0 ? Math.ceil((u.pro_expires - u.server_time) / 86400) : 0;

    let plansHtml = plans.map((p, i) => `
        <div class="plan-card ${p.key === selectedPlan ? 'selected' : ''}"
             data-plan="${p.key}" data-months="${p.months}" data-price="${p.price}"
             onclick="selectPlan(this)">
            ${p.badge ? '<div class="plan-badge">' + p.badge + '</div>' : ''}
            <div class="plan-name">${p.name}</div>
            <div class="plan-months">${p.months} 个月</div>
            <div class="plan-price">¥${p.price}<sub>.00</sub></div>
            <div class="plan-per-month">≈ ¥${p.perMonth}/月</div>
        </div>
    `).join('');

    let statusHtml;
    if (isPro) {
        statusHtml = `
            <div class="status-card">
                <div>
                    <span class="status-badge status-pro">✅ 专业版</span>
                    <span style="margin-left:12px;color:#ccc;">${escHtml(u.username)}</span>
                </div>
                <div class="status-info">
                    到期时间：<strong>${expiresDate}</strong>
                    &nbsp;(剩余 <strong>${remainingDays}</strong> 天)
                </div>
            </div>
            <p style="text-align:center;color:#888;padding:20px;">🎉 你已是专业版用户，享受全部 AI 功能</p>`;
    } else {
        statusHtml = `
            <div class="status-card">
                <div>
                    <span class="status-badge status-free">🆓 免费版</span>
                    <span style="margin-left:12px;color:#ccc;">${escHtml(u.username)}</span>
                </div>
                <div class="status-info">当前为免费版，购买后解锁全部功能</div>
            </div>
            <div class="plan-grid" id="planGrid">${plansHtml}</div>
            <button class="buy-btn" id="buyBtn" onclick="doPurchase()">💳 立即购买 ¥${selectedPrice}</button>
            <div class="msg" id="msg"></div>`;
    }

    document.getElementById('app').innerHTML = `
        <h1 class="page-title">🚀 7Tan 专业版</h1>
        <p class="page-subtitle">解锁全部 AI 功能，效率翻倍</p>
        ${statusHtml}
    `;
}

// ============================================================
// 渲染：未登录
// ============================================================
function renderLoginPrompt() {
    document.getElementById('app').innerHTML = `
        <div class="login-prompt">
            <h2>🔐 请先登录</h2>
            <p>登录后才能查看和购买专业版</p>
            <a href="/bbs/login.php?redirect=/pro.php">点击登录</a>
            <p style="margin-top:12px;font-size:12px;color:#666;">登录后自动返回此页面</p>
        </div>
    `;
}

// ============================================================
// 选择套餐
// ============================================================
function selectPlan(el) {
    document.querySelectorAll('.plan-card').forEach(c => c.classList.remove('selected'));
    el.classList.add('selected');
    selectedPlan = el.dataset.plan;
    selectedMonths = parseInt(el.dataset.months);
    selectedPrice = parseInt(el.dataset.price);
    const btn = document.getElementById('buyBtn');
    if (btn) btn.textContent = '💳 立即购买 ¥' + selectedPrice;
}

// ============================================================
// 购买
// ============================================================
async function doPurchase() {
    if (purchasing) return;
    const btn = document.getElementById('buyBtn');
    const msg = document.getElementById('msg');
    if (!btn || !msg) return;

    purchasing = true;
    btn.disabled = true;
    btn.textContent = '处理中...';
    msg.style.display = 'none';

    try {
        const resp = await fetch('/api/pro/purchase.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ plan: selectedPlan, months: selectedMonths, price: selectedPrice }),
        });
        const data = await resp.json();
        msg.style.display = 'block';
        if (data.code === 0) {
            msg.className = 'msg msg-success';
            msg.textContent = '✅ ' + (data.message || '购买成功') + '，页面即将刷新...';
            setTimeout(() => location.reload(), 2000);
        } else {
            msg.className = 'msg msg-error';
            msg.textContent = '❌ ' + (data.message || '购买失败');
        }
    } catch (e) {
        msg.style.display = 'block';
        msg.className = 'msg msg-error';
        msg.textContent = '❌ 网络错误：' + e.message;
    } finally {
        purchasing = false;
        btn.disabled = false;
        btn.textContent = '💳 立即购买 ¥' + selectedPrice;
    }
}

function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// 启动
init();
</script>

</body>
</html>
