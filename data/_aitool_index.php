<?php
/**
 * 7Tan AI 工具 · 下载页
 * ------------------------------------------------------------
 * 路由：/ai-tool/  （router.php 目录规则 → 本文件）
 * 版式与文案：中文硬编码
 * 版本信息：单一数据源 /updates/version.json，新版本发布后本页自动同步
 * 图片资源：/images/aitool/（由 nginx 静态直出）
 * 说明：本页 UI 沿用首页 /css/home.css 的深色设计语言，另加 /css/aitool.css
 */
require_once __DIR__ . '/../db.php';
require_once __DIR__ . '/../functions.php';

// 内容页禁用浏览器缓存：避免版本号 / 下载地址更新后访客仍看到旧内容
if (!headers_sent()) {
    header('Cache-Control: no-cache, must-revalidate');
    header('Pragma: no-cache');
    header('Expires: 0');
}

// ==================== 最新版本信息 ====================
$latest = array(
    'version' => '1.0.22',
    'url'     => '/updates/7tan-editor-free-v1.0.22.zip',
    'size'    => 422663043,
    'date'    => '2026-09-13',
);
$__vf = __DIR__ . '/../updates/version.json';
if (is_file($__vf)) {
    $__vj = json_decode((string)@file_get_contents($__vf), true);
    if (is_array($__vj) && !empty($__vj['versions'][0]) && is_array($__vj['versions'][0])) {
        $__v0 = $__vj['versions'][0];
        if (!empty($__v0['version']))      { $latest['version'] = (string)$__v0['version']; }
        if (!empty($__v0['url']))          { $latest['url']     = (string)$__v0['url']; }
        if (!empty($__v0['size']))         { $latest['size']    = (int)$__v0['size']; }
        if (!empty($__v0['release_date'])) { $latest['date']    = (string)$__v0['release_date']; }
    }
}
unset($__vf, $__vj, $__v0);

// ==================== GitHub 开源 / 分流地址 ====================
// 目的：把安装包的下载流量分流到 GitHub，减轻本站服务器带宽压力。
// 版本标签直接取自 $latest['version']，发新版后自动跟随版本号。
$ghRepo = 'https://github.com/maguanli/7tan-ai';
$ghTag  = $ghRepo . '/releases/tag/v' . $latest['version'];
$ghRels = $ghRepo . '/releases';
$ghIcon = '<svg viewBox="0 0 16 16" width="20" height="20" fill="currentColor" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg>';
$ghDlIcon = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 3a1 1 0 0 1 1 1v9.59l3.3-3.3a1 1 0 1 1 1.4 1.42l-5 5a1 1 0 0 1-1.4 0l-5-5a1 1 0 1 1 1.4-1.42l3.3 3.3V4a1 1 0 0 1 1-1zM5 19a1 1 0 0 1 1-1h12a1 1 0 1 1 0 2H6a1 1 0 0 1-1-1z"/></svg>';

$verText  = 'v' . $latest['version'];
$sizeText = $latest['size'] > 0 ? round($latest['size'] / 1048576) . ' MB' : '—';

$origin   = siteOrigin();
$canonPath = '/ai-tool/';
$canonUrl  = $origin . $canonPath;
$dlAbs     = (strpos($latest['url'], 'http') === 0) ? $latest['url'] : $origin . $latest['url'];
$imgBase   = '/images/aitool';
$ogImage   = $origin . $imgBase . '/desktop-1.jpg';

$pageTitle = '7Tan AI 工具' . ' — ' . '一句话，让电脑替你干活' . ' | ' . '7坛游戏社区';
$pageDesc  = '编程写代码 · 做游戏 · 自动化办公 · 插件无限扩展' . '。' . '全部功能与全部插件永久免费' . '（' . $verText . '）';

// ==================== 导航（与首页一致，本页高亮）====================
$navItems = array(
    array('https://www.7tan.com/', '首页',  ''),
    array('https://www.7tan.com/android/', '安卓',  ''),
    array('https://www.7tan.com/wangyou/', '网游',  ''),
    array('https://www.7tan.com/biantai/', 'BT版',  ''),
    array('https://www.7tan.com/fenlei/', '分类',  ''),
    array('https://www.7tan.com/game-creator/', '做游戏', ''),
    array('https://www.7tan.com/ai-tool/', 'AI工具', 'on'),
);

// ==================== 核心能力（8 项）====================
$features = array(
    array('💬', 'AI 对话与模型设置', '接入主流大模型，模型、接口与参数集中配置，随时切换。'),
    array('🧠', '长期记忆', '记住你说过的话与使用偏好，用得越久越懂你。'),
    array('💓', '意识模型', '心跳、记忆、器官模块与自我模型状态实时可见。'),
    array('🧰', '环境引擎', '一键检测并安装常用开发环境，内置 76+ 条软件清单。'),
    array('🧩', '能力清单与插件', '46+ 项能力勾选即用，插件中心全部免费。'),
    array('📝', '代码与文件变更', '每一处改动逐行可见，可对比、可回滚。'),
    array('🌐', '网页版与远程访问', '浏览器打开即用，手机也能连回你的电脑。'),
    array('🖱', '桌面自动化', '截图、键鼠、剪贴板与桌面监控，重复操作交给它。'),
);

