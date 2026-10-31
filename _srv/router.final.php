<?php
/**
 * 7坛游戏社区 路由
 * 深圳市柒贰叁叁网络科技有限公司版权所有
 * 
 * URL规范（2025 SEO最佳实践）：
 * - 无扩展名，使用连字符分隔
 * - 层级结构：/模块/类型/ID/
 * - 优先短URL
 */

$root = __DIR__;
$uri = urldecode(parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH));

// 将 URI 中的正斜杠转为系统路径分隔符
$relPath = str_replace('/', DIRECTORY_SEPARATOR, ltrim($uri, '/'));
$absPath = $root . DIRECTORY_SEPARATOR . $relPath;

// ============================================================
// 0.) 页码别名 _1 → 301 归一到基址（消除 /xxx_1/ 重复内容）
//     覆盖：/baike_1/、/biantai_1/ …（14 个频道页）、/fenlei/pojie_1/ 等
//     注意：nginx 会先把 /fenlei/xxx_1/ 重写为 /htm/list.php，
//           此时路径里已无 _1，必须读原始请求 URI（X-Original-URI）
// ============================================================
$_origUri = isset($_SERVER['HTTP_X_ORIGINAL_URI']) && $_SERVER['HTTP_X_ORIGINAL_URI'] !== ''
    ? $_SERVER['HTTP_X_ORIGINAL_URI'] : $uri;
$_origPath = parse_url($_origUri, PHP_URL_PATH);
if ($_origPath !== null && preg_match('#^/(.+?)_1/?$#', $_origPath, $_m1)
    && strpos($_m1[1], '..') === false) {
    header('HTTP/1.1 301 Moved Permanently');
    header('Location: /' . $_m1[1] . '/');
    return true;
}

// ============================================================
// 0. 如果是真实文件（非目录），让PHP内置服务器直接处理
// ============================================================
if ($uri !== '/' && file_exists($absPath) && !is_dir($absPath)) {
    return false;
}

