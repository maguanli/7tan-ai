# -*- coding: utf-8 -*-
"""构造 router.php / profile.php 的伪静态分页改造版本（纯字节替换，每处断言唯一命中）"""
import io, sys, hashlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

L = r'D:\7tan\7tanAI\_srv' + '\\'
CRLF = '\r\n'

# ══════════════════════════════════════════
# 一、router.php：在 user 路由前插入 _N 子路由
# ══════════════════════════════════════════
router = open(L + 'router.raw.php', 'rb').read()

anchor = ("    // /bbs/user/123/ → 用户主页" + CRLF +
          "    if (preg_match('#^user/(\\d+)/?$#', $bbsUri, $matches)) {").encode('utf-8')

new_block = (
    "    // /bbs/user/123_2/ → 用户主页第 2 页（20261030 伪静态分页）" + CRLF +
    "    if (preg_match('#^user/(\\d+)_(\\d+)/?$#', $bbsUri, $matches)) {" + CRLF +
    "        $_GET['id'] = $matches[1];" + CRLF +
    "        $GLOBALS['USER_PAGE_STATIC'] = (int)$matches[2];" + CRLF +
    "        $_SERVER['SCRIPT_NAME'] = '/bbs/profile.php';" + CRLF +
    "        chdir($bbsRoot);" + CRLF +
    "        require $bbsRoot . DIRECTORY_SEPARATOR . 'profile.php';" + CRLF +
    "        return true;" + CRLF +
    "    }" + CRLF +
    "    " + CRLF
).encode('utf-8')

assert router.count(anchor) == 1, 'router anchor 命中 %d 次' % router.count(anchor)
router_new = router.replace(anchor, new_block + anchor)
print('router: %d -> %d bytes (Δ %+d)' % (len(router), len(router_new), len(router_new) - len(router)))

# ══════════════════════════════════════════
# 二、profile.php：分页逻辑 + canonical + 模板链接
# ══════════════════════════════════════════
prof = open(L + 'profile.raw.php', 'rb').read()
orig_len = len(prof)
reps = []

# --- 2.1 分页入口逻辑 ---
reps.append((
    "// 参数走 ?page=N，不走 /bbs/user/1_2/ —— 后者得改 router.php 的匹配正则，" + CRLF +
    "// 那是全站唯一入口，改错会把所有页面一起打死，不值当。" + CRLF +
    "$pageSize = 20;" + CRLF +
    CRLF +
    "// ?page=1 / ?page=0 / ?page=abc 一律 301 回干净地址，避免同一页出现多个 URL" + CRLF +
    "$pageParam = isset($_GET['page']) ? trim((string)$_GET['page']) : null;" + CRLF +
    "$page = ($pageParam !== null && ctype_digit($pageParam)) ? (int)$pageParam : 0;" + CRLF +
    "if ($pageParam !== null && $page <= 1) {" + CRLF +
    "    header('Location: /bbs/user/' . $userId . '/', true, 301);" + CRLF +
    "    exit;" + CRLF +
    "}" + CRLF +
    "if ($page < 1) $page = 1;",

    "// 20261030 v2：分页改伪静态 /bbs/user/{id}_{N}/，与板块页 /bbs/board/18_2/ 同风格。" + CRLF +
    "// 旧的 ?page=N 一律 301 过去，同一页不留两个 URL。" + CRLF +
    "$pageSize = 20;" + CRLF +
    CRLF +
    "$staticPage = isset($GLOBALS['USER_PAGE_STATIC']) ? (int)$GLOBALS['USER_PAGE_STATIC'] : 0;" + CRLF +
    "$pageParam  = isset($_GET['page']) ? trim((string)$_GET['page']) : null;" + CRLF +
    CRLF +
    "if ($staticPage > 0) {" + CRLF +
    "    // 走 /bbs/user/1_2/ 这条路由，不再二次跳转" + CRLF +
    "    $page = $staticPage;" + CRLF +
    "    if ($page <= 1) {" + CRLF +
    "        header('Location: /bbs/user/' . $userId . '/', true, 301);" + CRLF +
    "        exit;" + CRLF +
    "    }" + CRLF +
    "} else {" + CRLF +
    "    $page = ($pageParam !== null && ctype_digit($pageParam)) ? (int)$pageParam : 0;" + CRLF +
    "    if ($pageParam !== null) {" + CRLF +
    "        if ($page <= 1) {" + CRLF +
    "            header('Location: /bbs/user/' . $userId . '/', true, 301);" + CRLF +
    "            exit;" + CRLF +
    "        }" + CRLF +
    "        header('Location: /bbs/user/' . $userId . '_' . $page . '/', true, 301);" + CRLF +
    "        exit;" + CRLF +
    "    }" + CRLF +
    "    $page = 1;" + CRLF +
    "}",
))