// ==================== 界面截图（14 张真实截图）====================
$shots = array(
    array('desktop-1',   '桌面客户端'),
    array('desktop-2',   '多面板工作台'),
    array('web',         '网页版'),
    array('login',       '账号登录'),
    array('exe-file',    '解压即用'),
    array('ai-settings', 'AI 对话与模型设置'),
    array('prompts',     '提示词'),
    array('memory',      '长期记忆'),
    array('consciousness', '意识模型'),
    array('env-engine',  '环境引擎'),
    array('capabilities','能力清单'),
    array('plugins',     '能力清单与插件'),
    array('code-diff',   '代码与文件变更'),
    array('remote',      '网页版与远程访问'),
);

// ==================== 安装三步 ====================
$steps = array(
    array('下载压缩包', '从本页或 GitHub 下载最新版 ZIP 压缩包。'),
    array('解压到本地', '把 ZIP 解压到任意文件夹，绿色免安装。'),
    array('双击运行', '双击 7tan-editor.exe 启动，按提示放行安全软件即可。'),
);

// ==================== FAQ ====================
$faqs = array(
    array('杀毒软件提示风险怎么办？', '7Tan 具备自动更新、本地服务、桌面自动化（截图 / 键鼠 / 剪贴板）等完整能力，行为特征与部分安全软件的启发式规则接近，加上暂未购买商业代码签名证书，首次运行可能被拦截。这是保守拦截，不是软件有毒。请在安全软件的「隔离区」把文件还原出来，并把解压后的整个文件夹加入白名单。'),
    array('需要付费或激活码吗？', '不需要。全部核心功能与全部插件永久免费，软件内没有任何付费入口，也没有试用次数限制。'),
    array('支持哪些系统？', 'Windows 10 / 11（64 位）。绿色免安装，解压即用；除桌面客户端外还内置网页版，浏览器打开即可使用。'),
);

// ==================== 结构化数据（SEO）====================
$ldShots = array();
foreach (array_slice($shots, 0, 6) as $s) {
    $ldShots[] = $origin . $imgBase . '/' . $s[0] . '.jpg';
}
$ld = array(
    '@context'            => 'https://schema.org',
    '@type'               => 'SoftwareApplication',
    'name'                => '7Tan AI 工具',
    'description'         => '编程写代码 · 做游戏 · 自动化办公 · 插件无限扩展',
    'applicationCategory' => 'DeveloperApplication',
    'operatingSystem'     => 'Windows 10, Windows 11',
    'softwareVersion'     => $latest['version'],
    'datePublished'       => $latest['date'],
    'inLanguage'          => 'zh-CN',
    'url'                 => $canonUrl,
    'downloadUrl'         => $dlAbs,
    'codeRepository'      => $ghRepo,
    'image'               => $ogImage,
    'screenshot'          => $ldShots,
    'offers'              => array(
        '@type'         => 'Offer',
        'price'         => '0',
        'priceCurrency' => 'CNY',
        'availability'  => 'https://schema.org/InStock',
    ),
    'publisher'           => array(
        '@type' => 'Organization',
        'name'  => '7坛游戏社区',
        'url'   => $origin,
    ),
);
if ($latest['size'] > 0) { $ld['fileSize'] = $latest['size'] . ' B'; }
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#06060E">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
<link rel="icon" href="/favicon.ico" type="image/x-icon">
<title><?= htmlspecialchars($pageTitle, ENT_QUOTES) ?></title>
<meta name="description" content="<?= htmlspecialchars($pageDesc, ENT_QUOTES) ?>">
<meta name="keywords" content="<?= htmlspecialchars('7Tan AI 工具' . ',7Tan,AI工具,AI工作台,写代码,做游戏,自动化办公,插件,免费软件,Windows', ENT_QUOTES) ?>">
<link rel="canonical" href="<?= htmlspecialchars($canonUrl, ENT_QUOTES) ?>">
<meta property="og:type" content="website">
<meta property="og:title" content="<?= htmlspecialchars($pageTitle, ENT_QUOTES) ?>">
<meta property="og:description" content="<?= htmlspecialchars($pageDesc, ENT_QUOTES) ?>">
<meta property="og:url" content="<?= htmlspecialchars($canonUrl, ENT_QUOTES) ?>">
<meta property="og:image" content="<?= htmlspecialchars($ogImage, ENT_QUOTES) ?>">
<meta property="og:site_name" content="7坛游戏社区">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="<?= htmlspecialchars($pageTitle, ENT_QUOTES) ?>">
<meta name="twitter:description" content="<?= htmlspecialchars($pageDesc, ENT_QUOTES) ?>">
<meta name="twitter:image" content="<?= htmlspecialchars($ogImage, ENT_QUOTES) ?>">
<link rel="stylesheet" href="/css/home.css?v=20260916f">
<link rel="stylesheet" href="/css/aitool.css?v=20260916f">
<script type="application/ld+json"><?= json_encode($ld, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) ?></script>
<?= renderBaiduStats() ?>
</head>
<body>

