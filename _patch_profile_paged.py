# -*- coding: utf-8 -*-
"""
profile.php 分页改造：
  改为每页 20 条 + 页码导航（原来写死 LIMIT 5，444 篇只露 5 篇）。
  走 ?page=N 查询串，不动 router.php 正则（全站唯一入口，改错会一起打死）。
  页码越界按站内既有约定 301 回第 1 页（list.php 同款处理，避免软 404）。
"""
import io, json, sys, time, hashlib
from pathlib import Path
import paramiko

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = Path(r'D:\7tan\7tanAI')
SRC = ROOT / '_srv' / 'profile.remote.php'
OUT = ROOT / '_srv' / 'profile.new.php'

cfg = json.loads((ROOT / 'config' / 'deploy.json').read_text(encoding='utf-8'))
srv = cfg['server']

raw = SRC.read_bytes()
txt = raw.decode('utf-8').replace('\r\n', '\n')
print('[0] 源文件 %d 字节 / %d 行 / LF=%d CRLF=%d'
      % (len(raw), len(txt.split('\n')), txt.count('\n'), raw.count(b'\r\n')))

reps = []

# ── 1. 查询块：LIMIT 5 → 分页 ──
reps.append((
    """// 获取用户最新帖子
$stmt = $pdo->prepare("SELECT id, ll_biaoti, ll_time2 FROM ll_lt WHERE ll_useid = ? AND ll_or = 0 ORDER BY id DESC LIMIT 5");
$stmt->execute([$userId]);
$recentTopics = $stmt->fetchAll();""",

    """// ── 帖子列表分页 ──
// 20261030: 原来写死 LIMIT 5，一个人发了几百篇，主页永远只露最后 5 篇。
// 改为每页 20（和板块列表 list.php 的 $pageSize 一致）。
// 参数走 ?page=N，不走 /bbs/user/1_2/ —— 后者得改 router.php 的匹配正则，
// 那是全站唯一入口，改错会把所有页面一起打死，不值当。
$pageSize = 20;

// ?page=1 / ?page=0 / ?page=abc 一律 301 回干净地址，避免同一页出现多个 URL
$pageParam = isset($_GET['page']) ? trim((string)$_GET['page']) : null;
$page = ($pageParam !== null && ctype_digit($pageParam)) ? (int)$pageParam : 0;
if ($pageParam !== null && $page <= 1) {
    header('Location: /bbs/user/' . $userId . '/', true, 301);
    exit;
}
if ($page < 1) $page = 1;

$topicTotal = (int)$topicCount;
$totalPages = max(1, (int)ceil($topicTotal / $pageSize));

// 越界页 301 回第 1 页（list.php 同款：越界页曾返回 200 空列表，属软 404）
if ($page > $totalPages) {
    header('Location: /bbs/user/' . $userId . '/', true, 301);
    exit;
}

$offset = ($page - 1) * $pageSize;
$stmt = $pdo->prepare("SELECT t.id, t.ll_biaoti, t.ll_time2, t.ll_rc, t.ll_idd, c.ll_title AS board_title
                         FROM ll_lt t LEFT JOIN ll_class c ON t.ll_idd = c.id
                        WHERE t.ll_useid = ? AND t.ll_or = 0
                        ORDER BY t.id DESC LIMIT " . $pageSize . " OFFSET " . $offset);
$stmt->execute([$userId]);
$recentTopics = $stmt->fetchAll();"""
))

# ── 2. canonical 带页码 ──
reps.append((
    "$canonicalPath = '/bbs/user/' . $userId . '/';",
    "$canonicalPath = '/bbs/user/' . $userId . '/';" + "\n" +
    "if ($page > 1) $canonicalPath .= '?page=' . $page;   // 分页页自引用，避免都指回第 1 页"
))