// ============================================================
// 1. 社区路由 /bbs/*
// ============================================================
if (strpos($uri, '/bbs/') === 0) {
    $bbsRoot = $root . DIRECTORY_SEPARATOR . 'bbs';
    $bbsUri = substr($uri, 5); // 移除 '/bbs/'
    
    // /bbs/123/ → 帖子详情 (兼容旧URL)
    if (preg_match('#^topic/(\d+)/?$#', $bbsUri, $matches)) {
        $_GET['id'] = $matches[1];
        $_SERVER['SCRIPT_NAME'] = '/bbs/view.php';
        chdir($bbsRoot);
        require $bbsRoot . DIRECTORY_SEPARATOR . 'view.php';
        return true;
    }

    // /bbs/123/ → 帖子详情 (简化URL，三级路径)
    if (preg_match('#^(\d+)/?$#', $bbsUri, $matches)) {
        $_GET['id'] = $matches[1];
        $_SERVER['SCRIPT_NAME'] = '/bbs/view.php';
        chdir($bbsRoot);
        require $bbsRoot . DIRECTORY_SEPARATOR . 'view.php';
        return true;
    }
    
    // /bbs/board/5/ → 第1页
    // /bbs/board/5_3/ → 第3页（无过滤）
    // /bbs/board/5_jing/ → 精华第1页
    // /bbs/board/5_jing_2/ → 精华第2页
    if (preg_match('#^board/(\d+)(?:_(jing|ding))?(?:_(\d+))?/?$#', $bbsUri, $matches)) {
        $_GET['id'] = $matches[1];
        if (!empty($matches[2])) {
            $_GET['filter'] = $matches[2];
        }
        if (!empty($matches[3])) {
            // _1 → 301 重定向到无后缀，避免重复内容
            if ($matches[3] === '1') {
                $newUrl = '/bbs/board/' . $matches[1];
                if (!empty($matches[2])) $newUrl .= '_' . $matches[2];
                $newUrl .= '/';
                header('HTTP/1.1 301 Moved Permanently');
                header('Location: ' . $newUrl);
                return true;
            }
            $_GET['page'] = $matches[3];
        }
        $_SERVER['SCRIPT_NAME'] = '/bbs/list.php';
        chdir($bbsRoot);
        require $bbsRoot . DIRECTORY_SEPARATOR . 'list.php';
        return true;
    }
    
    // /bbs/board/5/page-2/ → 旧格式，301 重定向
    if (preg_match('#^board/(\d+)/page-(\d+)/?$#', $bbsUri, $matches)) {
        $newUrl = '/bbs/board/' . $matches[1] . '/';
        if ($matches[2] > 1) $newUrl = '/bbs/board/' . $matches[1] . '_' . $matches[2] . '/';
        header('HTTP/1.1 301 Moved Permanently');
        header('Location: ' . $newUrl);
        return true;
    }
    
    // /bbs/search/ → 搜索页
    if ($bbsUri === 'search/' || $bbsUri === 'search') {
        $_SERVER['SCRIPT_NAME'] = '/bbs/search.php';
        chdir($bbsRoot);
        require $bbsRoot . DIRECTORY_SEPARATOR . 'search.php';
        return true;
    }
    
    // /bbs/post/ → 发帖页
    if ($bbsUri === 'post/' || $bbsUri === 'post') {
        $_SERVER['SCRIPT_NAME'] = '/bbs/post.php';
        chdir($bbsRoot);
        require $bbsRoot . DIRECTORY_SEPARATOR . 'post.php';
        return true;
    }
    
    // /bbs/user/123_2/ → 用户主页第 2 页（20261030 伪静态分页）
    if (preg_match('#^user/(\d+)_(\d+)/?$#', $bbsUri, $matches)) {
        $_GET['id'] = $matches[1];
        $GLOBALS['USER_PAGE_STATIC'] = (int)$matches[2];
        $GLOBALS['USER_PAGE_RAW']    = $matches[2];
        $_SERVER['SCRIPT_NAME'] = '/bbs/profile.php';
        chdir($bbsRoot);
        require $bbsRoot . DIRECTORY_SEPARATOR . 'profile.php';
        return true;
    }
    
    // /bbs/user/123/ → 用户主页
    if (preg_match('#^user/(\d+)/?$#', $bbsUri, $matches)) {
        $_GET['id'] = $matches[1];
        $_SERVER['SCRIPT_NAME'] = '/bbs/profile.php';
        chdir($bbsRoot);
        require $bbsRoot . DIRECTORY_SEPARATOR . 'profile.php';
        return true;
    }
    
    // /bbs/ → 社区首页（交给下面处理）
}

// ============================================================
// 1.5 API路由（/api/voice 等）
// ============================================================
if (strpos($uri, '/api/') === 0) {
    $apiUri = substr($uri, 5); // 移除 '/api/'
    $apiFile = $root . DIRECTORY_SEPARATOR . 'api' . DIRECTORY_SEPARATOR . $apiUri . '.php';
    $apiDir = $root . DIRECTORY_SEPARATOR . 'api';
    if (file_exists($apiFile)) {
        $_SERVER['SCRIPT_NAME'] = '/api/' . $apiUri . '.php';
        chdir($apiDir);
        require $apiFile;
        return true;
    }
}

// ============================================================
// 2. 主站路由
// ============================================================

// 游戏详情页 /game/123/ → /game/view.php?id=123（新格式，优先匹配）
if (preg_match('#^/game/(\d+)/?$#', $uri, $matches)) {
    $_GET['id'] = $matches[1];
    $_SERVER['SCRIPT_NAME'] = '/game/view.php';
    chdir($root . DIRECTORY_SEPARATOR . 'game');
    require $root . DIRECTORY_SEPARATOR . 'game' . DIRECTORY_SEPARATOR . 'view.php';
    return true;
}

// 兼容旧格式 /game/123.htm → /game/view.php?id=123
if (preg_match('#^/game/(\d+)\.htm$#', $uri, $matches)) {
    $_GET['id'] = $matches[1];
    $_SERVER['SCRIPT_NAME'] = '/game/view.php';
    chdir($root . DIRECTORY_SEPARATOR . 'game');
    require $root . DIRECTORY_SEPARATOR . 'game' . DIRECTORY_SEPARATOR . 'view.php';
    return true;
}