# --- 2.2 canonical ---
reps.append((
    "if ($page > 1) $canonicalPath .= '?page=' . $page;   // 分页页自引用，避免都指回第 1 页",
    "if ($page > 1) $canonicalPath = '/bbs/user/' . $userId . '_' . $page . '/';   // 分页页自引用，用伪静态地址",
))

# --- 2.3 baseUrl + 链接生成器 ---
reps.append((
    "                $baseUrl   = '/bbs/user/' . $userId . '/';" + CRLF +
    "                $winStart  = max(1, $page - 2);",
    "                $baseUrl   = '/bbs/user/' . $userId;   // 不带尾斜杠：第 1 页补 /，第 N 页补 _N/" + CRLF +
    "                $pgUrl     = function ($p) use ($baseUrl) {" + CRLF +
    "                    return $p <= 1 ? $baseUrl . '/' : $baseUrl . '_' . $p . '/';" + CRLF +
    "                };" + CRLF +
    "                $winStart  = max(1, $page - 2);",
))

# --- 2.4 上一页 ---
reps.append((
    "<a class=\"pg\" href=\"<?php echo $page === 2 ? $baseUrl : $baseUrl . '?page=' . ($page - 1); ?>\">",
    "<a class=\"pg\" href=\"<?php echo $pgUrl($page - 1); ?>\">",
))

# --- 2.5 第一页 ---
reps.append((
    "<a class=\"pg\" href=\"<?php echo $baseUrl; ?>\">1</a>",
    "<a class=\"pg\" href=\"<?php echo $pgUrl(1); ?>\">1</a>",
))

# --- 2.6 窗口内页码 ---
reps.append((
    "<a class=\"pg\" href=\"<?php echo $p === 1 ? $baseUrl : $baseUrl . '?page=' . $p; ?>\">",
    "<a class=\"pg\" href=\"<?php echo $pgUrl($p); ?>\">",
))

# --- 2.7 末页 ---
reps.append((
    "<a class=\"pg\" href=\"<?php echo $baseUrl . '?page=' . $totalPages; ?>\">",
    "<a class=\"pg\" href=\"<?php echo $pgUrl($totalPages); ?>\">",
))

# --- 2.8 下一页 ---
reps.append((
    "<a class=\"pg\" href=\"<?php echo $baseUrl . '?page=' . ($page + 1); ?>\">",
    "<a class=\"pg\" href=\"<?php echo $pgUrl($page + 1); ?>\">",
))

for idx, (old, new) in enumerate(reps, 1):
    o = old.encode('utf-8')
    n = new.encode('utf-8')
    cnt = prof.count(o)
    assert cnt == 1, 'replacement #%d 命中 %d 次：%s' % (idx, cnt, old[:60])
    prof = prof.replace(o, n)
    print('rep #%d  ok  (%d -> %d bytes)' % (idx, len(o), len(n)))

print('profile: %d -> %d bytes (Δ %+d)' % (orig_len, len(prof), len(prof) - orig_len))

# 残留检查
for bad in [b"'?page='", b"baseUrl . '?page='"]:
    c = prof.count(bad)
    print('  残留 %-22s %d' % (bad.decode(), c))
    assert c == 0, 'profile 仍残留 ' + bad.decode()
print('  注释里的 ?page= 提及  %d' % prof.count(b'?page='))

# 写盘
open(L + 'router.new.php', 'wb').write(router_new)
open(L + 'profile.new.php', 'wb').write(prof)
print()
print('md5 router.new.php  =', hashlib.md5(router_new).hexdigest()[:16])
print('md5 profile.new.php =', hashlib.md5(prof).hexdigest()[:16])
print('CRLF router =', router_new.count(b'\r\n'), ' bareLF =', router_new.count(b'\n') - router_new.count(b'\r\n'))
print('CRLF profile=', prof.count(b'\r\n'), ' bareLF =', prof.count(b'\n') - prof.count(b'\r\n'))
