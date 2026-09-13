# 7Tan 客户端流量统计 — 服务端部署说明

## 📁 文件清单

```
server/
├── api/
│   └── 7tan_ping.php        ← 客户端心跳 API
├── 7tan_stats.php            ← 管理后台统计页面
├── sql/
│   └── create_table.sql      ← 建表 SQL
└── README.md                 ← 本文件
```

## 🚀 部署步骤

### 1. 上传文件到服务器

将 `server/` 目录下的文件上传到 `img.7tan.com`：

```
api/7tan_ping.php  →  https://img.7tan.com/api/7tan_ping.php
7tan_stats.php     →  https://img.7tan.com/7tan_stats.php
```

### 2. 建表

在 phpMyAdmin 中执行 `sql/create_table.sql`，或者直接访问一次 API（会自动建表）：

```
https://img.7tan.com/api/7tan_ping.php?id=test123456789012&ver=5.1.0
```

### 3. 数据库连接配置

如果现有系统没有 `config.php` 中定义 `$conn`，请修改两个 PHP 文件中的数据库连接信息：

```php
$db_host = 'localhost';   // 数据库主机
$db_user = '7tan';        // 数据库用户名
$db_pass = '';            // 数据库密码
$db_name = '7tan';        // 数据库名称
```

### 4. 管理后台添加入口

在管理后台侧边栏 HTML 中，找到「统计」分组，添加：

```html
<li><a href="7tan_stats.php">📊 7Tan客户端流量</a></li>
```

## 📡 API 文档

### POST/GET `/api/7tan_ping.php`

| 参数 | 必填 | 说明 |
|------|:---:|------|
| `id` | ✅ | 16位匿名设备标识 |
| `ver` | ❌ | 客户端版本号，如 `5.1.0` |
| `user` | ❌ | 用户名（用于关联） |

**返回示例：**
```json
{"ok": true}
```

## 📊 统计指标说明

| 指标 | 计算方式 |
|------|---------|
| 今日活跃 | `last_active` 为今天的去重设备数 |
| 7日活跃 | `last_active` 在近7天的去重设备数 |
| 30日活跃 | `last_active` 在近30天的去重设备数 |
| 今日新增 | `first_date` 为今天的设备数 |
| 累计设备 | 表中总记录数 |
| 7日留存率 | 7天前新增的、且第2天之后回来过的比例 |

## ⚠️ 隐私说明

- 仅收集 16 位随机 GUID（非设备硬件信息）
- 不收集 IP 地址以外的任何个人信息
- 用户名仅在用户登录后附带（可选）
- 数据仅用于日活/留存/版本分布统计