// 分类列表页 /category/5/ → /htm/list.php?id=5
if (preg_match('#^/category/(\d+)/?$#', $uri, $matches)) {
    $_GET['id'] = $matches[1];
    $_SERVER['SCRIPT_NAME'] = '/htm/list.php';
    chdir($root . DIRECTORY_SEPARATOR . 'htm');
    require $root . DIRECTORY_SEPARATOR . 'htm' . DIRECTORY_SEPARATOR . 'list.php';
    return true;
}

// 新格式路由（短URL，无扩展名）- 先去除前导斜杠再匹配
$shortRules = [
    '^zuixin/?$' => '/htm/zuixin.php',
    '^jingpin/?$' => '/htm/jingpin.php',
    '^paihang/?$' => '/htm/paihang.php',
    '^pojie/?$' => '/htm/pojie.php',
    '^biantai/?$' => '/htm/biantai.php',
    '^zhongwen/?$' => '/htm/zhongwen.php',
    '^djph/?$' => '/htm/djph.php',
    '^wyph/?$' => '/htm/wyph.php',
    '^btyx/?$' => '/htm/btyx.php',
    '^btwy/?$' => '/htm/btwy.php',
    '^btjp/?$' => '/htm/btjp.php',
    '^btph/?$' => '/htm/btph.php',
    '^zx/?$' => '/htm/zx.php',
    '^ph/?$' => '/htm/ph.php',
    '^jp/?$' => '/htm/jp.php',
    '^baike/?$' => '/baike/index.php',
];
foreach ($shortRules as $pattern => $target) {
    $uriWithoutSlash = ltrim($uri, '/');
    if (preg_match('#' . $pattern . '#', $uriWithoutSlash)) {
        $_SERVER['SCRIPT_NAME'] = $target;
        $scriptPath = $root . str_replace('/', DIRECTORY_SEPARATOR, $target);
        chdir(dirname($scriptPath));
        require $scriptPath;
        return true;
    }
}

// 频道页分页伪静态 /biantai_2/ → /htm/biantai.php?page=2（与 canonical 家族保持一致）
$shortPageRules = [
    '^zuixin_(\d+)/?$'   => '/htm/zuixin.php',
    '^jingpin_(\d+)/?$'  => '/htm/jingpin.php',
    '^paihang_(\d+)/?$'  => '/htm/paihang.php',
    '^pojie_(\d+)/?$'    => '/htm/pojie.php',
    '^biantai_(\d+)/?$'  => '/htm/biantai.php',
    '^zhongwen_(\d+)/?$' => '/htm/zhongwen.php',
    '^djph_(\d+)/?$'     => '/htm/djph.php',
    '^wyph_(\d+)/?$'     => '/htm/wyph.php',
    '^btyx_(\d+)/?$'     => '/htm/btyx.php',
    '^btwy_(\d+)/?$'     => '/htm/btwy.php',
    '^btjp_(\d+)/?$'     => '/htm/btjp.php',
    '^btph_(\d+)/?$'     => '/htm/btph.php',
    '^zx_(\d+)/?$'       => '/htm/zx.php',
    '^ph_(\d+)/?$'       => '/htm/ph.php',
    '^jp_(\d+)/?$'       => '/htm/jp.php',
    '^baike_(\d+)/?$'    => '/baike/index.php',
];
foreach ($shortPageRules as $pattern => $target) {
    $uriWithoutSlash = ltrim($uri, '/');
    if (preg_match('#' . $pattern . '#', $uriWithoutSlash, $pm)) {
        $_GET['page'] = $pm[1];
        $_SERVER['SCRIPT_NAME'] = $target;
        $scriptPath = $root . str_replace('/', DIRECTORY_SEPARATOR, $target);
        chdir(dirname($scriptPath));
        require $scriptPath;
        return true;
    }
}

