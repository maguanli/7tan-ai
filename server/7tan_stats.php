<?php
/**
 * 7Tan 客户端流量统计 - 管理后台页面
 * 
 * 展示 7Tan 桌面软件的日活/新增/留存/版本分布等指标。
 * 风格参考泼猴编译神器的 apktool_stats.php。
 * 
 * 部署方式:
 *   1. 上传本文件到 img.7tan.cn 根目录
 *   2. 在管理后台侧边栏「统计」下添加入口链接
 */

// ── 权限检查 ──
session_start();
$is_logged_in = isset($_SESSION['admin_id']) || isset($_SESSION['user_id']);

// ── 数据库连接 ──
$config_file = __DIR__ . '/config.php';
if (!file_exists($config_file)) {
    die('config.php not found. Please upload config.php to the same directory as 7tan_stats.php.');
}
require_once $config_file;

if (!isset($conn) || !($conn instanceof mysqli)) {
    die('db connection not configured in config.php');
}

// ── 统计查询 ──
$today = date('Y-m-d');
$week_ago  = date('Y-m-d', strtotime('-7 days'));
$month_ago = date('Y-m-d', strtotime('-30 days'));

// 今日活跃
$r = $conn->query("SELECT COUNT(DISTINCT device_id) AS cnt FROM 7tan_client_sessions WHERE DATE(last_active) = '$today'");
$today_active = $r ? $r->fetch_assoc()['cnt'] : 0;

// 7日活跃
$r = $conn->query("SELECT COUNT(DISTINCT device_id) AS cnt FROM 7tan_client_sessions WHERE last_active >= '$week_ago'");
$week_active = $r ? $r->fetch_assoc()['cnt'] : 0;

// 30日活跃
$r = $conn->query("SELECT COUNT(DISTINCT device_id) AS cnt FROM 7tan_client_sessions WHERE last_active >= '$month_ago'");
$month_active = $r ? $r->fetch_assoc()['cnt'] : 0;

// 今日新增
$r = $conn->query("SELECT COUNT(*) AS cnt FROM 7tan_client_sessions WHERE first_date = '$today'");
$today_new = $r ? $r->fetch_assoc()['cnt'] : 0;

// 累计设备
$r = $conn->query("SELECT COUNT(*) AS cnt FROM 7tan_client_sessions");
$total_devices = $r ? $r->fetch_assoc()['cnt'] : 0;

