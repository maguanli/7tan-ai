# 7tan.com 网站端 — 专业版系统增量文件

## 📂 文件清单（共 11 个文件，5 个目录）

```
website/
│
├── 📖 README.md                      ← 本文件
│
├── 📁 config/
│   └── database.php                  ← ⚠️ 模板文件！需合并到现有数据库配置
│
├── 📁 database/
│   └── migration.sql                 ← 【B1】数据库迁移 SQL
│
├── 📁 lib/
│   ├── jwt_helper.php                ← JWT 编解码工具（login/verify/refresh 依赖）
│   └── auth_middleware.php            ← 登录验证中间件（pro API 依赖）
│
├── 📁 api/
│   ├── 📁 auth/
│   │   ├── login.php                 ← 【B2】登录 API
│   │   ├── verify.php                ← 【B3】验证 Token API
│   │   └── refresh.php               ← 【B4】刷新 Token API
│   │
│   └── 📁 pro/
│       ├── purchase.php              ← 【B5a】购买专业版 API
│       └── status.php                ← 【B5b】查询专业版状态 API
│
├── 📁 user/
│   └── 📁 pro/
│       └── index.php                 ← 【B5c】购买专业版前端页面
│
└── 📁 cron/
    └── check_expiry.php              ← 【B6】到期检查脚本
```

---

## 🚀 上传步骤（按顺序）

### 1️⃣ 数据库迁移
在 phpMyAdmin 或 MySQL 命令行执行：
```
执行 database/migration.sql
```
这会给 `ll_useregs` 表增加 `pro_activated` 和 `pro_expires` 两个字段。

### 2️⃣ 上传 lib/ 目录
把 `lib/jwt_helper.php` 和 `lib/auth_middleware.php` 上传到网站 `/lib/` 目录。

### 3️⃣ 上传 api/ 目录
把 `api/auth/` 和 `api/pro/` 下的 5 个文件上传到对应路径。

### 4️⃣ 上传前端页面
把 `user/pro/index.php` 上传到 `/user/pro/index.php`。

### 5️⃣ 上传 cron 脚本
把 `cron/check_expiry.php` 上传到 `/cron/check_expiry.php`。
设置 crontab：
```
0 2 * * * /usr/bin/php /www/wwwroot/7tan.com/cron/check_expiry.php >> /www/wwwroot/7tan.com/logs/expiry.log 2>&1
```

### 6️⃣ 配置整合
`config/database.php` 是模板文件。
- 如果网站已有数据库配置 → 只复制 `JWT_SECRET` 定义过去
- 如果网站已有 `get_db_connection()` → 忽略此文件
- 修改 `JWT_SECRET` 为一个随机的 64 字符密钥

---

## ⚠️ 注意事项

| 文件 | 需要适配的内容 |
|:--|:--|
| `config/database.php` | 合并到现有数据库配置 |
| `api/auth/login.php` | 密码加密方式（md5 / password_hash），根据现有系统调整 |
| `user/pro/index.php` | `$current_user` 变量来源，根据现有 Session 框架调整 |
| `cron/check_expiry.php` | `user_messages` 表名，根据现有站内信系统调整 |
| 所有 API 文件 | `get_db_connection()` 函数，确保与现有系统一致 |

---

## 🔗 客户端对应

| 网站 API | 客户端调用方 |
|:--|:--|
| `POST /api/auth/login.php` | `src/security/auth_client.py` → `login()` |
| `GET /api/auth/verify.php` | `src/security/auth_client.py` → `verify()` |
| `GET /api/auth/refresh.php` | `src/ui/pro_status_widget.py` → [刷新状态] 按钮 |
| `POST /api/pro/purchase.php` | `user/pro/index.php` → [立即购买] 按钮 |
