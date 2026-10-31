<?php
/**
 * 7坛社区 隐私政策
 * 深圳市柒贰叁叁网络科技有限公司版权所有
 */
require_once __DIR__ . '/config.php';

// 禁止缓存，防止浏览器缓存旧的错误页面
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('Pragma: no-cache');
header('Expires: Thu, 01 Jan 1970 00:00:00 GMT');

// 隐私政策正文（按章节组织）
$sections = array(
    array('一、信息收集', array(
        '我们收集的信息包括：您主动提供的注册信息（用户名、昵称、手机号等）、您发布的内容，以及您使用服务时产生的日志信息（IP地址、浏览器类型、访问时间等）。',
        '我们可能通过Cookie等技术收集您的设备信息和浏览偏好，用于改善服务体验。',
    )),
    array('二、信息使用', array(
        '我们收集的信息将用于：提供和改善服务、账号管理、安全风控、个性化推荐、统计分析等。',
        '我们不会向任何第三方出售您的个人信息。',
    )),
    array('三、Cookie的使用', array(
        'Cookie是存储在您设备上的小型数据文件，用于记录您的登录状态、语言偏好等。',
        '您可以通过浏览器设置禁用Cookie，但可能导致部分功能无法正常使用。',
    )),
    array('四、信息共享与披露', array(
        '除以下情形外，我们不会向第三方共享您的个人信息：获得您的明确同意；法律法规要求；为保护我们或他人的合法权益。',
        '我们可能委托第三方服务商（如云存储、数据分析）处理信息，但会要求其遵守保密义务。',
    )),
    array('五、信息存储与安全', array(
        '您的个人信息存储于中华人民共和国境内的服务器。',
        '我们采取合理的安全措施保护您的信息，但无法保证绝对安全。',
    )),
    array('六、用户权利', array(
        '您有权查询、更正、删除您的个人信息，有权注销您的账号。',
        '您可以通过站内功能或联系我们行使上述权利。',
    )),
    array('七、未成年人保护', array(
        '我们重视未成年人个人信息保护。未成年人应在监护人指导下使用本社区服务。',
    )),
    array('八、政策变更', array(
        '我们可能适时更新本政策，更新后将在本页面公布。',
    )),
    array('九、联系方式', array(
        '如您对本政策有任何疑问，可通过站内私信或公告中的联系方式与我们联系。',
    )),
);
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="noindex,nofollow">
    <title><?php echo '隐私政策' . ' - ' . '7坛游戏社区'; ?></title>
    <link rel="stylesheet" href="<?php echo $baseUrl; ?>css/style.css?v=20261030">
    <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        font-family: -apple-system, 'PingFang SC', sans-serif;
        background: #f4f5f7;
        min-height: 100vh;
        padding: 24px;
    }
    .doc-container {
        max-width: 820px;
        margin: 0 auto;
    }
    .doc-card {
        background: #fff;
        border-radius: 14px;
        padding: 40px 44px;
        box-shadow: 0 6px 24px rgba(0,0,0,0.06);
    }
    .lang-wrap {
        text-align: right;
        margin-bottom: 16px;
    }
    .doc-card h1 {
        font-size: 26px;
        color: #1f1f1f;
        margin-bottom: 10px;
    }
    .doc-meta {
        font-size: 13px;
        color: #999;
        margin-bottom: 28px;
        padding-bottom: 20px;
        border-bottom: 1px solid #eee;
    }
    .doc-body h2 {
        font-size: 18px;
        color: #222;
        margin: 24px 0 12px;
    }
    .doc-body p {
        font-size: 15px;
        line-height: 1.85;
        color: #444;
        margin-bottom: 12px;
    }
    .doc-back {
        margin-top: 32px;
        padding-top: 20px;
        border-top: 1px solid #eee;
    }
    .doc-back a {
        color: #5B8DEF;
        text-decoration: none;
        font-size: 15px;
    }
    .doc-back a:hover {
        text-decoration: underline;
    }
    @media (max-width: 600px) {
        body { padding: 12px; }
        .doc-card { padding: 28px 20px; }
    }
    </style>
<script>
var _hmt = _hmt || [];
(function() {
  var hm = document.createElement("script");
  hm.src = "https://hm.baidu.com/hm.js?f5f121dbbaa5fca7a5d5fba84a19576c";
  var s = document.getElementsByTagName("script")[0]; 
  s.parentNode.insertBefore(hm, s);
})();
</script>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-9874557266132949" crossorigin="anonymous"></script>
</head>
<body>
    <div class="doc-container">
        <div class="doc-card">
            <h1>隐私政策</h1>
            <p class="doc-meta">7坛游戏社区 · 最近更新：2026年9月7日</p>
            <div class="doc-body">
                <?php foreach ($sections as $sec): ?>
                <h2><?php echo e($sec[0]); ?></h2>
                <?php foreach ($sec[1] as $p): ?>
                <p><?php echo e($p); ?></p>
                <?php endforeach; ?>
                <?php endforeach; ?>
            </div>
            <div class="doc-back">
                <a href="/">← 返回首页</a>
            </div>
        </div>
    </div>
</body>
</html>