// /fenlei/xxx/（无页码）
if (preg_match('#^/fenlei/(jiaose|yizhi|dongzuo|minjie|maoxian|kapai|tiyu|monijingying|qipai|celue|sheji|qita)/?$#', $uri, $fm)) {
    $_GET['type'] = $fm[1];
    $_SERVER['SCRIPT_NAME'] = '/htm/list.php';
    chdir($root . DIRECTORY_SEPARATOR . 'htm');
    require $root . DIRECTORY_SEPARATOR . 'htm' . DIRECTORY_SEPARATOR . 'list.php';
    return true;
}
if (preg_match('#^/fenlei/(zuixin|jingpin|paihang|pojie|biantai|zhongwen|ph|jp|btyx|btwy|btjp|btph|djph|wyph|zx)/?$#', $uri, $fm)) {
    $_SERVER['SCRIPT_NAME'] = '/htm/' . $fm[1] . '.php';
    chdir($root . DIRECTORY_SEPARATOR . 'htm');
    require $root . DIRECTORY_SEPARATOR . 'htm' . DIRECTORY_SEPARATOR . $fm[1] . '.php';
    return true;
}

// 分类列表页兼容旧URL格式
$fenleiRules = [
    '/fenlei/zuixin_(\d+)/?$' => '/htm/zuixin.php',
    '/fenlei/jingpin_(\d+)/?$' => '/htm/jingpin.php',
    '/fenlei/paihang_(\d+)/?$' => '/htm/paihang.php',
    '/fenlei/pojie_(\d+)/?$' => '/htm/pojie.php',
    '/fenlei/biantai_(\d+)/?$' => '/htm/biantai.php',
    '/fenlei/zhongwen_(\d+)/?$' => '/htm/zhongwen.php',
    '/fenlei/ph_(\d+)/?$' => '/htm/ph.php',
    '/fenlei/jp_(\d+)/?$' => '/htm/jp.php',
    '/fenlei/btyx_(\d+)/?$' => '/htm/btyx.php',
    '/fenlei/btwy_(\d+)/?$' => '/htm/btwy.php',
    '/fenlei/btjp_(\d+)/?$' => '/htm/btjp.php',
    '/fenlei/btph_(\d+)/?$' => '/htm/btph.php',
    '/fenlei/djph_(\d+)/?$' => '/htm/djph.php',
    '/fenlei/wyph_(\d+)/?$' => '/htm/wyph.php',
    '/fenlei/zx_(\d+)/?$' => '/htm/zx.php',
];

foreach ($fenleiRules as $pattern => $target) {
    if (preg_match('#' . $pattern . '#', $uri, $matches)) {
        $_GET['page'] = $matches[1];
        $_SERVER['SCRIPT_NAME'] = $target;
        // 解析路径
        $parts = parse_url($target);
        $scriptPath = $root . str_replace('/', DIRECTORY_SEPARATOR, $parts['path']);
        chdir(dirname($scriptPath));
        require $scriptPath;
        return true;
    }
}

// 分类ID页
$categoryRules = [
    '/fenlei/jiaose_(\d+)/?$' => '/htm/list.php?type=jiaose',
    '/fenlei/yizhi_(\d+)/?$' => '/htm/list.php?type=yizhi',
    '/fenlei/dongzuo_(\d+)/?$' => '/htm/list.php?type=dongzuo',
    '/fenlei/minjie_(\d+)/?$' => '/htm/list.php?type=minjie',
    '/fenlei/maoxian_(\d+)/?$' => '/htm/list.php?type=maoxian',
    '/fenlei/kapai_(\d+)/?$' => '/htm/list.php?type=kapai',
    '/fenlei/tiyu_(\d+)/?$' => '/htm/list.php?type=tiyu',
    '/fenlei/monijingying_(\d+)/?$' => '/htm/list.php?type=monijingying',
    '/fenlei/qipai_(\d+)/?$' => '/htm/list.php?type=qipai',
    '/fenlei/celue_(\d+)/?$' => '/htm/list.php?type=celue',
    '/fenlei/sheji_(\d+)/?$' => '/htm/list.php?type=sheji',
    '/fenlei/qita_(\d+)/?$' => '/htm/list.php?type=qita',
];