<!-- ==================== 顶部导航（与首页同款）==================== -->
<nav class="navbar">
  <div class="container">
    <div class="nav-logo">7<span>坛</span>游戏社区</div>
    <div class="nav-links" id="navLinks">
      <?php foreach ($navItems as $n): ?>
      <a href="<?= htmlspecialchars($n[0], ENT_QUOTES) ?>" title="<?= htmlspecialchars($n[1], ENT_QUOTES) ?>"<?= $n[2] === 'on' ? ' style="color:var(--green);font-weight:700;"' : '' ?>><?= $n[1] ?></a>
      <?php endforeach; ?>
      <a href="https://www.7tan.com/down/index.php?idd=15&amp;id=893" class="btn-download-nav">下载APP</a>
    </div>
    <button class="nav-toggle" id="navToggle" onclick="document.getElementById('navLinks').classList.toggle('open')">☰</button>
  </div>
</nav>

<!-- ==================== Hero ==================== -->
<section class="ait-hero">
  <div class="glow-green"></div>
  <div class="container">
    <div class="ait-hero-inner">
      <div class="ait-hero-text">
        <div class="ait-brand">
          <img src="<?= $imgBase ?>/logo.png" width="60" height="60" alt="<?= '7Tan AI 工具' ?>">
          <div>
            <div class="ait-brand-name"><?= '7Tan AI 工具' ?> <?= htmlspecialchars($verText, ENT_QUOTES) ?></div>
            <span class="ait-badge-free"><?= '全部功能与全部插件永久免费' ?></span>
          </div>
        </div>
        <h1><?= '一句话，让电脑替你干活' ?></h1>
        <p class="ait-hero-sub"><?= '编程写代码 · 做游戏 · 自动化办公 · 插件无限扩展' ?></p>
        <div class="hero-btns ait-hero-btns">
          <a class="btn-primary" href="<?= htmlspecialchars($latest['url'], ENT_QUOTES) ?>">
            <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 3a1 1 0 0 1 1 1v9.59l3.3-3.3a1 1 0 1 1 1.4 1.42l-5 5a1 1 0 0 1-1.4 0l-5-5a1 1 0 1 1 1.4-1.42l3.3 3.3V4a1 1 0 0 1 1-1zM5 19a1 1 0 0 1 1-1h12a1 1 0 1 1 0 2H6a1 1 0 0 1-1-1z"/></svg>
            <?= '下载 Windows 版' ?>
          </a>
          <a class="btn-secondary" href="#download"><?= '三步开始使用' ?> ↓</a>
          <a class="btn-secondary ait-btn-gh" href="<?= htmlspecialchars($ghTag, ENT_QUOTES) ?>" target="_blank" rel="noopener">
            <?= $ghIcon ?>
            <?= htmlspecialchars('GitHub 下载', ENT_QUOTES) ?>
          </a>
        </div>
        <div class="ait-meta-row">
          <span><b><?= '安装包大小' ?>:</b> <?= htmlspecialchars($sizeText, ENT_QUOTES) ?></span>
          <span><b><?= '发布日期' ?>:</b> <?= htmlspecialchars($latest['date'], ENT_QUOTES) ?></span>
          <span><b><?= '系统要求' ?>:</b> <?= 'Windows 10 / 11 · 64 位' ?></span>
        </div>
      </div>
      <div class="ait-hero-shot">
        <div class="ait-dots"><i></i><i></i><i></i></div>
        <img src="<?= $imgBase ?>/desktop-1.jpg" width="1280" height="696" alt="<?= htmlspecialchars('7Tan AI 工具' . ' — ' . '桌面客户端', ENT_QUOTES) ?>">
      </div>
    </div>
  </div>
</section>

<!-- ==================== 数据条 ==================== -->
<section class="stats-bar">
  <div class="container">
    <div class="stats-grid">
      <div class="stat-item">
        <h3><?= htmlspecialchars($verText, ENT_QUOTES) ?></h3>
        <p><?= '最新版本' ?></p>
      </div>
      <div class="stat-item">
        <h3>46+</h3>
        <p><?= '内置插件' ?></p>
      </div>
      <div class="stat-item">
        <h3>76+</h3>
        <p><?= '环境清单' ?></p>
      </div>
      <div class="stat-item">
        <h3><?= '免费' ?></h3>
        <p><?= '价格' ?></p>
      </div>
    </div>
  </div>
</section>

<!-- ==================== 核心能力 ==================== -->
<section class="features" id="features">
  <div class="glow-green"></div>
  <div class="container">
    <div class="section-tag"><?= '核心能力' ?></div>
    <h2 class="section-title"><?= '它能替你做什么' ?></h2>
    <p class="section-desc"><?= '不止于聊天：写代码、做游戏、自动化办公、插件扩展，一台电脑上的通用 AI 工作台。' ?></p>
    <div class="features-grid">
      <?php foreach ($features as $f): ?>
      <div class="feature-card">
        <div class="feature-icon"><?= $f[0] ?></div>
        <h3><?= htmlspecialchars($f[1], ENT_QUOTES) ?></h3>
        <p><?= htmlspecialchars($f[2], ENT_QUOTES) ?></p>
      </div>
      <?php endforeach; ?>
    </div>
  </div>
