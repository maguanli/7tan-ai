<?php
header('Content-Type: text/html; charset=UTF-8');
// ============================================================
// 插件购买页面（原完整版购买页升级为插件中心）
// 位置: /pro.php
// 支持: BBS 登录会话 + 余额购买插件 + 自动签发授权码
// ============================================================
?><!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>7Tan 插件中心 - 7坛游戏社区</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #1a1a2e; color: #eee; min-height: 100vh; }
        .navbar { width: 100%; max-width: 1100px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; }
        .nav-logo { font-size: 22px; font-weight: bold; color: #ff6b35; }
        .nav-logo span { color: #ccc; }
        .nav-links { display: flex; gap: 20px; }
        .nav-links a { color: #aaa; text-decoration: none; font-size: 14px; }
        .nav-links a:hover { color: #ff6b35; }
        .container { max-width: 1000px; margin: 0 auto; padding: 20px 24px 60px; }
        .page-title { font-size: 28px; margin-bottom: 6px; }
        .page-subtitle { color: #888; margin-bottom: 28px; }
        .login-prompt { text-align: center; padding: 60px 20px; background: #16213e; border-radius: 12px; }
        .login-prompt h2 { margin-bottom: 12px; color: #ff6b35; }
        .login-prompt p { color: #888; margin-bottom: 16px; }
        .login-prompt a { display: inline-block; padding: 12px 32px; background: #ff6b35; color: #fff; border-radius: 8px; text-decoration: none; font-weight: 600; }
        .login-prompt a:hover { background: #e55a2b; }
        /* 余额卡片 */
        .balance-card { background: linear-gradient(135deg, #ff6b35 0%, #e0552a 100%); border-radius: 12px; padding: 20px 28px; margin-bottom: 24px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
        .balance-card .b-label { font-size: 13px; opacity: .85; }
        .balance-card .b-amount { font-size: 32px; font-weight: 800; }
        .balance-card .b-amount small { font-size: 15px; font-weight: 400; opacity: .8; }
        .balance-actions { display: flex; gap: 10px; }
        .btn { display: inline-block; padding: 10px 22px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 14px; cursor: pointer; border: none; transition: .2s; }
        .btn-light { background: #fff; color: #ff6b35; }
        .btn-light:hover { background: #f0f0f0; }
        .btn-ghost { background: transparent; color: #fff; border: 2px solid #ffffff66; }
        .btn-ghost:hover { background: #ffffff1a; }
        .btn-primary { background: #ff6b35; color: #fff; }
        .btn-primary:hover { background: #e55a2b; }
        .btn-primary:disabled { background: #555; cursor: not-allowed; }
        /* 插件卡片 */
        .plugin-card { background: #16213e; border: 2px solid #ff6b3540; border-radius: 14px; padding: 26px; margin-bottom: 20px; }
        .plugin-head { display: flex; align-items: center; gap: 16px; margin-bottom: 14px; flex-wrap: wrap; }
        .plugin-icon { font-size: 42px; }
        .plugin-name { font-size: 22px; font-weight: 700; }
        .plugin-tag { display: inline-block; padding: 3px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; background: #ff6b3520; color: #ff6b35; margin-left: 8px; }
        .plugin-price { font-size: 26px; color: #ff6b35; font-weight: 800; margin-left: auto; }
        .plugin-price small { font-size: 13px; color: #888; font-weight: 400; }
        .plugin-desc { color: #aaa; font-size: 14px; margin-bottom: 14px; line-height: 1.7; }
        .plugin-features { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 8px 20px; margin-bottom: 18px; }
        .plugin-features li { list-style: none; color: #bbb; font-size: 13px; padding-left: 20px; position: relative; }
        .plugin-features li::before { content: "✅"; position: absolute; left: 0; top: 0; font-size: 12px; }
        .plugin-buy { background: #0f1a2e; border-radius: 10px; padding: 16px; }
        .plugin-buy label { display: block; font-size: 13px; font-weight: 600; color: #aaa; margin-bottom: 8px; }
        .fp-row { display: flex; gap: 10px; flex-wrap: wrap; }
        .fp-input { flex: 1; min-width: 260px; padding: 12px 14px; border: 1px solid #ffffff22; border-radius: 8px; background: #1a2744; color: #eee; font-size: 14px; outline: none; font-family: monospace; }
        .fp-input:focus { border-color: #ff6b35; }
        .fp-input::placeholder { color: #666; font-family: inherit; }
        .buy-btn { padding: 12px 32px; background: #ff6b35; color: #fff; border: none; border-radius: 8px; font-size: 16px; font-weight: 700; cursor: pointer; }
        .buy-btn:hover { background: #e55a2b; }
        .buy-btn:disabled { background: #555; cursor: not-allowed; }
        /* 提示 */
        .tips { background: #16213e; border-radius: 10px; padding: 16px 20px; margin-bottom: 20px; font-size: 13px; color: #999; line-height: 1.9; }
        .tips b { color: #ff6b35; }
        /* 消息 */
        .msg { text-align: center; padding: 12px; margin-top: 12px; border-radius: 8px; display: none; }
        .msg.success { background: #1b5e20; color: #a5d6a7; display: block; }
        .msg.error { background: #5e1b1b; color: #ef9a9a; display: block; }
        /* 授权码结果 */
        .license-result { background: #0f1a2e; border: 2px dashed #ff6b3580; border-radius: 10px; padding: 18px; margin-top: 16px; }
        .license-result h4 { color: #ff6b35; margin-bottom: 10px; font-size: 15px; }
        .license-box { background: #1a2744; border-radius: 8px; padding: 14px; font-family: monospace; font-size: 13px; word-break: break-all; color: #8be28b; user-select: all; margin-bottom: 12px; line-height: 1.8; }
        .copy-btn { padding: 8px 20px; background: #ff6b35; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600; }
        .copy-btn:hover { background: #e55a2b; }
        .activate-steps { font-size: 13px; color: #bbb; line-height: 2; margin-top: 10px; }
        /* 我的授权 */
        .orders-section { margin-top: 24px; }
        .orders-section h3 { font-size: 17px; margin-bottom: 12px; color: #ff6b35; }
        .order-item { background: #16213e; border-radius: 10px; padding: 14px 18px; margin-bottom: 10px; display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
        .order-item .oi-name { font-weight: 600; font-size: 14px; }
        .order-item .oi-meta { color: #888; font-size: 12px; }
        .order-item .oi-license { font-family: monospace; font-size: 11px; color: #8be28b; word-break: break-all; flex: 1; min-width: 200px; }
        .order-empty { color: #666; font-size: 13px; padding: 20px; text-align: center; }
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
            <a href="/pro.php" style="color:#ff6b35;font-weight:600;">🧩 插件</a>
        </div>
    </nav>
</div>
<div class="container">
    <h1 class="page-title">🧩 7Tan 插件中心</h1>
    <p class="page-subtitle">软件本体完全免费，个别高级插件需付费解锁（永久授权，绑定购买时电脑）。</p>
    <div id="app"><p style="text-align:center;color:#888;padding:40px;">加载中...</p></div>
</div>

<script>
function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function fmtYuan(cents) {
    return (Number(cents) / 100).toFixed(2);
}

function renderPlugin(p) {
    return `
    <div class="plugin-card">
        <div class="plugin-head">
            <span class="plugin-icon">${p.icon}</span>
            <div>
                <span class="plugin-name">${escHtml(p.name)}</span>
                <span class="plugin-tag">${p.type === 'per_device' ? '按台永久授权' : '订阅'}</span>
            </div>
            <div class="plugin-price">¥${p.price_yuan}<small> / 台 永久</small></div>
        </div>
        <p class="plugin-desc">${escHtml(p.desc)}</p>
        <ul class="plugin-features">${(p.features||[]).map(f => '<li>'+escHtml(f)+'</li>').join('')}</ul>
        <div class="plugin-buy">
            <label>🖥️ 机器指纹（32 位，在软件「爆款写作」插件状态页点击复制）</label>
            <div class="fp-row">
                <input class="fp-input" id="fpInput" placeholder="例如：a1b2c3d4e5f60718293a4b5c6d7e8f90" autocomplete="off">
                <button class="buy-btn" id="buyBtn" onclick="doBuy('${p.id}')">💰 余额购买 ¥${p.price_yuan}</button>
            </div>
            <div class="msg" id="msg"></div>
            <div id="result"></div>
        </div>
    </div>`;
}

function renderOrders(orders) {
    if (!orders || !orders.length) return '<div class="order-empty">暂无购买记录</div>';
    return orders.map(o => `
        <div class="order-item">
            <span class="oi-name">${escHtml(o.plugin_name)}</span>
            <span class="oi-meta">${escHtml(o.fingerprint.slice(0,8))}… · ${escHtml(o.created_at)}</span>
            <span class="oi-license">${escHtml(o.license_key)}</span>
            <button class="copy-btn" onclick="copyText(this, '${escHtml(o.license_key).replace(/'/g, "\\'")}')">复制</button>
        </div>`).join('');
}

async function copyText(btn, text) {
    try {
        await navigator.clipboard.writeText(text);
        btn.textContent = '✅ 已复制';
        setTimeout(() => btn.textContent = '复制', 1500);
    } catch (e) {
        const ta = document.createElement('textarea');
        ta.value = text; document.body.appendChild(ta); ta.select();
        document.execCommand('copy'); ta.remove();
        btn.textContent = '✅ 已复制';
        setTimeout(() => btn.textContent = '复制', 1500);
    }
}

async function doBuy(pluginId) {
    const msg = document.getElementById('msg');
    const btn = document.getElementById('buyBtn');
    const fp = (document.getElementById('fpInput').value || '').trim().toLowerCase();
    if (!fp) { msg.className = 'msg error'; msg.style.display = ''; msg.textContent = '❌ 请先填写机器指纹'; return; }
    if (!/^[0-9a-f]{32}$/.test(fp)) { msg.className = 'msg error'; msg.style.display = ''; msg.textContent = '❌ 指纹格式不正确（应为 32 位十六进制）'; return; }
    btn.disabled = true; btn.textContent = '处理中...';
    msg.className = 'msg'; msg.style.display = 'none';
    document.getElementById('result').innerHTML = '';
    try {
        const resp = await fetch('/api/plugin/purchase.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ plugin_id: pluginId, fingerprint: fp })
        });
        const data = await resp.json();
        if (data.code === 0) {
            msg.style.display = '';
            msg.className = 'msg success';
            msg.textContent = '✅ ' + (data.message || '购买成功');
            document.getElementById('result').innerHTML = `
                <div class="license-result">
                    <h4>🔑 授权码（复制后在软件中激活）</h4>
                    <div class="license-box">${escHtml(data.data.license_key)}</div>
                    <button class="copy-btn" onclick="copyText(this, '${escHtml(data.data.license_key).replace(/'/g, "\\'")}')">📋 复制授权码</button>
                    <div class="activate-steps">
                        <b>激活步骤：</b><br>
                        ① 打开 7Tan 软件 → 插件市场 → 爆款写作<br>
                        ② 输入命令 <b>viral_activate</b>，粘贴授权码回车<br>
                        ③ 激活成功，永久使用全部功能 ✅
                    </div>
                </div>`;
            setTimeout(() => location.reload(), 4000);
        } else {
            msg.style.display = '';
            msg.className = 'msg error';
            if (data.recharge_url) {
                msg.innerHTML = '❌ ' + escHtml(data.message) + '<br><br><a href="' + escHtml(data.recharge_url) + '" style="display:inline-block;padding:10px 24px;background:#ff6b35;color:#fff;border-radius:6px;text-decoration:none;font-weight:600;">💰 去充值</a>';
            } else {
                msg.textContent = '❌ ' + (data.message || '购买失败');
            }
        }
    } catch (e) {
        msg.style.display = '';
        msg.className = 'msg error';
        msg.textContent = '网络错误：' + e.message;
    } finally {
        btn.disabled = false; btn.textContent = '💰 余额购买 ¥' + (window.CURRENT_PRICE || 50);
    }
}

async function init() {
    const app = document.getElementById('app');
    try {
        const resp = await fetch('/api/plugin/list.php', { credentials: 'include' });
        const json = await resp.json();
        if (json.code !== 0) {
            if (json.need_login) {
                app.innerHTML = '<div class="login-prompt"><h2>请先登录</h2><p>登录后即可使用余额购买插件</p><a href="/bbs/login.php?redirect=/pro.php">立即登录</a></div>';
                return;
            }
            app.innerHTML = '<div class="login-prompt"><h2>加载失败</h2><p>' + escHtml(json.message || '') + '</p><a href="javascript:location.reload()">重试</a></div>';
            return;
        }
        const d = json.data || {};
        const b = d.balance || {};
        window.CURRENT_PRICE = (d.plugins && d.plugins[0]) ? d.plugins[0].price_yuan : 50;
        const pluginsHtml = (d.plugins || []).map(renderPlugin).join('');
        app.innerHTML = `
            <div class="balance-card">
                <div>
                    <div class="b-label">💰 我的余额（可用）</div>
                    <div class="b-amount">¥${Number(b.available_yuan || 0).toFixed(2)}<small> &nbsp;总余额 ¥${Number(b.balance_yuan || 0).toFixed(2)}</small></div>
                </div>
                <div class="balance-actions">
                    <a href="/task/wallet.php" class="btn btn-light">💳 充值</a>
                    <a href="/api/logout.php" class="btn btn-ghost">退出</a>
                </div>
            </div>
            <div class="tips">
                📌 <b>购买流程</b>：① 打开 7Tan 软件 → 插件市场 → 爆款写作 → 查看状态，复制「机器指纹」→ ② 粘贴到下方输入框 → ③ 点击「余额购买」，系统自动扣款并生成授权码 → ④ 复制授权码，在软件中运行 <b>viral_activate</b> 输入即可激活。<br>
                💡 未购买用户可免费试用 5 次；授权码<b>绑定当前电脑</b>，换机/重装可联系作者免费补发。
            </div>
            ${pluginsHtml}
            <div class="orders-section">
                <h3>📦 我的授权</h3>
                ${renderOrders(d.orders || [])}
            </div>`;
    } catch (e) {
        app.innerHTML = '<div class="login-prompt"><h2>加载失败</h2><p>' + escHtml(e.message) + '</p><a href="javascript:location.reload()">重试</a></div>';
    }
}

init();
</script>
</body>
</html>