foreach ($categoryRules as $pattern => $target) {
    if (preg_match('#' . $pattern . '#', $uri, $matches)) {
        $_GET['page'] = $matches[1];
        $_SERVER['SCRIPT_NAME'] = $target;
        // 解析路径和query string
        $parts = parse_url($target);
        $scriptPath = $root . str_replace('/', DIRECTORY_SEPARATOR, $parts['path']);
        if (isset($parts['query'])) {
            parse_str($parts['query'], $queryParams);
            $_GET = array_merge($_GET, $queryParams);
        }
        chdir(dirname($scriptPath));
        require $scriptPath;
        return true;
    }
}

// 3.3（2026-10-30）：外部若引用过 .html/.htm 后缀的隐私政策地址，301 归一到正式地址，
// 避免白丢一条外链权重。这几条只是别名，没有任何证据说明已被引用，属预防性处理。
// 注意：不包含 /privacy.php —— 那是「7Tan AI 工具客户端」的 App 隐私政策（真实存在的独立页面），
//       且 router 前面「真实文件直接放行」的分支会先 return，这里的列表对它本来也不生效。
if (in_array($uri, ['/privacy.html', '/privacy.htm', '/privacy', '/yszc.html', '/yszc.htm'], true)) {
    header('Location: /web/yszc.htm', true, 301);
    return true;
}

// 静态页面
$staticPages = [
    '/web/gywm.htm' => '/about.php',
    '/web/lcwm.htm' => '/contact.php',
    '/web/bqsm.htm' => '/copyright.php',
    '/web/map.htm' => '/sitemap_page.php',
    // 1.3（2026-10-30）：站内隐私政策页。此前 /privacy.html、/web/yszc.htm 全部 404，
    // 站内 PAGE 只有「版权声明」里一节讲资源免责，完全没有个人信息条款；
    // AdSense 政策要求公示隐私政策并说明 Google 使用 Cookie 投放广告。
    '/web/yszc.htm' => '/yszc.php',
];

foreach ($staticPages as $pattern => $target) {
    if ($uri === $pattern || preg_match('#^' . $pattern . '$#', $uri)) {
        $_SERVER['SCRIPT_NAME'] = $target;
        $scriptPath = $root . str_replace('/', DIRECTORY_SEPARATOR, $target);
        chdir(dirname($scriptPath));
        require $scriptPath;
        return true;
    }
}

// 下载页 /down/ → /down/index.php
if ($uri === '/down/' || $uri === '/down') {
    $_SERVER['SCRIPT_NAME'] = '/down/index.php';
    chdir($root . DIRECTORY_SEPARATOR . 'down');
    require $root . DIRECTORY_SEPARATOR . 'down' . DIRECTORY_SEPARATOR . 'index.php';
    return true;
}

// .asp 重定向到 .php
if (preg_match('#^(.+)\.asp$#', $uri, $matches)) {
    $newUri = $matches[1] . '.php';
    header('Location: ' . $newUri, true, 301);
    return true;
}

// ============================================================
// 3. 如果是目录，寻找目录下的 index.php
// ============================================================
$dirPath = rtrim($absPath, DIRECTORY_SEPARATOR);
$indexFile = $dirPath . DIRECTORY_SEPARATOR . 'index.php';
if (is_dir($absPath) && file_exists($indexFile)) {
    chdir(dirname($indexFile));
    require $indexFile;
    return true;
}

// 4. 尝试将路径直接当目录处理（无尾部斜杠的情况）
$indexFile2 = $absPath . DIRECTORY_SEPARATOR . 'index.php';
if (file_exists($indexFile2)) {
    chdir(dirname($indexFile2));
    require $indexFile2;
    return true;
}

// 404 错误页 /404/ → /404.php
if ($uri === '/404/' || $uri === '/404') {
    http_response_code(404);
    $_SERVER['SCRIPT_NAME'] = '/404.php';
    require $root . DIRECTORY_SEPARATOR . '404.php';
    return true;
}

// 只有根路径 / 才回退到首页，其他路径返回404
if ($uri === '/' || $uri === '') {
    chdir($root);
    require $root . DIRECTORY_SEPARATOR . 'index.php';
    return true;
}

// 所有未匹配的路径 → 404
http_response_code(404);
$_SERVER['SCRIPT_NAME'] = '/404.php';
require $root . DIRECTORY_SEPARATOR . '404.php';
return true;