</section>

<!-- ==================== 界面截图 ==================== -->
<section class="screenshots" id="gallery">
  <div class="container">
    <div class="section-tag"><?= '界面一览' ?></div>
    <h2 class="section-title"><?= '真实界面截图' ?></h2>
    <p class="section-desc"><?= '以下均为软件真实界面，不是效果图。左右滑动查看，点击可放大。' ?></p>
  </div>
  <div class="ait-gallery-wrap">
    <div class="ait-car" id="aitCar">
      <div class="ait-car-viewport" id="aitCarView">
        <div class="ait-gallery-track" id="aitCarTrack">
          <?php $__si = 0; foreach ($shots as $s): $__src = $imgBase . '/' . $s[0] . '.jpg'; $__alt = '7Tan AI 工具' . ' — ' . $s[1]; ?>
          <div class="ait-shot<?= $__si === 0 ? ' is-active' : '' ?>" data-index="<?= $__si ?>">
            <div class="ait-shot-box" data-full="<?= htmlspecialchars($__src, ENT_QUOTES) ?>">
              <img src="<?= htmlspecialchars($__src, ENT_QUOTES) ?>" width="1280" height="696" loading="<?= $__si === 0 ? 'eager' : 'lazy' ?>" alt="<?= htmlspecialchars($__alt, ENT_QUOTES) ?>">
              <span class="ait-shot-zoom" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M9 3H3v6M15 3h6v6M15 21h6v-6M9 21H3v-6"/></svg></span>
            </div>
            <div class="ait-shot-label"><?= htmlspecialchars($s[1], ENT_QUOTES) ?></div>
          </div>
          <?php $__si++; endforeach; ?>
        </div>
        <button type="button" class="ait-car-btn ait-car-prev" id="aitCarPrev" aria-label="<?= htmlspecialchars('上一张', ENT_QUOTES) ?>">‹</button>
        <button type="button" class="ait-car-btn ait-car-next" id="aitCarNext" aria-label="<?= htmlspecialchars('下一张', ENT_QUOTES) ?>">›</button>
      </div>
      <div class="ait-car-foot">
        <div class="ait-car-dots" id="aitCarDots"></div>
        <div class="ait-car-bar" id="aitCarBar">1 / <?= count($shots) ?></div>
      </div>
    </div>
  </div>

</section>

<!-- ==================== 内置网页版 ==================== -->
<section class="ait-web" id="web">
  <div class="glow-green"></div>
  <div class="container">
    <div class="section-tag"><?= htmlspecialchars('网页版', ENT_QUOTES) ?></div>
    <h2 class="section-title"><?= htmlspecialchars('浏览器打开即用', ENT_QUOTES) ?></h2>
    <p class="section-desc"><?= htmlspecialchars('客户端内置网页版：软件保持运行时，用浏览器打开下面的地址即可使用；手机连同一网络还能远程操作电脑。', ENT_QUOTES) ?></p>
    <div class="ait-web-grid">
      <div class="ait-web-card">
        <div class="ait-web-addr-label"><?= htmlspecialchars('访问地址', ENT_QUOTES) ?></div>
        <div class="ait-web-addr">
          <code id="aitWebAddr">http://127.0.0.1:9900/</code>
          <button type="button" class="ait-web-copy" id="aitWebCopy" data-done="<?= htmlspecialchars('已复制', ENT_QUOTES) ?>"><?= htmlspecialchars('复制', ENT_QUOTES) ?></button>
        </div>
        <p class="ait-web-note"><?= htmlspecialchars('在浏览器打开上面的地址即可使用网页版，软件需保持运行。', ENT_QUOTES) ?></p>
        <div class="ait-web-shot">
          <div class="ait-shot-box" data-full="<?= $imgBase ?>/web.jpg">
            <img src="<?= $imgBase ?>/web.jpg" width="1280" height="696" loading="lazy" alt="<?= htmlspecialchars('7Tan AI 工具' . ' — ' . '网页版', ENT_QUOTES) ?>">
          </div>
        </div>
      </div>
      <div class="ait-web-points">
        <div class="ait-web-point">
          <div class="ico">🧩</div>
          <div>
            <h3><?= htmlspecialchars('能力不打折', ENT_QUOTES) ?></h3>
            <p><?= htmlspecialchars('对话、长期记忆、插件等核心能力与桌面客户端保持一致。', ENT_QUOTES) ?></p>
          </div>
        </div>
        <div class="ait-web-point">
          <div class="ico">📱</div>
          <div>
            <h3><?= htmlspecialchars('手机也能连', ENT_QUOTES) ?></h3>
            <p><?= htmlspecialchars('手机与电脑处于同一网络时，用手机浏览器即可连回你的电脑。', ENT_QUOTES) ?></p>
          </div>
        </div>
        <div class="ait-web-point">
          <div class="ico">🛠</div>
          <div>
            <h3><?= htmlspecialchars('数据留本机', ENT_QUOTES) ?></h3>
            <p><?= htmlspecialchars('网页服务运行在你自己的电脑上，对话与文件不外传第三方。', ENT_QUOTES) ?></p>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- ==================== 开源项目 · GitHub ==================== -->
