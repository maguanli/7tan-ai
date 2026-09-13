<?php

// ============================================================

// 隐私政策

// 位置: /privacy.php

// 7Tan AI工具 客户端《隐私政策》页面

// ============================================================

$page_title = '隐私政策 - 7坛游戏社区';

?>

<!DOCTYPE html>

<html lang="zh-CN">

<head>

    <meta charset="UTF-8">

    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title><?= $page_title ?></title>

    <style>

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {

            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", Roboto, sans-serif;

            background: #1a1a2e;

            color: #e0e0e0;

            min-height: 100vh;

            line-height: 1.8;

        }

        .navbar {

            width: 100%; max-width: 1100px;

            margin: 0 auto;

            display: flex; align-items: center; justify-content: space-between;

            padding: 16px 24px;

        }

        .nav-logo { font-size: 22px; font-weight: bold; color: #ff6b35; }

        .nav-logo span { color: #ccc; }

        .nav-links { display: flex; gap: 20px; }

        .nav-links a { color: #aaa; text-decoration: none; font-size: 14px; }

        .nav-links a:hover { color: #ff6b35; }

        .container { max-width: 900px; margin: 24px auto 60px; padding: 0 20px; }

        .card {

            background: #16213e;

            border-radius: 12px;

            padding: 48px 56px;

            box-shadow: 0 8px 32px rgba(0,0,0,0.3);

        }

        .card h1 { text-align: center; font-size: 28px; color: #fff; margin-bottom: 8px; }

        .meta { text-align: center; color: #888; font-size: 13px; margin-bottom: 36px; }

        h2 { color: #ff6b35; font-size: 18px; margin: 28px 0 12px; padding-bottom: 8px; border-bottom: 1px solid #2a3550; }

        p, li { font-size: 14px; color: #d0d5dd; margin-bottom: 8px; }

        ul, ol { padding-left: 24px; margin: 8px 0 16px; }

        li { margin-bottom: 6px; }

        strong { color: #fff; }

        table { width: 100%; border-collapse: collapse; margin: 12px 0 20px; font-size: 13px; }

        th, td { border: 1px solid #2a3550; padding: 10px 12px; text-align: left; color: #d0d5dd; }

        th { background: #1e2a4a; color: #fff; }

        .footer { text-align: center; color: #777; font-size: 13px; padding: 24px 0 48px; }

        .footer a { color: #ff6b35; text-decoration: none; }

        @media (max-width: 700px) { .card { padding: 28px 20px; } }

    </style>

</head>

<body>

    <nav class="navbar">

        <div class="nav-logo">7<span>坛游戏社区</span></div>

        <div class="nav-links">

            <a href="/">首页</a>

            <a href="/agreement.php">用户协议</a>

            <a href="/privacy.php" style="color:#ff6b35;">隐私政策</a>

        </div>

    </nav>



    <div class="container">

        <div class="card">

            <h1>7Tan AI工具 隐私政策</h1>

            <div class="meta">版本：V1.0 &nbsp;|&nbsp; 更新日期：2026年8月2日 &nbsp;|&nbsp; 生效日期：2026年8月2日</div>



            <p>本《隐私政策》（以下简称"本政策"）适用于「7Tan AI工具」客户端软件（以下简称"本软件"）及其相关服务。我们（<strong>7Tan 平台</strong>，以下简称"我们"或"7Tan"）深知个人信息对您的重要性，将按照法律法规要求，采取相应安全保护措施，尽力保护您的个人信息安全可控。</p>

            <p>请您在使用本软件前，仔细阅读并理解本政策的全部内容。您使用本软件，即表示您同意我们按照本政策收集、使用、存储和保护您的相关信息。</p>



            <h2>一、我们收集的信息</h2>

            <p>为向您提供本软件的各项功能与服务，我们可能会收集以下类别的信息：</p>



            <table>

                <tr><th>信息类别</th><th>具体内容</th><th>收集目的</th></tr>

                <tr>

                    <td>账号信息</td>

                    <td>用户名（或手机号）、密码（加密存储）、账号等级、完整版到期时间</td>

                    <td>账号登录、身份验证、完整版授权校验</td>

                </tr>

                <tr>

                    <td>设备信息（设备指纹）</td>

                    <td>主机名、系统架构、MAC 地址、Windows MachineGuid、主板序列号、电脑 UUID、CPU ID、硬盘序列号、BIOS 序列号（以上信息经 SHA-256 哈希处理后形成不可逆的设备指纹标识）</td>

                    <td>账号安全防护、防转卖/防共享检测、设备管理</td>

                </tr>

                <tr>

                    <td>网络信息</td>

                    <td>IP 地址、登录时间</td>

                    <td>安全风控、异常登录检测、故障排查</td>

                </tr>

                <tr>

                    <td>使用统计信息</td>

                    <td>软件版本号、启动/关闭时间、匿名设备标识（16位随机GUID）</td>

                    <td>统计日活/留存、版本分布分析、改进产品</td>

                </tr>

                <tr>

                    <td>本地烙印信息</td>

                    <td>登录用户名、登录时间、设备指纹（写入本软件安装目录、系统 AppData 目录及 Windows 注册表）</td>

                    <td>防止软件转卖与账号共享，泄露溯源</td>

                </tr>

            </table>



            <p>说明：设备指纹为多项硬件信息的不可逆哈希结果，我们无法从该标识反推出您的具体硬件序列号。除法律法规另有规定外，我们不会收集与您身份直接关联的敏感个人信息。</p>



            <h2>二、我们如何使用信息</h2>

            <ol>

                <li>提供、维护和改进本软件的各项功能与服务；</li>

                <li>账号登录验证、完整版授权管理与到期提醒；</li>

                <li>安全防护与反滥用：检测异常登录、账号共享、软件转卖等行为，保障您的账号与我们的服务安全；</li>

                <li>统计分析：了解用户规模与活跃情况，优化产品体验；</li>

                <li>处理投诉、纠纷与法律事务。</li>

            </ol>



            <h2>三、信息的存储与保护</h2>

            <ol>

                <li><strong>传输安全</strong>：客户端与服务器之间的数据传输均通过 HTTPS 加密通道进行。</li>

                <li><strong>存储安全</strong>：您的密码采用不可逆哈希算法加密存储，服务器采取防火墙、访问控制等措施保护数据。</li>

                <li><strong>存储期限</strong>：我们仅在实现本政策所述目的所必需的期限内保留您的信息，法律法规另有规定的除外。您注销账号后，我们将依法删除或匿名化处理您的个人信息（法律法规要求保留的除外）。</li>

            </ol>



            <h2>四、信息的共享与披露</h2>

            <ol>

                <li>我们不会向任何第三方出售您的个人信息。</li>

                <li>除以下情形外，我们不会向第三方共享您的信息：<br>

                    （1）取得您的明确同意；<br>

                    （2）根据法律法规、司法或行政机关的强制性要求；<br>

                    （3）为保护我们、您或其他用户的合法权益所必需。</li>

            </ol>



            <h2>五、您的权利</h2>

            <ol>

                <li><strong>查询与更正</strong>：您可以登录后台或联系我们查询、更正您的账号信息。</li>

                <li><strong>删除与注销</strong>：您可以通过联系我们注销账号。注销后，我们将删除或匿名化处理您的个人信息。</li>

                <li><strong>撤回同意</strong>：您可以通过卸载软件、停止使用等方式撤回对本政策下信息处理的同意。撤回不影响撤回前基于您的同意已进行的信息处理。</li>

            </ol>



            <h2>六、未成年人保护</h2>

            <p>本软件面向成年人提供服务。若您为未成年人，请在监护人指导下使用本软件，并在监护人同意本政策后再行使用。</p>



            <h2>七、政策的更新</h2>

            <p>我们可能适时修订本政策。本政策更新后，我们将在本页面公布最新版本。重大变更（如收集信息范围、使用目的的重大变化）我们将以弹窗、公告等显著方式通知您。您继续使用本软件即视为接受更新后的政策。</p>



            <h2>八、联系我们</h2>

            <p>如您对本政策有任何疑问、意见或建议，或需要行使您的个人信息相关权利，请通过以下方式联系我们：</p>

            <ul>

                <li>官方网站：<a href="https://www.7tan.com" style="color:#ff6b35;">www.7tan.com</a></li>

                <li>问题求助：<a href="https://www.7tan.com/bbs/board/25/" style="color:#ff6b35;">www.7tan.com/bbs/board/25/</a></li>

                <li>投诉建议：<a href="https://www.7tan.com/bbs/board/26/" style="color:#ff6b35;">www.7tan.com/bbs/board/26/</a></li>

            </ul>

            <p>我们将在收到您的反馈后 15 个工作日内予以答复。</p>

        </div>

        <div class="footer">

            <p>© 2026 7坛游戏社区 · 7Tan</p>

        </div>

    </div>

</body>

</html>