// 7日留存率: (7天前新增的、且7天内回来过的) ÷ 7天前新增总数
$seven_days_ago = date('Y-m-d', strtotime('-7 days'));
$r = $conn->query("
    SELECT 
        (SELECT COUNT(DISTINCT device_id) FROM 7tan_client_sessions 
         WHERE first_date = '$seven_days_ago' AND last_active > DATE_ADD(first_date, INTERVAL 1 DAY)) AS retained,
        (SELECT COUNT(*) FROM 7tan_client_sessions WHERE first_date = '$seven_days_ago') AS total
");
$retention = $r ? $r->fetch_assoc() : ['retained' => 0, 'total' => 0];
$retention_rate = $retention['total'] > 0 ? round($retention['retained'] / $retention['total'] * 100, 1) : 0;

// 近7日版本分布
$versions = [];
$r = $conn->query("SELECT version, COUNT(*) AS cnt FROM 7tan_client_sessions WHERE last_active >= '$week_ago' GROUP BY version ORDER BY cnt DESC LIMIT 10");
if ($r) {
    while ($row = $r->fetch_assoc()) {
        $versions[] = $row;
    }
}

// 近30日活跃趋势（按日汇总）
$daily_stats = [];
$r = $conn->query("
    SELECT 
        DATE(last_active) AS dt,
        COUNT(DISTINCT device_id) AS active,
        SUM(CASE WHEN first_date = DATE(last_active) THEN 1 ELSE 0 END) AS new_cnt
    FROM 7tan_client_sessions 
    WHERE last_active >= '$month_ago'
    GROUP BY dt 
    ORDER BY dt DESC 
    LIMIT 30
");
if ($r) {
    while ($row = $r->fetch_assoc()) {
        $daily_stats[] = $row;
    }
}
// 正序
$daily_stats = array_reverse($daily_stats);

// 最近 ping 记录
$recent_pings = [];
$r = $conn->query("
    SELECT device_id, version, first_date, last_active, type, username 
    FROM 7tan_client_sessions 
    ORDER BY last_active DESC 
    LIMIT 20
");
if ($r) {
    while ($row = $r->fetch_assoc()) {
        $recent_pings[] = $row;
    }
}

// ── 辅助函数 ──
function mask_id($id) {
    if (strlen($id) > 8) {
        return substr($id, 0, 8) . '...';
    }
    return $id;
}

// ── 页面渲染 ──
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>7Tan 客户端流量统计 - 7坛游戏社区 管理后台</title>
    <style>
        :root {
            --bg: #f5f6fa;
            --card-bg: #fff;
            --text: #2d3436;
            --text-secondary: #636e72;
            --accent: #6c5ce7;
            --accent-light: #a29bfe;
            --green: #00b894;
            --orange: #fdcb6e;
            --red: #e17055;
            --border: #dfe6e9;
            --shadow: 0 2px 8px rgba(0,0,0,.06);
            --radius: 10px;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC',
                         'Microsoft YaHei', sans-serif;
            background: var(--bg);
            color: var(--text);
            padding: 24px;
            line-height: 1.6;
        }

        .header {
            margin-bottom: 24px;
        }
        .header h1 {
            font-size: 22px;
            font-weight: 700;
            color: var(--text);
        }
        .header .subtitle {
            font-size: 13px;
            color: var(--text-secondary);
            margin-top: 4px;
        }

        /* ── 统计卡片 ── */
        .cards {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
            gap: 14px;
            margin-bottom: 24px;
        }
        .card {
            background: var(--card-bg);
            border-radius: var(--radius);
            padding: 18px 20px;
            box-shadow: var(--shadow);
            border: 1px solid var(--border);
            text-align: center;
            transition: transform .15s;
        }
        .card:hover { transform: translateY(-2px); }
        .card .number {
            font-size: 32px;
            font-weight: 700;
            color: var(--accent);
        }
        .card .label {
            font-size: 13px;
            color: var(--text-secondary);
            margin-top: 4px;
        }
        .card.green .number { color: var(--green); }
        .card.orange .number { color: var(--orange); }
        .card.red .number { color: var(--red); }

        /* ── 表格 ── */
        .section {
            background: var(--card-bg);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            border: 1px solid var(--border);
            margin-bottom: 20px;
            overflow: hidden;
        }
        .section-title {
            font-size: 15px;
            font-weight: 600;
            padding: 14px 20px;
            border-bottom: 1px solid var(--border);
            background: #fafbfc;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 10px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border);
            font-size: 13px;
        }
        th {
            background: #f8f9fa;
            font-weight: 600;
            color: var(--text-secondary);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: .5px;
        }
        tr:hover td { background: #f8f9ff; }

        .badge {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
        }
        .badge-new { background: #e8f8f5; color: #00b894; }
        .badge-return { background: #eef0ff; color: #6c5ce7; }
        .badge-unknown { background: #f1f2f6; color: #636e72; }

        .empty {
            text-align: center;
            color: #b2bec3;
            padding: 40px;
        }

        .trend-cell {
            display: flex;
            gap: 4px;
            align-items: center;
        }
        .trend-bar {
            height: 6px;
            border-radius: 3px;
            background: var(--accent-light);
            min-width: 2px;
        }

        .footer-note {
            text-align: center;
            color: var(--text-secondary);
            font-size: 12px;
            margin-top: 16px;
        }
    </style>
</head>
<body>

<div class="header">
    <h1>📊 7Tan 客户端 · 流量统计</h1>
    <p class="subtitle">客户端启动即上报匿名标识 + 版本号，不涉及用户隐私</p>
</div>

<!-- 统计卡片 -->
<div class="cards">
    <div class="card">
        <div class="number"><?= $today_active ?></div>
        <div class="label">今日活跃</div>
    </div>
    <div class="card">
        <div class="number"><?= $week_active ?></div>
        <div class="label">7日活跃</div>
    </div>
    <div class="card green">
        <div class="number"><?= $month_active ?></div>
        <div class="label">30日活跃</div>
    </div>
    <div class="card orange">
        <div class="number"><?= $today_new ?></div>
        <div class="label">今日新增</div>
    </div>
    <div class="card">
        <div class="number"><?= $total_devices ?></div>
        <div class="label">累计设备</div>
    </div>
    <div class="card red">
        <div class="number"><?= $retention_rate ?>%</div>
        <div class="label">7日留存率</div>
    </div>
</div>

<!-- 版本分布 -->
<div class="section">
    <div class="section-title">📱 近7日版本分布</div>
    <?php if (empty($versions)): ?>
        <div class="empty">暂无数据</div>
    <?php else: ?>
        <table>
            <thead>
                <tr><th>版本</th><th>活跃设备数</th><th>占比</th></tr>
            </thead>
            <tbody>
                <?php 
                $total_ver = array_sum(array_column($versions, 'cnt'));
                foreach ($versions as $v): 
                    $pct = $total_ver > 0 ? round($v['cnt'] / $total_ver * 100, 1) : 0;
                ?>
                <tr>
                    <td><strong><?= htmlspecialchars($v['version']) ?></strong></td>
                    <td><?= $v['cnt'] ?></td>
                    <td>
                        <div class="trend-cell">
                            <div class="trend-bar" style="width:<?= max($pct * 2, 2) ?>px;"></div>
                            <?= $pct ?>%
                        </div>
                    </td>
                </tr>
                <?php endforeach; ?>
            </tbody>
        </table>
    <?php endif; ?>
</div>

<!-- 近30日活跃趋势 -->
<div class="section">
    <div class="section-title">📈 近30日活跃趋势</div>
    <?php if (empty($daily_stats)): ?>
        <div class="empty">暂无数据</div>
    <?php else: ?>
        <table>
            <thead>
                <tr><th>日期</th><th>活跃</th><th>新增</th><th>趋势</th></tr>
            </thead>
            <tbody>
                <?php 
                $max_active = max(array_column($daily_stats, 'active')) ?: 1;
                foreach ($daily_stats as $d): 
                    $bar_w = max(round($d['active'] / $max_active * 200), 2);
                ?>
                <tr>
                    <td><?= htmlspecialchars($d['dt']) ?></td>
                    <td><strong><?= $d['active'] ?></strong></td>
                    <td><?= $d['new_cnt'] ?></td>
                    <td>
                        <div class="trend-cell">
                            <div class="trend-bar" style="width:<?= $bar_w ?>px;"></div>
                            <?= $d['active'] ?>
                        </div>
                    </td>
                </tr>
                <?php endforeach; ?>
            </tbody>
        </table>
    <?php endif; ?>
</div>

<!-- 最近 Ping 记录 -->
<div class="section">
    <div class="section-title">📋 最近 Ping 记录</div>
    <?php if (empty($recent_pings)): ?>
        <div class="empty">暂无数据</div>
    <?php else: ?>
        <table>
            <thead>
                <tr>
                    <th>设备ID</th>
                    <th>版本</th>
                    <th>首次出现</th>
                    <th>用户名</th>
                    <th>类型</th>
                    <th>最后活跃</th>
                </tr>
            </thead>
            <tbody>
                <?php foreach ($recent_pings as $p): 
                    $badge_class = ($p['type'] === '新设备') ? 'badge-new' : (($p['type'] === '回头客') ? 'badge-return' : 'badge-unknown');
                ?>
                <tr>
                    <td><code><?= htmlspecialchars(mask_id($p['device_id'])) ?></code></td>
                    <td><?= htmlspecialchars($p['version']) ?></td>
                    <td><?= htmlspecialchars($p['first_date']) ?></td>
                    <td><?= $p['username'] ? htmlspecialchars($p['username']) : '<em style="color:#b2bec3">匿名</em>' ?></td>
                    <td><span class="badge <?= $badge_class ?>"><?= htmlspecialchars($p['type']) ?></span></td>
                    <td><?= htmlspecialchars($p['last_active']) ?></td>
                </tr>
                <?php endforeach; ?>
            </tbody>
        </table>
    <?php endif; ?>
</div>

<div class="footer-note">
    💡 提示：将此页面链接添加到管理后台侧边栏「统计」菜单下即可快速访问
</div>

</body>
</html>