<section class="features ait-gh-sec" id="github">
  <div class="glow-green"></div>
  <div class="container">
    <div class="section-tag" style="text-align:center;display:block;"><?= htmlspecialchars('开源项目', ENT_QUOTES) ?></div>
    <h2 class="section-title" style="text-align:center;"><?= htmlspecialchars('在 GitHub 上开源', ENT_QUOTES) ?></h2>
    <p class="section-desc" style="margin-left:auto;margin-right:auto;text-align:center;"><?= htmlspecialchars('源码公开、版本可追溯，欢迎 Star、提交 Issue 或参与共建。', ENT_QUOTES) ?></p>
    <div class="ait-gh-cards">
      <a class="ait-gh-card" href="<?= htmlspecialchars($ghRepo, ENT_QUOTES) ?>" target="_blank" rel="noopener">
        <span class="ico"><?= $ghIcon ?></span>
        <h3><?= htmlspecialchars('GitHub 仓库', ENT_QUOTES) ?></h3>
        <p><?= htmlspecialchars('源码完全公开，欢迎 Star、提交 Issue 与 PR。', ENT_QUOTES) ?></p>
        <code>github.com/maguanli/7tan-ai</code>
      </a>
      <a class="ait-gh-card" href="<?= htmlspecialchars($ghTag, ENT_QUOTES) ?>" target="_blank" rel="noopener">
        <span class="ico"><?= $ghDlIcon ?></span>
        <h3><?= htmlspecialchars('GitHub 下载', ENT_QUOTES) ?></h3>
        <p><?= htmlspecialchars('官方发布页，含最新版与历史版本安装包。', ENT_QUOTES) ?></p>
        <code>releases/tag/v<?= htmlspecialchars($latest['version'], ENT_QUOTES) ?></code>
      </a>
    </div>
    <p class="ait-gh-tip2"><?= htmlspecialchars('本站下载慢？可切换到 GitHub 官方发布页获取安装包。', ENT_QUOTES) ?> <?= htmlspecialchars('查看全部版本', ENT_QUOTES) ?> → <a href="<?= htmlspecialchars($ghRels, ENT_QUOTES) ?>" target="_blank" rel="noopener">github.com/maguanli/7tan-ai/releases</a></p>
  </div>
</section>