# ── 3. title 带页码 ──
reps.append((
    "    <title><?php echo e($nickname); ?> - <?php echo e('7坛游戏社区'); ?></title>",
    "    <title><?php echo e($nickname); ?><?php if ($page > 1) echo e(' 第' . $page . '页'); ?> - <?php echo e('7坛游戏社区'); ?></title>"
))

# ── 4. 补样式 ──
reps.append((
    "        .back-btn { position: absolute; top: 20px; left: 20px; color: white; text-decoration: none; }",
    "        .count-badge { display: inline-block; font-size: 12px; font-weight: 400; color: #667eea; background: #eef0fd; border-radius: 10px; padding: 2px 9px; margin-left: 8px; vertical-align: middle; }\n"
    "        .topic-meta { font-size: 12px; color: #999; margin-top: 6px; display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }\n"
    "        .topic-meta .board-tag { color: #667eea; text-decoration: none; background: #f0f2ff; border-radius: 4px; padding: 1px 7px; }\n"
    "        .topic-meta .board-tag:hover { background: #e3e7ff; }\n"
    "        .pager { display: flex; gap: 6px; flex-wrap: wrap; justify-content: center; align-items: center; margin-top: 18px; padding-top: 16px; border-top: 1px solid #eee; }\n"
    "        .pager .pg { display: inline-block; min-width: 34px; text-align: center; padding: 6px 10px; border: 1px solid #e2e2e2; border-radius: 6px; color: #555; text-decoration: none; font-size: 13px; background: #fff; }\n"
    "        .pager .pg:hover { border-color: #667eea; color: #667eea; }\n"
    "        .pager .pg.on { background: #667eea; border-color: #667eea; color: #fff; font-weight: 600; }\n"
    "        .pager .pg-dot { color: #bbb; padding: 0 2px; font-size: 13px; }\n"
    "        .back-btn { position: absolute; top: 20px; left: 20px; color: white; text-decoration: none; }"
))

# ── 5. 列表渲染块 ──
old_list = """        <?php if (!empty($recentTopics)): ?>
        <div class="content-card">
            <h5><?php echo e('📝 最新帖子'); ?></h5>
            <?php foreach ($recentTopics as $topic): ?>
            <div class="topic-item">
                <a href="<?php echo htmlspecialchars(bbsUrl('topic', $topic['id']), ENT_QUOTES); ?>"><?php echo e($topic['ll_biaoti']); ?></a>
                <div style="font-size: 12px; color: #999; margin-top: 5px;"><?php echo formatTime($topic['ll_time2']); ?></div>
            </div>
            <?php endforeach; ?>
        </div>
        <?php endif; ?>"""

