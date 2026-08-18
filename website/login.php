<?php
// ============================================================
// 登录页面
// 位置: /login.php
// 从 ?redirect=xxx 获取登录后跳转地址
// ============================================================

$redirect = $_GET['redirect'] ?? '/pro.php';
// 安全：只允许相对路径
if (!preg_match('#^/[a-zA-Z0-9_./]*$#', $redirect)) {
    $redirect = '/pro.php';
}
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>登录 - 7坛游戏社区</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .navbar {
            width: 100%; max-width: 1100px;
            display: flex; align-items: center; justify-content: space-between;
            padding: 16px 24px;
        }
        .nav-logo { font-size: 22px; font-weight: bold; color: #ff6b35; }
        .nav-logo span { color: #ccc; }
        .nav-links { display: flex; gap: 20px; }
        .nav-links a { color: #aaa; text-decoration: none; font-size: 14px; }
        .nav-links a:hover { color: #ff6b35; }
        .card {
            background: #16213e;
            border-radius: 12px;
            padding: 40px 36px;
            width: 400px;
            max-width: 90vw;
            margin-top: 60px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }
        .card h2 { text-align: center; margin-bottom: 28px; font-size: 24px; color: #fff; }
        .form-group { margin-bottom: 18px; }
        .form-group label { display: block; margin-bottom: 6px; font-size: 14px; color: #aaa; }
        .form-group input {
            width: 100%; padding: 12px 14px;
            border: 1px solid #333;
            border-radius: 8px;
            background: #1a1a2e; color: #eee;
            font-size: 15px;
            outline: none; transition: border-color 0.2s;
        }
        .form-group input:focus { border-color: #ff6b35; }
        .btn {
            width: 100%; padding: 13px;
            background: #ff6b35; color: #fff;
            border: none; border-radius: 8px;
            font-size: 16px; font-weight: 600;
            cursor: pointer; transition: background 0.2s;
            margin-top: 6px;
        }
        .btn:hover { background: #e55a2b; }
        .btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .msg { text-align: center; margin-top: 16px; font-size: 14px; min-height: 20px; }
        .msg-error { color: #ff6b6b; }
        .msg-success { color: #51cf66; }
        .back-link { text-align: center; margin-top: 20px; }
        .back-link a { color: #aaa; font-size: 13px; text-decoration: none; }
        .back-link a:hover { color: #ff6b35; }
    </style>
</head>
<body>

<div class="navbar">
    <div class="nav-logo">7<span>坛</span>游戏社区</div>
    <div class="nav-links">
        <a href="/">首页</a>
        <a href="/android/">安卓游戏</a>
        <a href="/bbs/">社区</a>
    </div>
</div>

<div class="card">
    <h2>🔐 登录</h2>
    <div class="form-group">
        <label>用户名 / 手机号</label>
        <input type="text" id="username" placeholder="请输入用户名或手机号" autocomplete="username">
    </div>
    <div class="form-group">
        <label>密码</label>
        <input type="password" id="password" placeholder="请输入密码" autocomplete="current-password">
    </div>
    <button class="btn" id="loginBtn" onclick="doLogin()">登 录</button>
    <div class="msg" id="msg"></div>
</div>

<div class="back-link">
    <a href="/">← 返回首页</a>
</div>

<script>
const redirect = <?= json_encode($redirect) ?>;

async function doLogin() {
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    const btn = document.getElementById('loginBtn');
    const msg = document.getElementById('msg');

    if (!username || !password) {
        msg.className = 'msg msg-error';
        msg.textContent = '请输入用户名和密码';
        return;
    }

    btn.disabled = true;
    btn.textContent = '登录中...';
    msg.textContent = '';

    try {
        const resp = await fetch('/api/auth/login.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
        });
        const data = await resp.json();

        if (data.code === 0) {
            // 🔑 写入 Cookie（pro.php 依赖此 Cookie 判断登录状态）
            const token = data.data?.token || '';
            if (token) {
                document.cookie = 'auth_token=' + token + '; path=/; max-age=2592000; SameSite=Lax';
            }
            msg.className = 'msg msg-success';
            msg.textContent = '✅ 登录成功，正在跳转...';
            setTimeout(() => { window.location.href = redirect; }, 800);
        } else {
            msg.className = 'msg msg-error';
            msg.textContent = '❌ ' + (data.message || '登录失败');
            btn.disabled = false;
            btn.textContent = '登 录';
        }
    } catch (e) {
        msg.className = 'msg msg-error';
        msg.textContent = '❌ 网络错误：' + e.message;
        btn.disabled = false;
        btn.textContent = '登 录';
    }
}

// 回车提交
document.getElementById('password').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') doLogin();
});
document.getElementById('username').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') document.getElementById('password').focus();
});
</script>

</body>
</html>