<!-- ==================== 下载安装 ==================== -->
<section class="cta" id="download" style="padding-top:0;">
  <div class="container">
    <div class="section-tag"><?= '下载安装' ?></div>
    <h2 class="section-title"><?= '三步开始使用' ?></h2>
    <p class="section-desc" style="margin-left:auto;margin-right:auto;"><?= '绿色免安装，解压即可运行。' ?></p>

    <div class="ait-steps">
      <?php $__i = 0; foreach ($steps as $st): $__i++; ?>
      <div class="ait-step">
        <div class="ait-step-no">STEP <?= $__i ?></div>
        <h3><?= htmlspecialchars($st[0], ENT_QUOTES) ?></h3>
        <p><?= htmlspecialchars($st[1], ENT_QUOTES) ?></p>
      </div>
      <?php endforeach; ?>
    </div>

    <div class="ait-dl-grid">
      <div class="ait-dl-main">
        <h3><?= '最新版本' ?> <?= htmlspecialchars($verText, ENT_QUOTES) ?></h3>
        <div class="ait-dl-ver"><?= htmlspecialchars($latest['date'], ENT_QUOTES) ?> · <?= htmlspecialchars($sizeText, ENT_QUOTES) ?> · <?= 'Windows 10 / 11 · 64 位' ?></div>
        <a class="btn-primary" href="<?= htmlspecialchars($latest['url'], ENT_QUOTES) ?>">
          <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 3a1 1 0 0 1 1 1v9.59l3.3-3.3a1 1 0 1 1 1.4 1.42l-5 5a1 1 0 0 1-1.4 0l-5-5a1 1 0 1 1 1.4-1.42l3.3 3.3V4a1 1 0 0 1 1-1zM5 19a1 1 0 0 1 1-1h12a1 1 0 1 1 0 2H6a1 1 0 0 1-1-1z"/></svg>
          <?= '下载 Windows 版' ?>
        </a>
        <div class="ait-gh-row">
          <a class="btn-secondary ait-btn-gh" href="<?= htmlspecialchars($ghTag, ENT_QUOTES) ?>" target="_blank" rel="noopener">
            <?= $ghIcon ?>
            <?= htmlspecialchars('GitHub 下载', ENT_QUOTES) ?>
          </a>
          <a class="ait-gh-all" href="<?= htmlspecialchars($ghRels, ENT_QUOTES) ?>" target="_blank" rel="noopener"><?= htmlspecialchars('查看全部版本', ENT_QUOTES) ?> →</a>
        </div>
        <p class="ait-note ait-gh-tip"><?= htmlspecialchars('本站下载慢？可切换到 GitHub 官方发布页获取安装包。', ENT_QUOTES) ?></p>
        <p class="ait-note ait-av-tip"><?= '⚠️ 使用 AI 功能前，请先关闭杀毒软件，或把解压后的整个文件夹加入信任名单（白名单）。AI 的桌面自动化（截图、键鼠、剪贴板）、网页抓取与本地服务都需要系统权限，安全软件会把它误判为可疑行为并拦截，导致 AI 无法使用；若仍被拦截，请右键「以管理员身份运行」。' ?></p>
        <p class="ait-note" style="margin-top:18px;"><?= '下载后解压 ZIP，双击 7tan-editor.exe 即可运行，无需安装。' ?></p>
        <p class="ait-note"><?= '推荐通过本站或上方 GitHub 官方镜像下载：更新包内置 MD5 与数字签名校验，可自行核对。' ?></p>
      </div>
      <div class="ait-dl-side">
        <div class="ait-meta-row" style="margin-top:0;flex-direction:column;gap:8px;">
          <span><b><?= '安装包大小' ?>:</b> <?= htmlspecialchars($sizeText, ENT_QUOTES) ?></span>
          <span><b><?= '发布日期' ?>:</b> <?= htmlspecialchars($latest['date'], ENT_QUOTES) ?></span>
          <span><b><?= '系统要求' ?>:</b> <?= 'Windows 10 / 11 · 64 位' ?></span>
        </div>
        <div class="ait-links" style="margin-top:18px;">
          <a href="#web">🌐 <?= htmlspecialchars('浏览器打开即用', ENT_QUOTES) ?></a>
          <a href="<?= htmlspecialchars($ghRepo, ENT_QUOTES) ?>" target="_blank" rel="noopener">🐙 <?= htmlspecialchars('GitHub 仓库', ENT_QUOTES) ?></a>
          <a href="<?= htmlspecialchars($ghTag, ENT_QUOTES) ?>" target="_blank" rel="noopener">⬇️ <?= htmlspecialchars('GitHub 下载', ENT_QUOTES) ?></a>
          <a href="/manual.html" target="_blank" rel="noopener">📘 <?= '使用说明书' ?></a>
          <a href="/updates/">🗂 <?= '历史版本与更新日志' ?></a>
          <a href="/agreement.php">📄 <?= '用户协议' ?></a>
          <a href="/privacy.php">🔒 <?= '隐私政策' ?></a>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- ==================== 常见问题 ==================== -->
<section class="features" id="faq" style="padding-top:0;">
  <div class="container">
    <div class="section-tag" style="text-align:center;display:block;"><?= '常见问题' ?></div>
    <h2 class="section-title" style="text-align:center;"><?= '你可能想问' ?></h2>
    <div class="ait-faq">
      <?php foreach ($faqs as $q): ?>
      <details>
        <summary><?= htmlspecialchars($q[0], ENT_QUOTES) ?></summary>
        <div class="ait-faq-body"><?= htmlspecialchars($q[1], ENT_QUOTES) ?></div>
      </details>
      <?php endforeach; ?>
    </div>
  </div>
</section>

<!-- ==================== 结尾 CTA ==================== -->
<section class="cta">
  <div class="glow-green"></div>
  <div class="container">
    <h2><?= '现在就把 7Tan 装进你的电脑' ?></h2>
    <p><?= '免费 · 免安装 · 解压即用' ?></p>
    <a href="<?= htmlspecialchars($latest['url'], ENT_QUOTES) ?>" class="btn-primary"><?= '⬇ 免费下载 7Tan AI 工具' ?></a>
  </div>
</section>

<button class="back-to-top" id="backToTop" onclick="window.scrollTo({top:0,behavior:'smooth'})">↑</button>

<!-- ==================== 页脚 ==================== -->
<footer>
  <div class="container">
    <p>© 2009-<?= date('Y') ?> <a href="https://www.7tan.com/">7坛游戏社区</a> 版权所有</p>
    <p style="margin-top:8px;">
      <a href="https://www.7tan.com/web/gywm.htm">关于我们</a>
      <a href="https://www.7tan.com/web/lcwm.htm">联系我们</a>
      <a href="https://www.7tan.com/web/bqsm.htm">版权声明</a>
      <a href="https://www.7tan.com/web/map.htm">网站地图</a>
      <a href="https://www.7tan.com/web/yszc.htm">隐私政策</a>
      <a href="<?= htmlspecialchars($ghRepo, ENT_QUOTES) ?>" target="_blank" rel="noopener">GitHub <?= htmlspecialchars('GitHub 仓库', ENT_QUOTES) ?></a>
    </p>
  </div>
