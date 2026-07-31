<?php
/**
 * 7Tan 客户端流量统计 - 管理后台页面
 * 
 * 展示 7Tan 桌面软件的日活/新增/留存/版本分布等指标。
 * 使用管理后台统一的 config.php → getDB() PDO 连接。
 */

// ── 加载管理后台配置 ──
$config_file = __DIR__ . '/config.php';
if (!file_exists($config_file)) {
    die('config.php not found. Please upload config.php to the same directory.');
}
require_once $config_file;

// 使用 config.php 提供的 getDB()
if (!function_exists('getDB')) {
    die('getDB() not found in config.php');
}
$db = getDB();

// ── 确保表存在（首次访问自动建表）──
$db->exec("
    CREATE TABLE IF NOT EXISTS `7tan_client_sessions` (
        `id` INT AUTO_INCREMENT PRIMARY KEY,
        `device_id` VARCHAR(32) NOT NULL,
        `version` VARCHAR(16) DEFAULT 'unknown',
        `username` VARCHAR(64) DEFAULT '',
        `first_date` DATE NOT NULL,
        `last_active` DATETIME NOT NULL,
        `type` VARCHAR(10) DEFAULT '新设备',
        `ip_address` VARCHAR(45) DEFAULT '',
        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX `idx_device` (`device_id`),
        INDEX `idx_last_active` (`last_active`),
        INDEX `idx_first_date` (`first_date`),
        INDEX `idx_type` (`type`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
");

// ── 统计查询 ──
$today = date('Y-m-d');
$week_ago  = date('Y-m-d', strtotime('-7 days'));
$month_ago = date('Y-m-d', strtotime('-30 days'));

// 今日活跃
$stmt = $db->prepare("SELECT COUNT(DISTINCT device_id) AS cnt FROM 7tan_client_sessions WHERE DATE(last_active) = ?");
$stmt->execute([$today]);
$today_active = $stmt->fetch()['cnt'] ?? 0;

// 7日活跃
$stmt = $db->prepare("SELECT COUNT(DISTINCT device_id) AS cnt FROM 7tan_client_sessions WHERE last_active >= ?");
$stmt->execute([$week_ago]);
$week_active = $stmt->fetch()['cnt'] ?? 0;

// 30日活跃
$stmt = $db->prepare("SELECT COUNT(DISTINCT device_id) AS cnt FROM 7tan_client_sessions WHERE last_active >= ?");
$stmt->execute([$month_ago]);
$month_active = $stmt->fetch()['cnt'] ?? 0;

// 今日新增
$stmt = $db->prepare("SELECT COUNT(*) AS cnt FROM 7tan_client_sessions WHERE first_date = ?");
$stmt->execute([$today]);
$today_new = $stmt->fetch()['cnt'] ?? 0;

// 累计设备
$stmt = $db->query("SELECT COUNT(*) AS cnt FROM 7tan_client_sessions");
$total_devices = $stmt->fetch()['cnt'] ?? 0;

// 7日留存率
$seven_days_ago = date('Y-m-d', strtotime('-7 days'));
$stmt = $db->prepare("
    SELECT 
        (SELECT COUNT(DISTINCT device_id) FROM 7tan_client_sessions 
         WHERE first_date = ? AND last_active > DATE_ADD(first_date, INTERVAL 1 DAY)) AS retained,
        (SELECT COUNT(*) FROM 7tan_client_sessions WHERE first_date = ?) AS total
");
$stmt->execute([$seven_days_ago, $seven_days_ago]);
$retention = $stmt->fetch();
$retention_rate = ($retention['total'] ?? 0) > 0 
    ? round(($retention['retained'] ?? 0) / $retention['total'] * 100, 1) 
    : 0;

// 近7日版本分布
$stmt = $db->prepare("SELECT version, COUNT(*) AS cnt FROM 7tan_client_sessions WHERE last_active >= ? GROUP BY version ORDER BY cnt DESC LIMIT 10");
$stmt->execute([$week_ago]);
$versions = $stmt->fetchAll();

// 近30日活跃趋势（按日汇总）
$stmt = $db->prepare("
    SELECT 
        DATE(last_active) AS dt,
        COUNT(DISTINCT device_id) AS active,
        SUM(CASE WHEN first_date = DATE(last_active) THEN 1 ELSE 0 END) AS new_cnt
    FROM 7tan_client_sessions 
    WHERE last_active >= ?
    GROUP BY dt 
    ORDER BY dt DESC 
    LIMIT 30
");
$stmt->execute([$month_ago]);
$daily_stats = array_reverse($stmt->fetchAll());

// 最近 ping 记录
$stmt = $db->query("
    SELECT device_id, version, first_date, last_active, type, username 
    FROM 7tan_client_sessions 
    ORDER BY last_active DESC 
    LIMIT 20
");
$recent_pings = $stmt->fetchAll();

// ── 辅助函数 ──
function mask_id($id) {
    return strlen($id) > 8 ? substr($id, 0, 8) . '...' : $id;
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

        .header { margin-bottom: 24px; }
        .header h1 { font-size: 22px; font-weight: 700; color: var(--text); }
        .header .subtitle { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }

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
        .card .number { font-size: 32px; font-weight: 700; color: var(--accent); }
        .card .label { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }
        .card.green .number { color: var(--green); }
        .card.orange .number { color: var(--orange); }
        .card.red .number { color: var(--red); }

        .section {
            background: var(--card-bg);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            border: 1px solid var(--border);
            padding: 20px;
            margin-bottom: 20px;
        }
        .section h2 {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 14px;
            color: var(--text);
            border-bottom: 2px solid var(--accent-light);
            padding-bottom: 8px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }
        th, td {
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }
        th { background: #f8f9fa; font-weight: 600; color: var(--text-secondary); white-space: nowrap; }
        tr:hover { background: #f8f9ff; }

        .tag {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
        }
        .tag-new { background: #d5f5e3; color: #27ae60; }
        .tag-return { background: #e8daef; color: #8e44ad; }

        .bar-chart { display: flex; align-items: flex-end; gap: 3px; height: 120px; padding: 8px 0; }
        .bar-chart .bar-wrap { flex: 1; display: flex; flex-direction: column; align-items: center; height: 100%; justify-content: flex-end; }
        .bar-chart .bar { width: 100%; max-width: 20px; background: var(--accent); border-radius: 3px 3px 0 0; min-height: 2px; transition: height .3s; position: relative; }
        .bar-chart .bar.new-bar { background: var(--green); max-width: 8px; margin-left: 1px; }
        .bar-chart .bar-label { font-size: 9px; color: var(--text-secondary); margin-top: 3px; transform: rotate(-45deg); transform-origin: top left; white-space: nowrap; }
        .bar-chart .bar-value { font-size: 9px; color: var(--text-secondary); margin-bottom: 1px; }

        .empty { text-align: center; color: var(--text-secondary); padding: 40px; font-size: 14px; }

        @media (max-width: 768px) {
            .cards { grid-template-columns: repeat(2, 1fr); }
            body { padding: 12px; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 7Tan 客户端流量统计</h1>
        <div class="subtitle">统计 7Tan 桌面软件的日活/新增/留存/版本分布</div>
    </div>

    <!-- 统计卡片 -->
    <div class="cards">
        <div class="card">
            <div class="number"><?= number_format($today_active) ?></div>
            <div class="label">📅 今日活跃</div>
        </div>
        <div class="card green">
            <div class="number"><?= number_format($week_active) ?></div>
            <div class="label">📆 7日活跃</div>
        </div>
        <div class="card">
            <div class="number"><?= number_format($month_active) ?></div>
            <div class="label">📈 30日活跃</div>
        </div>
        <div class="card green">
            <div class="number"><?= number_format($today_new) ?></div>
            <div class="label">✨ 今日新增</div>
        </div>
        <div class="card">
            <div class="number"><?= number_format($total_devices) ?></div>
            <div class="label">💻 累计设备</div>
        </div>
        <div class="card orange">
            <div class="number"><?= $retention_rate ?>%</div>
            <div class="label">🔁 7日留存率</div>
        </div>
    </div>

    <!-- 30日趋势 -->
    <div class="section">
        <h2>📈 近30日活跃趋势</h2>
        <?php if (empty($daily_stats)): ?>
            <div class="empty">暂无数据，等待客户端上报</div>
        <?php else: ?>
            <div class="bar-chart">
                <?php 
                $max_val = 1;
                foreach ($daily_stats as $d) { $max_val = max($max_val, $d['active']); }
                foreach ($daily_stats as $d): 
                    $h = $max_val > 0 ? round($d['active'] / $max_val * 100) : 0;
                    $date_label = substr($d['dt'], 5);
                ?>
                <div class="bar-wrap">
                    <div class="bar-value"><?= $d['active'] ?></div>
                    <div class="bar" style="height:<?= $h ?>px" title="<?= $d['dt'] ?>: 活跃<?= $d['active'] ?> 新增<?= $d['new_cnt'] ?>"></div>
                    <div class="bar-label"><?= $date_label ?></div>
                </div>
                <?php endforeach; ?>
            </div>
        <?php endif; ?>
    </div>

    <!-- 版本分布 -->
    <div class="section">
        <h2>📱 近7日版本分布</h2>
        <?php if (empty($versions)): ?>
            <div class="empty">暂无数据</div>
        <?php else: ?>
            <table>
                <thead>
                    <tr><th>版本</th><th>设备数</th><th>占比</th></tr>
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
                        <td><?= $pct ?>%</td>
                    </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
        <?php endif; ?>
    </div>

    <!-- 最近活动 -->
    <div class="section">
        <h2>📋 最近活动记录</h2>
        <?php if (empty($recent_pings)): ?>
            <div class="empty">暂无数据，等待客户端上报</div>
        <?php else: ?>
            <table>
                <thead>
                    <tr><th>设备ID</th><th>版本</th><th>用户名</th><th>类型</th><th>首次出现</th><th>最后活跃</th></tr>
                </thead>
                <tbody>
                    <?php foreach ($recent_pings as $r): ?>
                    <tr>
                        <td><code><?= mask_id($r['device_id']) ?></code></td>
                        <td><?= htmlspecialchars($r['version']) ?></td>
                        <td><?= htmlspecialchars($r['username'] ?: '-') ?></td>
                        <td><span class="tag <?= $r['type'] === '新设备' ? 'tag-new' : 'tag-return' ?>"><?= $r['type'] ?></span></td>
                        <td><?= $r['first_date'] ?></td>
                        <td><?= $r['last_active'] ?></td>
                    </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
        <?php endif; ?>
    </div>
</body>
</html>