new_list = """        <?php if (!empty($recentTopics)): ?>
        <div class="content-card">
            <h5><?php echo e('📝 帖子'); ?><span class="count-badge"><?php echo e('共 ' . $topicTotal . ' 篇'); ?></span><?php if ($totalPages > 1): ?><span class="count-badge"><?php echo e('第 ' . $page . ' / ' . $totalPages . ' 页'); ?></span><?php endif; ?></h5>
            <?php foreach ($recentTopics as $topic): ?>
            <div class="topic-item">
                <a href="<?php echo htmlspecialchars(bbsUrl('topic', $topic['id']), ENT_QUOTES); ?>"><?php echo e($topic['ll_biaoti']); ?></a>
                <div class="topic-meta">
                    <?php if (!empty($topic['board_title'])): ?>
                    <a class="board-tag" href="<?php echo htmlspecialchars(bbsUrl('board', $topic['ll_idd']), ENT_QUOTES); ?>"><?php echo e($topic['board_title']); ?></a>
                    <?php endif; ?>
                    <span><?php echo formatTime($topic['ll_time2']); ?></span>
                    <span><?php echo (int)($topic['ll_rc'] ?? 0); ?><?php echo e(' 次浏览'); ?></span>
                </div>
            </div>
            <?php endforeach; ?>
            <?php if ($totalPages > 1): ?>
            <nav class="pager" aria-label="<?php echo e('帖子分页'); ?>">
                <?php
                $baseUrl   = '/bbs/user/' . $userId . '/';
                $winStart  = max(1, $page - 2);
                $winEnd    = min($totalPages, $page + 2);
                ?>
                <?php if ($page > 1): ?>
                <a class="pg" href="<?php echo $page === 2 ? $baseUrl : $baseUrl . '?page=' . ($page - 1); ?>"><?php echo e('← 上一页'); ?></a>
                <?php endif; ?>
                <?php if ($winStart > 1): ?>
                <a class="pg" href="<?php echo $baseUrl; ?>">1</a>
                <?php if ($winStart > 2): ?><span class="pg-dot">…</span><?php endif; ?>
                <?php endif; ?>
                <?php for ($p = $winStart; $p <= $winEnd; $p++): ?>
                    <?php if ($p === $page): ?>
                <span class="pg on"><?php echo $p; ?></span>
                    <?php else: ?>
                <a class="pg" href="<?php echo $p === 1 ? $baseUrl : $baseUrl . '?page=' . $p; ?>"><?php echo $p; ?></a>
                    <?php endif; ?>
                <?php endfor; ?>
                <?php if ($winEnd < $totalPages): ?>
                <?php if ($winEnd < $totalPages - 1): ?><span class="pg-dot">…</span><?php endif; ?>
                <a class="pg" href="<?php echo $baseUrl . '?page=' . $totalPages; ?>"><?php echo $totalPages; ?></a>
                <?php endif; ?>
                <?php if ($page < $totalPages): ?>
                <a class="pg" href="<?php echo $baseUrl . '?page=' . ($page + 1); ?>"><?php echo e('下一页 →'); ?></a>
                <?php endif; ?>
            </nav>
            <?php endif; ?>
        </div>
        <?php else: ?>
        <div class="content-card">
            <h5><?php echo e('📝 帖子'); ?></h5>
            <p style="color: #888; font-size: 14px; margin: 0;"><?php echo e('这个账号还没有发过帖子'); ?></p>
        </div>
        <?php endif; ?>"""

reps.append((old_list, new_list))

# ── 应用并断言每条只命中一次 ──
for i, (a, b) in enumerate(reps, 1):
    n = txt.count(a)
    assert n == 1, '替换 %d 命中 %d 次（应为 1）: %r' % (i, n, a[:60])
    txt = txt.replace(a, b, 1)
    print('[1] 替换 %d 命中 1 次 OK  %s…' % (i, a.strip().split('\n')[0][:52]))

# ── 自检 ──
checks = [
    ('SQL 里不再有 LIMIT 5',     'LIMIT 5")' not in txt and txt.count('LIMIT 5') == 1),   # 唯一 1 次在注释里
    ('pageSize = 20 存在',       '$pageSize = 20;' in txt),
    ('OFFSET 拼接存在',          'OFFSET " . $offset' in txt),
    ('canonical 带 page',        "$canonicalPath .= '?page=' . $page" in txt),
    ('pager 样式 5 条',          txt.count('.pager') == 5),
    ('count-badge 样式 1 条',    txt.count('.count-badge') == 1),
    ('空状态分支存在',           '这个账号还没有发过帖子' in txt),
    ('board_title 字段被用',     "board_title" in txt),
    ('<?php 与 ?> 配平',         txt.count('<?php') == txt.count('?>')),
]
for name, ok in checks:
    print('    %-22s %s' % (name, 'PASS' if ok else 'FAIL'))
assert all(ok for _, ok in checks), '自检未通过'

crlf = txt.replace('\n', '\r\n')
print('\n[2] 新文件 %d 字节 / %d 行 / CRLF=%d'
      % (len(crlf.encode('utf-8')), len(txt.split('\n')), crlf.count('\r\n')))
OUT.write_bytes(crlf.encode('utf-8'))
print('[2] 已写本地', OUT, OUT.stat().st_size, 'B  md5=', hashlib.md5(OUT.read_bytes()).hexdigest())