</footer>

<!-- ==================== 图片放大灯箱 ==================== -->
<div class="ait-lb" id="aitLb" role="dialog" aria-modal="true" aria-label="图片查看">
  <div class="ait-lb-stage"><img src="" alt="" id="aitLbImg"></div>
  <button type="button" class="ait-lb-btn ait-lb-close" id="aitLbClose" aria-label="<?= htmlspecialchars('关闭', ENT_QUOTES) ?>">✕</button>
  <button type="button" class="ait-lb-btn ait-lb-prev" id="aitLbPrev" aria-label="<?= htmlspecialchars('上一张', ENT_QUOTES) ?>">‹</button>
  <button type="button" class="ait-lb-btn ait-lb-next" id="aitLbNext" aria-label="<?= htmlspecialchars('下一张', ENT_QUOTES) ?>">›</button>
  <div class="ait-lb-bar" id="aitLbBar"></div>
</div>

<script>
(function () {
  /* ---------- 图片灯箱：上一张 / 下一张 / 关闭 / 键盘 / 滑动 ---------- */
  var lb = document.getElementById('aitLb');
  var lbImg = document.getElementById('aitLbImg');
  var lbBar = document.getElementById('aitLbBar');
  var btnPrev = document.getElementById('aitLbPrev');
  var btnNext = document.getElementById('aitLbNext');
  var btnClose = document.getElementById('aitLbClose');

  if (lb && lbImg) {
    var boxes = Array.prototype.slice.call(document.querySelectorAll('.ait-shot-box[data-full]'));
    var idx = -1;

    var render = function () {
      var box = boxes[idx];
      if (!box) { return; }
      var full = box.getAttribute('data-full');
      var inner = box.querySelector('img');
      var alt = inner ? inner.getAttribute('alt') : '';
      lbImg.setAttribute('src', full);
      lbImg.setAttribute('alt', alt);
      lbImg.setAttribute('data-alt', alt);
      if (lbBar) { lbBar.textContent = (idx + 1) + ' / ' + boxes.length; }
      if (btnPrev) { btnPrev.disabled = boxes.length < 2; }
      if (btnNext) { btnNext.disabled = boxes.length < 2; }
    };
    var openAt = function (i) {
      if (!boxes.length) { return; }
      idx = (i + boxes.length) % boxes.length;
      render();
      lb.classList.add('open');
      document.body.style.overflow = 'hidden';
    };
    var close = function () {
      lb.classList.remove('open');
      document.body.style.overflow = '';
    };
    var step = function (d) {
      if (!lb.classList.contains('open') || boxes.length < 2) { return; }
      idx = (idx + d + boxes.length) % boxes.length;
      render();
    };

    document.addEventListener('click', function (e) {
      var box = e.target.closest ? e.target.closest('.ait-shot-box[data-full]') : null;
      if (box) {
        var i = boxes.indexOf(box);
        if (i >= 0) { openAt(i); }
        return;
      }
      if (lb.classList.contains('open')) {
        if (swiped) { return; }   /* 刚滑动过：不当作关闭点击 */
        if (e.target.closest && e.target.closest('.ait-lb-btn')) { return; }
        close();
      }
    });

    if (btnPrev)  { btnPrev.addEventListener('click',  function (e) { e.stopPropagation(); step(-1); }); }
    if (btnNext)  { btnNext.addEventListener('click',  function (e) { e.stopPropagation(); step(1); }); }
    if (btnClose) { btnClose.addEventListener('click', function (e) { e.stopPropagation(); close(); }); }

    document.addEventListener('keydown', function (e) {
      if (!lb.classList.contains('open')) { return; }
      if (e.key === 'Escape')          { close(); }
      else if (e.key === 'ArrowLeft')  { step(-1); }
      else if (e.key === 'ArrowRight') { step(1); }
    });

    var touchX = null;
    var swiped = false;
    lb.addEventListener('touchstart', function (e) {
      touchX = e.touches && e.touches[0] ? e.touches[0].clientX : null;
    }, {passive: true});
    lb.addEventListener('touchend', function (e) {
      if (touchX === null || !e.changedTouches || !e.changedTouches[0]) { return; }
      var dx = e.changedTouches[0].clientX - touchX;
      touchX = null;
      if (Math.abs(dx) > 42) {
        swiped = true;
        setTimeout(function () { swiped = false; }, 400);
        step(dx > 0 ? -1 : 1);
      }
    }, {passive: true});
  }

  /* ---------- 截图画廊：单图轮播（点左右按钮 / 滑动 / 键盘 翻看） ---------- */
  var car = document.getElementById('aitCar');
  var carView = document.getElementById('aitCarView');
  if (car && carView) {
    var slides = Array.prototype.slice.call(car.querySelectorAll('.ait-gallery-track .ait-shot'));
    var carTotal = slides.length;
    var dotsBox = document.getElementById('aitCarDots');
    var carBar = document.getElementById('aitCarBar');
    var cBtnPrev = document.getElementById('aitCarPrev');
    var cBtnNext = document.getElementById('aitCarNext');
    var cur = 0;
    var carSwiped = false;

    var carPrefetch = function (i) {
      var s = slides[i];
      var im = s ? s.querySelector('img') : null;
      if (im && im.getAttribute('src') && !im.getAttribute('data-pf')) {
        im.setAttribute('data-pf', '1');
        var pre = new Image();
        pre.src = im.getAttribute('src');
      }
    };

    var jump = function (i) {
      if (!carTotal) { return; }
      cur = ((i % carTotal) + carTotal) % carTotal;
      for (var k = 0; k < carTotal; k++) {
        if (k === cur) { slides[k].classList.add('is-active'); }
        else { slides[k].classList.remove('is-active'); }
      }
      if (dotsBox) {
        for (var d = 0; d < dotsBox.children.length; d++) {
          if (d === cur) {
            dotsBox.children[d].classList.add('on');
            dotsBox.children[d].setAttribute('aria-current', 'true');
          } else {
            dotsBox.children[d].classList.remove('on');
            dotsBox.children[d].removeAttribute('aria-current');
          }
        }
      }
      if (carBar) { carBar.textContent = (cur + 1) + ' / ' + carTotal; }
      carPrefetch((cur + 1) % carTotal);
      carPrefetch((cur - 1 + carTotal) % carTotal);
    };

    if (dotsBox) {
      for (var n = 0; n < carTotal; n++) {
        (function (i) {
          var b = document.createElement('button');
          b.type = 'button';
          b.className = 'ait-car-dot';
          b.setAttribute('aria-label', (i + 1) + ' / ' + carTotal);
          b.addEventListener('click', function (e) { if (e) { e.preventDefault(); } jump(i); });
          dotsBox.appendChild(b);
        })(n);
      }
    }

    if (cBtnPrev) { cBtnPrev.addEventListener('click', function (e) { e.preventDefault(); jump(cur - 1); }); }
    if (cBtnNext) { cBtnNext.addEventListener('click', function (e) { e.preventDefault(); jump(cur + 1); }); }
    if (carTotal < 2) {
      if (cBtnPrev) { cBtnPrev.style.display = 'none'; }
      if (cBtnNext) { cBtnNext.style.display = 'none'; }
    }

    /* 滑动翻看；滑动后短暂抑制点击，避免误触放大灯箱 */
    var carX = null;
    carView.addEventListener('touchstart', function (e) {
      carX = e.touches && e.touches[0] ? e.touches[0].clientX : null;
    }, {passive: true});
    carView.addEventListener('touchend', function (e) {
      if (carX === null || !e.changedTouches || !e.changedTouches[0]) { return; }
      var mdx = e.changedTouches[0].clientX - carX;
      carX = null;
      if (Math.abs(mdx) > 40) {
        carSwiped = true;
        setTimeout(function () { carSwiped = false; }, 420);
        jump(mdx > 0 ? cur - 1 : cur + 1);
      }
    }, {passive: true});
    carView.addEventListener('click', function (e) {
      if (carSwiped) { e.stopPropagation(); }
    }, true);

    /* 键盘左右翻看：仅当画廊在视口内，且灯箱未打开 */
    document.addEventListener('keydown', function (e) {
      if (lb && lb.classList.contains('open')) { return; }
      var tg = e.target;
      if (tg && (tg.tagName === 'INPUT' || tg.tagName === 'TEXTAREA' || tg.tagName === 'SELECT' || tg.isContentEditable)) { return; }
      var r = carView.getBoundingClientRect();
      var vh = window.innerHeight || document.documentElement.clientHeight || 800;
      if (r.bottom < 60 || r.top > vh - 60) { return; }
      if (e.key === 'ArrowLeft') { jump(cur - 1); }
      else if (e.key === 'ArrowRight') { jump(cur + 1); }
    });

    jump(0);
  }

  /* ---------- 网页版地址复制 ---------- */
  var cp = document.getElementById('aitWebCopy');
  var addr = document.getElementById('aitWebAddr');
  if (cp && addr) {
    cp.addEventListener('click', function () {
      var text = addr.textContent.trim();
      var done = function () {
        var old = cp.textContent;
        cp.classList.add('done');
        cp.textContent = cp.getAttribute('data-done') || 'OK';
        setTimeout(function () { cp.classList.remove('done'); cp.textContent = old; }, 1800);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, done);
      } else {
        var ta = document.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        try { document.execCommand('copy'); } catch (err) {}
        document.body.removeChild(ta);
        done();
      }
    });
  }

  // 顶部导航滚动加深阴影
  var nav = document.querySelector('.navbar');
  var top = document.getElementById('backToTop');
  function onScroll() {
    var y = window.pageYOffset || document.documentElement.scrollTop;
    if (nav) { nav.style.background = y > 30 ? 'rgba(6,6,14,0.92)' : ''; }
    if (top) { top.style.opacity = y > 400 ? '1' : '0'; }
  }
  window.addEventListener('scroll', onScroll, {passive: true});
  onScroll();
})();
</script>
</body>
</html>
