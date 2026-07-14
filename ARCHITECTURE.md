# 7坛AI小编 — 架构文档 v5.1

> **软件名称**: 7坛AI小编
> **运行平台**: Windows 桌面 / Windows Server / Linux 服务器
> **UI 方式**: 精美 Web 管理面板（深色主题 + 毛玻璃 + 渐变光效）⭐
> **打包方式**: PyInstaller 打包为独立 exe，免安装绿色运行
>
> **⚠️ 文档状态说明**: 本文档为完整设计目标文档。当前代码库处于早期骨架阶段，
> 大部分模块尚未实现。配置文件统一使用 YAML 格式（config.yaml）。
> 文档中标注 `[已实现]` 的部分已有对应代码，其余为设计目标。

---

## 一、系统概述

### 1.1 四大核心能力

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  ① 自动发布    AI 自主爬取源站 → 下载资源                  │
│               → 改写内容 → 自动上传OSS → 发布到7坛         │
│               ✅ 支持游戏    ✅ 支持软件                   │
│               ✅ 新品首发    ✅ 版本更新                   │
│               ✅ 上传成功后自动删除本地包，释放磁盘          │
│                                                          │
│  ② AI 对话     在精美的 Web 面板中与 AI 实时聊天            │
│               问进度、给指令、提需求、打字机效果回复          │
│                                                          │
│  ③ 可视化监控  仪表盘、任务进度、资源管理、数据统计          │
│               一切尽在 Web 面板，实时 WebSocket 推送        │
│                                                          │
│  ④ 自我进化    AI 根据用户要求修改自己的代码                │
│               "把这个功能改一下" → AI 自己改源码            │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 1.2 与传统采集器的本质区别

| 对比维度 | 传统采集器 | 本系统 |
|----------|-----------|--------|
| 源站适配 | 每个站写 CSS 选择器 | AI 自己看懂网页 |
| 内容提取 | 正则/模板硬提取 | AI 阅读理解后提取 |
| 内容改写 | 固定模板替换 | AI 像真人编辑一样重写 |
| 新站接入 | 需要开发写代码 | 告诉 AI 网址就行 |
| 用户交互 | 无，只能改配置 | **精美 Web 面板，可视化操作** |
| 功能修改 | 改代码重新编译 | **AI 自己改自己** |
| 模型选择 | 绑定固定模型 | **任意兼容 API 的模型** |
| 部署方式 | pip install 一堆依赖 | **PyInstaller 打包 exe，免安装** |
| 资源类型 | 通常只支持游戏 | **游戏 + 软件双类目** |
| 版本更新 | 无 | **自动检测版本升级并更新** |

---

## 二、部署与打包方案

### 2.1 绿色免安装设计

```
开发阶段:
  python main.py          ← 开发者运行方式

发布阶段（PyInstaller 打包）:
  7tan-updater.exe        ← 双击即用，无需 Python 环境

服务器部署:
  # Windows Server
  7tan-updater.exe --daemon    ← 后台守护进程模式

  # Linux 服务器
  ./7tan-updater --daemon      ← PyInstaller 也可打 Linux 包
```

### 2.2 PyInstaller 打包配置

```python
# build.spec — 打包配置
pyinstaller 7tan-updater.spec

# 产物:
# dist/
#   └── 7tan-updater.exe     (约 300-500MB，含 Python 运行时 + Playwright + Chromium 浏览器 + 依赖)
#   ⚠️ 注意: Playwright 的 Chromium 二进制约 300MB，因此最终产物远大于纯 Python 项目。
#      建议使用 --onedir 模式（而非 --onefile）以减小单文件体积和加快启动速度。
```

关键处理：
- Playwright 浏览器（Chromium）打包时一起打入，用户无需手动安装浏览器
- ⚠️ Chromium 二进制约 300MB，最终产物体积 300-500MB，需在发布说明中提前告知用户
- 推荐使用 `--onedir` 模式打包（启动更快，更新更方便），而非 `--onefile` 单文件模式
- `config.yaml` 放在 exe 同级目录，不打包进去，方便用户编辑
- `data/` `downloads/` `logs/` `backup/` 运行时自动创建

---

## 三、系统架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                         用户交互层                                     │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  🌐 Web 管理面板 (FastAPI + Vue 3 + WebSocket)                │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐    │   │
│  │  │📊仪表盘│ │💬AI对话│ │📦资源  │ │📋任务  │ │⚙️设置  │    │   │
│  │  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘    │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             │                                     │
│  ┌──────────────┐  ┌────────┴─────┐  ┌──────────────┐             │
│  │ 💬 CLI 对话   │  │ 🚀 发布模式   │  │ ⚙️ config.yaml │             │
│  │ (服务器保留)  │  │ 单次/定时执行  │  │  配置文件     │             │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘             │
│         │                 │                 │                       │
├─────────┴─────────────────┴─────────────────┴─────────────────────────┤
│                                                                       │
│                      🤖 AI Agent 核心引擎                              │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐ │  │
│  │  │ 思考循环   │  │ 工具调用  │  │ 记忆管理  │  │ 上下文窗口管理 │ │  │
│  │  │ThinkLoop │  │Tool Use  │  │ Memory   │  │ ContextMgr   │ │  │
│  │  └──────────┘  └────┬─────┘  └──────────┘  └───────────────┘ │  │
│  │                     │                                          │  │
│  │         ┌───────────┼───────────┐                              │  │
│  │         ▼           ▼           ▼                              │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐                       │  │
│  │  │ 任务队列  │ │ 并发控制  │ │ 异常恢复  │                       │  │
│  │  │TaskQueue │ │  Lock    │ │ RetryMgr │                       │  │
│  │  └──────────┘ └──────────┘ └──────────┘                       │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                │                                     │
├────────────────────────────────┼─────────────────────────────────────┤
│                                ▼                                     │
│                      🔧 AI 可调用的工具集                              │
│                                                                       │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────────┐│
│  │浏览器工具│ │下载工具  │ │OSS工具  │ │图片工具  │ │数据库工具      ││
│  │         │ │         │ │         │ │         │ │               ││
│  │打开网页  │ │🕷️蜘蛛下载│ │上传     │ │压缩     │ │查询/保存       ││
│  │点击元素  │ │🖥️浏览器下载│ │外链     │ │调整尺寸  │ │去重/统计       ││
│  │输入文字  │ │断点续传  │ │删除     │ │格式转换  │ │版本比较        ││
│  │截图     │ │速度限制  │ │         │ │         │ │               ││
│  │反检测   │ │大小检查  │ │         │ │         │ │               ││
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └───────────────┘│
│                                                                       │
│  ┌─────────┐ ┌─────────┐ ┌──────────────┐ ┌────────────────────────┐│
│  │发布工具  │ │内容工具  │ │自改进工具     │ │成本与监控工具           ││
│  │         │ │         │ │              │ │                        ││
│  │登录7坛  │ │提取信息  │ │读源码(沙箱)   │ │token_usage() 用量统计   ││
│  │填表单   │ │改写简介  │ │写源码(备份)   │ │cost_estimate() 费用估算  ││
│  │传图片   │ │敏感词   │ │diff预览      │ │disk_check() 磁盘检查     ││
│  │提交发布  │ │去水印   │ │重启         │ │health_check() 健康检查   ││
│  │验证结果  │ │         │ │              │ │🔐integrity_check() 完整性││
│  └─────────┘ └─────────┘ └──────────────┘ └────────────────────────┘│
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 四、数据库设计

### 4.1 资源表（支持游戏 + 软件）

> **技术说明**: 项目使用 SQLAlchemy ORM + aiosqlite（见 requirements.txt）。
> 以下 SQL 语句描述表结构设计，实际代码中通过 SQLAlchemy 模型类定义。
> `features`、`requirements`、`tags` 等 JSON 字段在 ORM 中使用 `JSON` 类型。

```sql
CREATE TABLE resources (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_type TEXT NOT NULL DEFAULT 'game',  -- 'game' | 'software'
    title         TEXT NOT NULL,
    original_title TEXT,                         -- 源站原标题
    alias         TEXT,                          -- 别名（搜索用）

    -- 来源信息
    source_url    TEXT,
    source_site   TEXT,                          -- 来源站点标识
    source_id     TEXT,                          -- 源站唯一ID（用于去重和版本比较）

    -- 分类（游戏/软件各有不同分类体系）
    category      TEXT,     -- 游戏: 动作/冒险/RPG/策略/模拟/...
                            -- 软件: 系统工具/办公/多媒体/安全/...

    -- 版本信息（支持版本更新） ⭐
    version       TEXT,                          -- 版本号，如 v2.1.3
    is_update     INTEGER DEFAULT 0,             -- 0=新发布 1=版本更新
    previous_id   INTEGER,                       -- 关联的上一版本资源ID
    update_log    TEXT,                          -- 更新日志/改了什么

    -- 基本信息
    platform      TEXT,     -- 游戏: PC/手游/Switch/PS5/...
                            -- 软件: Windows/macOS/Linux/全平台
    language      TEXT,                          -- 中文/英文/多语言
    file_size     TEXT,                          -- 如 "45.2 GB"
    file_size_bytes INTEGER,                     -- 字节数（用于磁盘检查）

    -- AI 改写后的内容
    intro         TEXT,                          -- 简介
    features      TEXT,                          -- JSON数组: 特色亮点
    requirements  TEXT,                          -- JSON: 系统要求/配置需求
    install_guide TEXT,                          -- 安装说明/激活说明
    tags          TEXT,                          -- JSON数组: 标签

    -- 资源文件
    logo_local     TEXT,                         -- 本地 LOGO 路径
    logo_remote    TEXT,                         -- 上传后的 LOGO URL
    screenshots_local  TEXT,                     -- JSON: 本地截图路径
    screenshots_remote TEXT,                     -- JSON: 上传后截图 URL

    -- 下载链接
    download_original TEXT,                      -- 原始下载链接
    download_oss     TEXT,                       -- OSS外链
    download_md5     TEXT,                       -- MD5校验
    package_local    TEXT,                       -- 本地文件路径

    -- 发布时间线
    source_publish_date TEXT,                    -- 源站发布日期
    status          TEXT DEFAULT 'pending',
    -- pending → scraping → scraped → rewriting → rewritten
    -- → downloading → downloaded → uploading → uploaded
    -- → reviewing → reviewed → publishing → published → failed

    publish_id      INTEGER,                     -- 7坛返回的发布ID
    publish_url     TEXT,                        -- 发布后的URL
    error_message   TEXT,

    -- Token 成本追踪 ⭐
    token_prompt    INTEGER DEFAULT 0,
    token_completion INTEGER DEFAULT 0,
    cost_estimate   REAL DEFAULT 0.0,            -- 预估费用（人民币）

    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    published_at    DATETIME
);

CREATE INDEX idx_resources_type ON resources(resource_type);
CREATE INDEX idx_resources_status ON resources(status);
CREATE INDEX idx_resources_source ON resources(source_site, source_id);
CREATE INDEX idx_resources_title ON resources(title);
```

### 4.2 任务日志表

```sql
CREATE TABLE task_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id INTEGER,
    task_type   TEXT,        -- browse/download/rewrite/upload/publish/review
    status      TEXT,        -- running/success/failed/retrying
    message     TEXT,
    retry_count INTEGER DEFAULT 0,
    started_at  DATETIME,
    finished_at DATETIME,
    FOREIGN KEY (resource_id) REFERENCES resources(id)
);
```

### 4.3 源站配置表

```sql
CREATE TABLE source_sites (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL,
    url            TEXT NOT NULL,
    site_type      TEXT DEFAULT 'game',        -- 'game' | 'software' | 'both'
    need_login     INTEGER DEFAULT 0,           -- 是否需要登录
    login_url      TEXT,
    login_username TEXT,
    login_password TEXT,                        -- ⚠️ 加密存储
    cookies_json   TEXT,                        -- 持久化 Cookie
    enabled        INTEGER DEFAULT 1,
    last_crawl_at  DATETIME,
    crawl_interval INTEGER DEFAULT 360,         -- 爬取间隔（分钟）
    notes          TEXT
);
```

### 4.4 对话历史表

```sql
CREATE TABLE conversation_history (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    role       TEXT,        -- 'user' | 'assistant' | 'tool'
    content    TEXT,
    tool_name  TEXT,
    session_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 五、资源类型设计（游戏 + 软件）⭐

### 5.1 双类型完整覆盖

```
┌──────────────────────────────────────────┐
│              资源类型                      │
│                                          │
│  🎮 游戏                                 │
│  ├── 动作冒险    ├── RPG角色扮演           │
│  ├── 策略战棋    ├── 模拟经营              │
│  ├── 射击游戏    ├── 体育竞速              │
│  ├── 独立游戏    ├── 恐怖解谜              │
│  ├── 网游/手游   └── 其他                  │
│                                          │
│  💻 软件                                 │
│  ├── 系统工具    ├── 办公效率              │
│  ├── 多媒体     ├── 图形设计               │
│  ├── 安全防护    ├── 网络工具              │
│  ├── 编程开发    ├── 教育教学              │
│  └── 其他                               │
└──────────────────────────────────────────┘
```

### 5.2 AI 提取时自动区分

AI 访问源站详情页后，自主判断是游戏还是软件：

```
游戏特征 → 有"游戏类型/玩法/剧情/配置要求/手柄支持"等关键词
软件特征 → 有"版本号/激活方式/系统兼容/功能列表/更新日志"等关键词
```

---

## 六、版本更新场景 ⭐

### 6.1 新发布 vs 版本更新

```
新发布（is_update=0）:
  源站出现全新资源 → 之前数据库没有 → 走完整发布流程

版本更新（is_update=1）:
  源站出现已有资源的更新版本 → AI 比较版本号 → 判断是否需要更新
  → 只下载新安装包 + 更新简介 + 在7坛发布"更新帖"
```

### 6.2 AI 判断更新的逻辑

```
1. 爬取到资源标题："XXX v3.2.1 最新版"
2. AI 调用 db_check("XXX") → 发现已有 v3.1.0
3. AI 比较: 3.2.1 > 3.1.0 → 是更新
4. AI 提取更新日志（源站页面上的 "更新内容" 区域）
5. AI 改写更新说明
6. 下载新包 → 上传 OSS（覆盖或新增）
7. 在7坛发布更新（标明"v3.1.0 → v3.2.1 更新"）
```

### 6.3 版本号提取

AI 自主从标题/页面内容中提取版本号：
- `v3.2.1` / `3.2.1`
- `2024.07.01` / `Build 240701`
- `最新版` / `正式版` / `稳定版`（不确定时标记为当前日期）

---

## 七、异常恢复与容错机制 ⭐

### 7.1 分级重试策略

```
┌─────────────┬──────────┬──────────┬─────────────┐
│   失败类型   │ 重试次数  │ 重试间隔  │  降级策略     │
├─────────────┼──────────┼──────────┼─────────────┤
│ API调用超时  │    5     │ 指数退避  │  跳过该步骤   │
│ API限流     │    3     │  60秒    │  等待后继续   │
│ 下载中断    │    3     │  立即    │  断点续传     │
│ 浏览器崩溃  │    2     │  30秒    │  重启浏览器   │
│ 7坛登录失败 │    3     │  120秒   │  标记失败     │
│ 7坛网站宕机 │    ∞     │  600秒   │  等待恢复     │
│ 磁盘不足    │    1     │   -      │  停止+告警    │
│ 验证码出现  │    0     │   -      │  暂停+通知用户 │
└─────────────┴──────────┴──────────┴─────────────┘
```

### 7.2 断点续传

```python
# 下载中断后恢复
def resume(url, local_path):
    existing_size = os.path.getsize(local_path) if os.path.exists(local_path) else 0
    headers = {"Range": f"bytes={existing_size}-"}
    response = requests.get(url, headers=headers, stream=True)

    # 先检查服务器是否支持断点续传
    if existing_size > 0 and response.headers.get("Accept-Ranges") != "bytes":
        # 不支持 Range，从头下载
        mode = "wb"
        existing_size = 0
    else:
        mode = "ab"

    # 检查返回的状态码：206=续传成功，200=服务器忽略了Range需从头下载
    if existing_size > 0 and response.status_code == 200:
        mode = "wb"
        existing_size = 0

    with open(local_path, mode) as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            f.write(chunk)
```

### 7.3 全局异常兜底

```
任何未捕获异常 → 
  1. 记录完整堆栈到 error 日志
  2. 标记当前步骤为 failed
  3. 尝试回到安全状态（关闭浏览器、清理临时文件）
  4. Agent 继续处理下一个资源（不因一个失败全崩）
```

---

## 八、反爬与反检测 ⭐

### 8.1 Playwright 反检测配置

```python
# 启动浏览器时的反检测参数
# headless 策略: 桌面模式默认 False（更像真人），服务器 --headless 模式时为 True
# 通过 config.yaml 的 无头模式 配置项控制
browser = playwright.chromium.launch(
    headless=config["network"]["headless"],  # 桌面默认False，服务器模式True
    args=[
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
        "--no-sandbox",
    ]
)

context = browser.new_context(
    viewport={"width": 1920, "height": 1080},
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
               "AppleWebKit/537.36 ...",   # 真实UA
    locale="zh-CN",
)

# 注入反检测脚本
page.add_init_script("""
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    // 覆盖更多检测点...
""")
```

### 8.2 访问频率控制

```
访问同一源站:
  - 页面间间隔: 随机 5~15 秒
  - 每次最多访问: 20 个页面/小时
  - 每日上限: 50 个页面/源站

AI 自主判断:
  - 如果页面返回 403/503 → 暂停该源站 30 分钟
  - 如果出现验证码 → 立即暂停并通知用户
```

### 8.3 搜索引擎蜘蛛模拟 ⭐

```
大多数游戏/软件源站会对普通浏览器用户施加严格的访问限制，
但会主动放行搜索引擎爬虫（为了让自己的资源能被搜到）。

策略: 爬取和下载时伪装成 Googlebot / Bingbot / 百度蜘蛛，
      源站会认为这是搜索引擎在索引页面，不会封 IP。
```

**双模式切换策略**:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  模式 A: 真人浏览器（Playwright）                                 │
│  ├── 用于: 需要 JS 渲染的页面、需要点击交互的操作                 │
│  ├── 用于: 7坛后台登录和发布（必须真实浏览器）                    │
│  └── UA: 真人 Chrome/Firefox                                     │
│                                                                  │
│  模式 B: 搜索引擎蜘蛛（requests / httpx）                         │
│  ├── 用于: 下载安装包、下载图片、获取静态页面内容                  │
│  ├── 优势: 不渲染JS → 速度极快、资源占用极小                      │
│  ├── 优势: 源站通常不限制爬虫 → 无需反检测                        │
│  └── UA: 搜索引擎爬虫 UA（Googlebot / Bingbot / 百度蜘蛛）        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**支持的搜索引擎蜘蛛 UA**:

```python
import random

# 各大搜索引擎蜘蛛的 User-Agent
SPIDER_UA_POOL = {
    # Google
    "googlebot_desktop": (
        "Mozilla/5.0 (compatible; Googlebot/2.1; "
        "+http://www.google.com/bot.html)"
    ),
    "googlebot_smartphone": (
        "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.94 "
        "Mobile Safari/537.36 (compatible; Googlebot/2.1; "
        "+http://www.google.com/bot.html)"
    ),
    
    # Bing
    "bingbot": (
        "Mozilla/5.0 (compatible; bingbot/2.0; "
        "+http://www.bing.com/bingbot.htm)"
    ),
    
    # 百度
    "baiduspider_desktop": (
        "Mozilla/5.0 (compatible; Baiduspider/2.0; "
        "+http://www.baidu.com/search/spider.html)"
    ),
    "baiduspider_mobile": (
        "Mozilla/5.0 (Linux; Android 10; MI 9) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.88 "
        "Mobile Safari/537.36 (compatible; Baiduspider-render/2.0; "
        "+http://www.baidu.com/search/spider.html)"
    ),
    
    # 搜狗
    "sogou_spider": (
        "Sogou web spider/4.0("
        "+http://www.sogou.com/docs/help/webmasters.htm#07)"
    ),
    
    # 360
    "360spider": (
        "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0); "
        "360Spider"
    ),
    
    # 神马 (UC)
    "shenma_spider": (
        "Mozilla/5.0 (compatible; YisouSpider; "
        "+https://help.sm.cn/help_center/robot.html)"
    ),
    
    # 字节跳动/头条
    "bytedance_spider": (
        "Mozilla/5.0 (compatible; Bytespider; "
        "spider-feedback@bytedance.com)"
    ),
    
    # Yandex (俄罗斯最大)
    "yandex_bot": (
        "Mozilla/5.0 (compatible; YandexBot/3.0; "
        "+http://yandex.com/bots)"
    ),
}

def get_spider_ua(engine: str = None) -> str:
    """随机获取一个搜索引擎蜘蛛 UA"""
    if engine:
        return SPIDER_UA_POOL[engine]
    return random.choice(list(SPIDER_UA_POOL.values()))

def get_spider_headers(engine: str = None) -> dict:
    """构造完整的蜘蛛请求头"""
    ua = get_spider_ua(engine)
    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
    }
```

**下载时的蜘蛛策略**:

```python
class SpiderDownloader:
    """伪装成搜索引擎蜘蛛进行下载"""
    
    def __init__(self, proxy: str = None):
        self.session = requests.Session()
        self.proxy = proxy
        
        # 随机选一个蜘蛛
        self.current_spider = random.choice(list(SPIDER_UA_POOL.keys()))
        self.session.headers.update(get_spider_headers(self.current_spider))
    
    def rotate_spider(self):
        """轮换蜘蛛身份（一个源站别一直用一个）"""
        available = [k for k in SPIDER_UA_POOL if k != self.current_spider]
        self.current_spider = random.choice(available)
        self.session.headers.update(get_spider_headers(self.current_spider))
        logger.debug(f"🕷️ 切换到蜘蛛: {self.current_spider}")
    
    def download(self, url: str, dest: str) -> str:
        """
        以搜索引擎蜘蛛身份下载文件
        
        速度优势:
          - 源站通常会为爬虫开放更大带宽（方便搜索引擎索引大文件）
          - 不会被限速/限流
          - 不触发验证码
        """
        # 每下载一个文件换一次蜘蛛
        self.rotate_spider()
        
        resp = self.session.get(url, stream=True, timeout=7200)
        resp.raise_for_status()
        
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024*1024):  # 1MB
                f.write(chunk)
                downloaded += len(chunk)
                # 进度回调（给 WebSocket 推送）
                if total:
                    progress = int(downloaded / total * 100)
                    yield {"progress": progress, "downloaded": downloaded, "total": total}
        
        # 验证完整性
        actual_md5 = file_md5(dest)
        logger.info(f"✅ 下载完成: {dest} (MD5: {actual_md5})")
        return dest
```

**蜘蛛下载 vs 浏览器下载对比**:

```
┌──────────────┬─────────────────────┬─────────────────────┐
│    对比维度   │   浏览器下载          │   蜘蛛下载           │
├──────────────┼─────────────────────┼─────────────────────┤
│ 适用场景     │ JS动态生成的下载链接  │ 静态直链下载         │
│ 速度         │ 慢（需渲染页面）      │ 快（纯HTTP下载）     │
│ 被封概率     │ 中（反检测可降低）    │ 极低（源站欢迎爬虫）  │
│ 资源占用     │ 高（Chromium进程）   │ 低（仅requests库）   │
│ 断点续传     │ 复杂                 │ 简单（HTTP Range）   │
│ 大文件支持   │ 一般                 │ 优秀（无内存压力）    │
│ 验证码风险   │ 有                   │ 几乎为零             │
└──────────────┴─────────────────────┴─────────────────────┘
```

**AI 自主决策逻辑**:

```
AI 在下载时自动判断使用哪种模式:

1. 先尝试蜘蛛模式（默认）
   → 成功下载 → ✅ 最快、最安全
   → 403/拒绝 → 切换到浏览器模式

2. 浏览器模式（兜底）
   → Playwright 打开页面 → 找到真实下载按钮 → 点击触发下载
   → 成功下载 → ✅
   → 仍需登录/付费 → 标记失败，通知用户

3. 蜘蛛智能轮换
   - 同一个源站: 每次请求换一个搜索引擎蜘蛛
   - 下载多个文件: 每个文件用不同蜘蛛
   - 如果某个蜘蛛被拦截: 自动切换到下一个
```

> **⚠️ 法律与合规风险提示**
>
> 伪装搜索引擎爬虫（伪造 User-Agent 冒充 Googlebot/Bingbot 等）存在以下风险：
>
> 1. **法律风险**：可能违反《网络安全法》《反不正当竞争法》等相关法律法规，
>    伪造身份获取非授权访问可能构成不正当竞争或侵权行为
> 2. **技术反制**：成熟网站会通过反向 DNS 验证（PTR 记录）确认是否为真正的
>    搜索引擎 IP，伪造 UA 但 IP 不匹配会被识别并封禁
> 3. **道德风险**：冒充第三方身份进行数据采集属于欺骗行为
>
> **建议**：
> - 仅在明确合法授权的场景下使用此功能
> - 优先尊重源站 `robots.txt` 协议
> - 生产环境建议使用真实 UA + 合理频率控制 + 代理池，而非伪装爬虫
> - 本功能默认关闭，需用户在配置中显式开启并知悉风险

---

## 九、浏览器与7坛后台会话 ⭐

### 9.1 为什么必须有浏览器

```
7坛AI小编的核心工作流程中，有两个环节必须使用真实浏览器:

  ┌─────────────────────────────────────────────────────────────┐
  │                                                             │
  │  ① 爬取源站资源                                              │
  │     Playwright 打开源站网页 → AI 阅读页面内容 → 提取信息     │
  │     → 下载资源（蜘蛛优先/浏览器兜底，详见 §8.3）              │
  │                                                             │
  │  ② 登录7坛管理后台并发布 ⭐                                   │
  │     Playwright 打开 img.7tan.cn (login.php)                │
  │     → 自动登录（用户名+密码）                                 │
  │     → 填写发布表单（标题/简介/分类/标签/下载链接）             │
  │     → 上传 LOGO 和截图（通过浏览器文件选择器）                │
  │     → 点击"发布"按钮                                         │
  │     → 验证发布结果                                           │
  │                                                             │
  └─────────────────────────────────────────────────────────────┘

  ⚠️ 这两个环节都必须通过真实浏览器完成，无法用 HTTP API 替代:
     - 7坛后台是标准 Web 表单，不是 REST API
     - 文件上传需要通过浏览器文件选择器
     - 可能有 CSRF Token、验证码等安全机制
```

### 9.2 7坛后台登录会话管理

```
软件启动时自动登录7坛后台，并全程保持登录状态:

┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  启动阶段                                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 1. 检查 data/sessions/7tan_cookies.json 是否存在          │  │
│  │    ├── 存在 → 加载 Cookie → 访问后台首页验证是否仍登录     │  │
│  │    │         ├── 有效 → ✅ 直接进入就绪状态               │  │
│  │    │         └── 过期 → 执行自动登录                      │  │
│  │    └── 不存在 → 执行自动登录                              │  │
│  │                                                          │  │
│  │ 2. 自动登录流程:                                          │  │
│  │    browser.goto(config.site_7tan.login_url)              │  │
│  │    # login_url = "https://img.7tan.cn/login.php"         │  │
│  │    page.fill('input[name="username"]', config.用户名)      │  │
│  │    page.fill('input[name="password"]', config.密码)       │  │
│  │    page.click('button[type="submit"]')                   │  │
│  │    page.wait_for_load_state("networkidle")  ← 登录成功    │  │
│  │    page.context.storage_state(path="cookies.json")       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  运行阶段                                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 每次发布前: page.goto(后台首页) → 检查是否被踢出           │  │
│  │   ├── 正常 → 继续发布                                     │  │
│  │   └── 被踢出 → 自动重新登录 → 继续发布                    │  │
│  │                                                          │  │
│  │ 每次发布后: 保存最新 Cookie → data/sessions/7tan_cookies  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 9.3 Cookie 持久化

```python
# 使用 Playwright 原生 storage_state 机制
# 保存完整的浏览器状态（Cookie + localStorage + sessionStorage）

from playwright.sync_api import sync_playwright

class SessionManager:
    """管理7坛后台的登录会话"""
    
    COOKIE_FILE = "data/sessions/7tan_cookies.json"
    
    def __init__(self, browser_context):
        self.context = browser_context
    
    def save_session(self):
        """保存当前浏览器会话到文件"""
        self.context.storage_state(path=self.COOKIE_FILE)
    
    def load_session(self) -> bool:
        """加载已保存的会话，返回是否有效"""
        import os, json
        if not os.path.exists(self.COOKIE_FILE):
            return False

        # 检查 Cookie 是否过期
        with open(self.COOKIE_FILE) as f:
            data = json.load(f)

        cookies = data.get("cookies", [])
        for c in cookies:
            if c.get("name") == "session_expiry":
                import time
                if c.get("value", 0) < time.time():
                    return False  # 已过期

        # ⚠️ 正确做法：创建新 context 时加载 storage_state，而非调用 storage_state(path=...)
        # storage_state(path=...) 是保存操作，不是加载！
        # 加载应在创建 context 时完成：
        #   context = browser.new_context(storage_state=self.COOKIE_FILE)
        # 此处仅返回 True 表示文件有效，实际加载在 context 创建时完成
        return True
    
    def is_logged_in(self, page) -> bool:
        """检查7坛后台是否仍处于登录状态"""
        page.goto("https://img.7tan.cn/admin")
        page.wait_for_load_state("networkidle")
        # 如果被重定向到登录页，说明登录过期
        return "login" not in page.url

    def login(self, page, username, password):
        """执行登录"""
        page.goto("https://img.7tan.cn/login.php")
        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")

        if "login" in page.url:
            raise Exception("❌ 7坛后台登录失败，请检查用户名和密码")
        
        self.save_session()
        return True
```

### 9.4 浏览器实例隔离

```
软件运行期间有两个浏览器场景，需要隔离:

┌────────────────────────────────────────────────────────────┐
│                                                            │
│  BrowserContext A - 7坛后台会话（长期保持）                   │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ 持久化 Cookie                                        │ │
│  │ 启动时登录一次，随后保持登录态                          │ │
│  │ 用于: 发布资源、修改已发布内容、检查发布结果             │ │
│  │ Cookie 文件: data/sessions/7tan_cookies.json          │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  BrowserContext B - 源站爬取（按需创建/销毁）                │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ 每次爬取新建 Context（隔离 Cookie，避免被追踪）         │ │
│  │ 爬取完毕后销毁 Context                                 │ │
│  │ 用于: 浏览源站、提取信息、触发下载                      │ │
│  │ 可配置代理（通过 config.yaml 的 network 段）             │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 9.5 会话健康检查

```python
class SessionHealthChecker:
    """定期检查7坛后台登录状态"""
    
    def __init__(self, session_manager, interval_minutes=30):
        self.session_manager = session_manager
        self.interval = interval_minutes
    
    def check(self, page):
        """检查登录状态，过期自动重登"""
        if not self.session_manager.is_logged_in(page):
            logger.warning("⚠️ 7坛后台登录已过期，正在重新登录...")
            self.session_manager.login(
                page,
                config["site_7tan"]["username"],
                config["site_7tan"]["password"],
            )
            logger.info("✅ 7坛后台重新登录成功")
```

### 9.6 无头模式下的特殊处理

```
服务器模式（--headless）下，浏览器在后台运行，但7坛后台可能检测到无头浏览器。

应对策略:
  1. 发布时临时切换到有头模式（虚拟显示）
     Linux: 配合 Xvfb 虚拟显示
     Windows: 无头模式下也能正常操作表单（Playwright 支持）
  
  2. 反检测脚本增强
     page.add_init_script("""
       // 隐藏 webdriver 特征
       Object.defineProperty(navigator, 'webdriver', {get: () => false});
       // 模拟真实的 plugins 和 mimeTypes
       Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
     """)
     
  3. 人工干预兜底
     如果自动登录失败（出现验证码等），通知用户:
     "⚠️ 7坛后台登录需要验证码，请在浏览器中手动登录"
     → 用户通过 Web UI 的"手动登录"功能完成验证码
     → 软件保存 Cookie 后继续自动运行
```

### 9.7 在 Web UI 中的体现

```
设置页面中新增"7坛后台"区域:

┌─ [7坛后台] ────────────────────────────────────────────┐
│  登录状态  🟢 已登录 (会话有效期至 14:30)                │
│                                                         │
│  网址      [https://img.7tan.cn/admin        ]          │
│  用户名    [admin                              ]         │
│  密码      [••••••••]              [👁 显示]             │
│                                                         │
│  [🔄 重新登录]  [🔍 测试登录]  [🧹 清除Cookie]           │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │ 📋 登录日志:                                      │  │
│  │ 14:00  ✅ 自动登录成功                            │  │
│  │ 08:00  ✅ Cookie有效，跳过登录                    │  │
│  │ 昨日   ✅ 自动登录成功                            │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 十、并发控制与任务隔离 ⭐

```
┌──────────────┐
│  任务队列     │
│              │
│  TaskQueue   │
│  ┌────────┐  │      ┌─────────────────┐
│  │ 发布1   │──┼─────→│ Agent 实例 1     │  ← 独立的 messages 上下文
│  │ 发布2   │  │      │ (处理一个资源)    │
│  │ 发布3   │  │      └─────────────────┘
│  │ 对话    │──┼─────→│ Agent 实例 2     │  ← 独立的 messages 上下文
│  └────────┘  │      │ (对话模式)        │
│              │      └─────────────────┘
│  全局锁      │
│  ┌────────┐  │      同一时间只允许一个实例操作浏览器
│  │browser │  │      同一时间只允许一个实例操作数据库（SQLite 单写）
│  │_lock   │  │
│  └────────┘  │
└──────────────┘
```

### 10.1 任务队列（架构说明）

```
用户: "帮我把《XXX》发布了"

方案: 对话 Agent 创建一个子任务，丢到任务队列
  → 对话 Agent 继续和用户聊天（不阻塞）
  → 后台任务 Agent 独立执行发布
  → 发布完成后通知对话 Agent
  → 对话 Agent 告知用户:"《XXX》发布完成了！"

这样对话和发布互不干扰，各自独立的 Agent 实例、独立的上下文。
```

### 10.2 冲突处理

```
冲突场景:
  定时任务正在发布 → 用户进入对话 → 用户说"停下来，先发这个"

处理:
  1. 对话 Agent 向任务队列发送 "暂停" 信号
  2. 当前发布任务完成当前步骤后暂停（不中断正在下载的文件）
  3. 用户指定的任务插入队首
  4. 执行完毕后恢复原任务
```

---

## 十一、上下文窗口管理 ⭐

### 11.1 问题分析

发布一个游戏可能经历 20~30 次 tool call，每次 tool call 都往 messages 追加，很快就超过模型的 token 上限。

### 11.2 解决方案：滚动摘要

```python
class ContextManager:
    """管理 Agent 的上下文窗口"""
    
    def __init__(self, context_window=120000):
        # context_window: 模型上下文窗口大小（如 deepseek-chat 支持 128K）
        # 注意: 这与 API 请求的 max_tokens（输出上限，通常 4096-8192）不同
        self.context_window = context_window
        self.messages = []
        self.summary = ""            # 历史积累摘要
    
    def add_message(self, msg):
        self.messages.append(msg)
        
        # 检查是否超出限制
        if self.estimate_tokens() > self.context_window * 0.7:
            self.compress()
    
    def compress(self):
        """压缩历史消息"""
        # 保留：system prompt + 最近10条消息
        # 中间部分用 AI 总结成一段话替换
        
        old = self.messages[1:-10]   # 去掉 system + 最近10条
        summary_prompt = f"请将以下对话历史概括为一段摘要：\n{old}"
        new_summary = ai.chat(summary_prompt)
        
        self.messages = [
            self.messages[0],        # system prompt
            {"role": "system", "content": f"[历史摘要] {new_summary}"},
            *self.messages[-10:]     # 最近10条
        ]
```

### 11.3 当压缩还不够时

```
如果压缩后仍然超限 → AI 将 tool 返回的大量内容（如网页HTML）
截断为前2000字符 + "...(已截断，完整内容已缓存)"
```

---

## 十二、自改进安全机制 ⭐

### 12.1 问题分析

`write_own_code` 允许 AI 直接改源码，风险极高：
- Prompt injection 攻击
- AI 改出 bug 导致程序崩溃
- 误删关键代码

### 12.2 沙箱机制

```python
def write_own_code(file_path, new_content):
    """安全的代码修改"""
    
    # 1. 权限检查（YAML 配置访问）
    # file_category 映射到 config.yaml security 段的键名
    # 如 "工具代码" → "allow_modify_tools", "核心代码" → "allow_modify_core"
    perm_key = {
        "配置": "allow_modify_config",
        "Prompt": "allow_modify_prompts",
        "工具代码": "allow_modify_tools",
        "核心代码": "allow_modify_core",
    }.get(file_category, "allow_modify_tools")
    allowed = config["security"].get(perm_key, False)
    if not allowed:
        return "❌ 该文件类别不允许修改"
    
    # 2. 备份原文件
    backup_path = f"backup/{timestamp}_{file_path}"
    shutil.copy2(file_path, backup_path)
    
    # 3. 语法检查（Python 文件）
    if file_path.endswith('.py'):
        try:
            compile(new_content, file_path, 'exec')
        except SyntaxError as e:
            return f"❌ 新代码有语法错误，拒绝修改: {e}"
    
    # 4. 展示 diff → 用户确认
    #    ⚠️ 在 Web UI 环境下不能用 input()，需通过 WebSocket 推送确认请求
    diff = compute_diff(file_path, new_content)

    # Web UI 模式：通过 WebSocket 推送 diff，等待前端确认
    if WEB_UI_MODE:
        ws_manager.broadcast({
            "type": "confirm_modify",
            "data": {"file": file_path, "diff": diff, "backup": backup_path}
        })
        confirm = await wait_for_user_confirmation(timeout=60)
    else:
        # CLI 模式：命令行交互
        print(f"改动预览:\n{diff}")
        confirm = input("确认修改？(y/n): ")

    if confirm.lower() != 'y':
        return "❌ 已取消"
    
    # 5. 写入 + 记录
    with open(file_path, 'w') as f:
        f.write(new_content)
    log_modification(file_path, backup_path, diff)
    
    return f"✅ 已修改 {file_path}，备份: {backup_path}"
```

### 12.3 代码修改白名单

> 以下配置对应 config.yaml 中的 `security` 段。

```yaml
security:
  # 分级控制
  allow_modify_config: true        # 直接生效
  allow_modify_prompts: true       # 直接生效
  allow_modify_tools: true         # 需语法检查 + 用户确认
  allow_modify_core: false         # 默认关闭
  allow_create_files: true         # 新增工具时用
  allow_delete_files: false        # 默认禁止

  # 不允许修改的文件列表
  protected_files:
    - src/main.py
    - config.yaml
```

---

## 十三、自重启机制 ⭐

### 13.1 实现方案

```python
import os, sys, subprocess

def restart_self():
    """Python 进程优雅重启"""
    
    # 1. 保存当前状态
    save_state_to_disk()
    
    # 2. 关闭所有资源
    close_browser()
    close_db()
    
    # 3. 启动新进程
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后
        exe = sys.executable
    else:
        # 开发环境
        exe = sys.executable
    
    subprocess.Popen([exe, *sys.argv[1:]])
    
    # 4. 退出当前进程
    os._exit(0)
```

### 13.2 局限性说明

- 如果 AI 改坏了 `main.py`，重启后可能启动失败 → 手动从 backup 恢复
- Windows 服务模式下需要配合 `--daemon` 参数
- 建议核心代码修改后不自动重启，而是提示用户手动重启
- ⚠️ **PyInstaller `--onefile` 模式注意**: 单文件模式下，进程退出时临时解压目录
  会被清理，新进程可能找不到依赖。建议使用 `--onedir` 模式，或在 `subprocess.Popen`
  后延迟退出（`time.sleep(1)` 确保新进程已启动并完成解压）。

---

## 十四、工具注册机制 ⭐

### 14.1 统一注册

```python
# src/tools/registry.py

from dataclasses import dataclass
from typing import Any, Callable

@dataclass
class Tool:
    name: str                    # 函数名
    description: str             # 给 AI 看的描述（prompt用）
    parameters: dict             # JSON Schema 参数定义
    function: Callable           # 实际函数
    category: str                # 分类: browser/file/oss/db/image/content/publish/self_modify/monitor
    dangerous: bool = False      # 是否需要用户确认
    requires_browser: bool = False
    requires_db: bool = False

# 全局注册表
TOOL_REGISTRY: dict[str, Tool] = {}

def register_tool(
    name: str = None,
    description: str = "",
    parameters: dict = None,
    category: str = "misc",
    dangerous: bool = False,
    requires_browser: bool = False,
    requires_db: bool = False,
):
    """工具注册装饰器。

    用法一: 直接装饰函数，通过参数提供元数据
        @register_tool(name="download", description="...", parameters={...})
        def download(url): ...

    用法二: 装饰 Tool 子类
        @register_tool
        class MyTool(Tool): ...
    """
    def decorator(target):
        if isinstance(target, type):
            # 装饰类: 实例化后注册
            instance = target()
            tool = Tool(
                name=instance.name,
                description=instance.description,
                parameters=instance.parameters,
                function=instance.run if hasattr(instance, "run") else instance.__call__,
                category=getattr(instance, "category", category),
                dangerous=getattr(instance, "dangerous", dangerous),
                requires_browser=getattr(instance, "requires_browser", requires_browser),
                requires_db=getattr(instance, "requires_db", requires_db),
            )
        else:
            # 装饰函数
            tool = Tool(
                name=name or target.__name__,
                description=description,
                parameters=parameters or {"type": "object", "properties": {}},
                function=target,
                category=category,
                dangerous=dangerous,
                requires_browser=requires_browser,
                requires_db=requires_db,
            )
        TOOL_REGISTRY[tool.name] = tool
        return target
    return decorator

def get_all_tools() -> list[dict]:
    """返回 OpenAI 兼容的 tools 数组"""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            }
        }
        for t in TOOL_REGISTRY.values()
    ]

def execute_tool(name: str, args: dict) -> str:
    """执行工具并返回结果"""
    tool = TOOL_REGISTRY[name]
    if tool.dangerous:
        if not confirm_dangerous_action(name, args):
            return "用户取消了操作"
    return tool.function(**args)
```

### 14.2 新增工具的步骤

用户说"能不能加一个XXX功能" → AI 执行：

1. 创建 `src/tools/xxx_tool.py`
2. 定义函数 + 用 `@register_tool` 装饰器注册
3. 重启即可用

```python
# AI 创建的新工具示例
from .registry import register_tool, Tool

@register_tool(
    name="email_notify",
    description="发送邮件通知。当发布完成或出错时调用。",
    parameters={
        "type": "object",
        "properties": {
            "subject": {"type": "string", "description": "邮件主题"},
            "body": {"type": "string", "description": "邮件正文"},
        },
        "required": ["subject", "body"]
    },
    category="monitor",
)
def email_notify(subject: str, body: str) -> str:
    """发送邮件通知"""
    # ... 实际发送逻辑 ...
    return f"✅ 邮件已发送: {subject}"

# 也可以用类形式:
# @register_tool
# class EmailNotifyTool(Tool):
#     name = "email_notify"
#     description = "..."
#     parameters = {...}
#     category = "monitor"
#     def run(self, subject, body): ...
```

---

## 十五、Token 成本追踪 ⭐

### 15.1 每次 API 调用都记录用量

```python
class CostTracker:
    """记录每次 API 调用的 token 和费用"""
    
    # 各模型价格（每百万 token，人民币，参考各厂商公开定价）
    PRICES = {
        "deepseek-chat":       {"prompt": 1.0,  "completion": 4.0},
        "deepseek-reasoner":   {"prompt": 4.0,  "completion": 16.0},
        "gpt-4o":              {"prompt": 18.0, "completion": 72.0},
        "qwen2.5-7b":          {"prompt": 0.5,  "completion": 2.0},
    }
    
    def record_usage(self, model, prompt_tokens, completion_tokens):
        price = self.PRICES.get(model, {"prompt": 1.0, "completion": 4.0})
        cost = (prompt_tokens / 1_000_000 * price["prompt"] +
                completion_tokens / 1_000_000 * price["completion"])
        # 存入数据库
```

### 15.2 用户可查看

```
你: 今天花了多少钱？

AI: 今天 API 调用统计:
    - 总 Token: 125,430 (输入: 98,200, 输出: 27,230)
    - 模型: deepseek-chat
    - 预估费用: ¥0.21
    
    本月累计: ¥3.47
```

---

## 十六、磁盘与资源检查 ⭐

### 16.1 下载前检查

```python
def check_before_download(url_info, download_dir):
    """下载前检查"""
    file_size = url_info.get("size_bytes", 0)
    
    # 1. 磁盘空间检查（需要 2 倍文件大小，下载+解压）
    free_space = shutil.disk_usage(download_dir).free
    if free_space < file_size * 2:
        return f"❌ 磁盘空间不足: 需要 {file_size*2/1024**3:.1f}GB, 可用 {free_space/1024**3:.1f}GB"
    
    # 2. 文件大小警告
    if file_size > 50 * 1024**3:  # >50GB
        return f"⚠ 文件超过50GB ({file_size/1024**3:.1f}GB)，确认下载？"
    
    return "✅ OK"
```

### 16.2 AI 自主判断

AI 调用 `download_file` 前，先调 `check_disk()` 获取可用空间。如果空间不足，AI 会通知用户并跳过该资源。

---

## 十七、首次启动引导 ⭐

### 17.1 无配置时启动

```
============================================
  🤖 7坛AI小编 - 首次启动引导
============================================

检测到配置文件不存在，请完成以下设置:

[1/5] 选择 AI 模型:
   1. DeepSeek (推荐)
   2. OpenAI
   3. 本地 Ollama
   4. 自定义 API
   请选择 (1-4): 

[2/5] 请填写 API Key: 

[3/5] 请填写 7坛 管理后台信息:
   网址 [https://img.7tan.cn]: 
   用户名: 
   密码: 

[4/5] 云存储配置 (必填！未配置则无法发布安装包): ⭐
   类型:
     1. 阿里云 OSS
     2. 腾讯云 COS
     3. 七牛 Kodo
     4. 跳过（无法发布安装包，只能发布Logo+简介）
   请选择 (1-4): 1
   
   AccessKey ID: xxxxx
   AccessKey Secret: xxxxx
   Bucket名称: my-game-files
   地域: oss-cn-shanghai
   自定义域名 [可选]: https://games.7tan.cn   ; 留空使用OSS默认域名

[5/5] 添加源站 (一行一个网址，留空结束):
   源站1: https://example-game.com
   源站2: 
   
============================================
✅ 配置完成！已保存到 config.yaml
============================================
```

### 17.2 完整配置模板 (config.yaml)

> **注意**: 配置文件统一使用 YAML 格式（与实际项目一致），不再使用 INI 格式。
> 敏感信息（API密钥、密码等）通过 `.env` 环境变量注入，用 `${VAR}` 引用。

```yaml
# ============================================
# 7坛AI小编 配置文件
# 首次启动时由引导程序创建，也可手动编辑
# ============================================

# AI 模型配置
ai:
  provider: "deepseek"              # deepseek / openai / ollama / siliconflow / doubao / custom
  model: "deepseek-chat"            # deepseek-chat / deepseek-reasoner / gpt-4o / qwen2.5-7b / ...
  base_url: "https://api.deepseek.com/v1"
  api_key: "${DEEPSEEK_API_KEY}"    # 从 .env 读取，⚠️ 请勿硬编码
  context_window: 128000            # 模型上下文窗口大小（与 max_tokens 不同）
  max_tokens: 4096                  # 单次 API 响应最大输出 token 数
  temperature: 0.7

# 7坛后台配置
site_7tan:
  base_url: "https://img.7tan.cn"
  login_url: "https://img.7tan.cn/login.php"
  username: "${TANTAN_USERNAME}"    # 从 .env 读取
  password: "${TANTAN_PASSWORD}"    # 从 .env 读取
  publish_delay_min: 30             # 发布间隔(秒)，防机器人检测
  publish_delay_max: 120

# 云存储配置 ⭐
# 必填！安装包将自动上传到这里，再通过外链发布到7坛
# 未配置则无法发布安装包（LOGO/截图/简介仍可正常发布）
oss:
  provider: "aliyun"                # aliyun / tencent / qiniu / none
  access_key: "${OSS_ACCESS_KEY}"
  secret_key: "${OSS_SECRET_KEY}"
  bucket: "${OSS_BUCKET}"
  region: "oss-cn-shanghai"         # aliyun: oss-cn-shanghai / tencent: ap-guangzhou / qiniu: z0
  domain: "${OSS_DOMAIN}"           # 自定义域名，留空使用OSS默认域名

# 本地存储管理 ⭐
storage:
  delete_after_upload: true         # 上传OSS成功后自动删除本地安装包
  image_retention_days: 30          # 发布成功后本地LOGO和截图保留天数
  disk_cleanup_threshold_gb: 10     # 磁盘剩余低于此值(GB)时自动清理

# 源站配置
sources:
  sites:                            # 源站列表，也可通过数据库 source_sites 表管理
    # - name: "示例站"
    #   url: "https://example.com/games"
    #   enabled: true
  crawl_interval: 360               # 每个源站爬取间隔(分钟)
  max_resources_per_run: 5          # 单次运行最多发布多少个资源（游戏+软件）

# Web 界面配置 ⭐
web:
  port: 9800
  auto_open_browser: true
  theme: "dark"
  language: "zh-CN"

# 调度配置
scheduler:
  cron_jobs:                        # 定时执行时间
    - name: "每日早间更新"
      cron: "0 8 * * *"
    - name: "每日午间更新"
      cron: "0 12 * * *"
    - name: "每日晚间更新"
      cron: "0 18 * * *"
  auto_publish: false               # 默认不自动发布（先预览再手动开启）
  daemon: false                     # 守护进程模式

# 网络配置
network:
  http_proxy: ""                    # 如 127.0.0.1:7890
  https_proxy: ""
  connect_timeout: 30
  download_timeout: 7200
  browser_type: "chromium"          # chromium / firefox / webkit
  browser_path: ""                  # 自定义浏览器路径，留空用默认
  headless: false                   # 桌面默认false(更像真人)，服务器模式true
  # ⚠️ 蜘蛛下载模式有法律风险，详见 §8.3 风险提示，默认关闭
  spider_download: false            # true=伪装搜索引擎爬虫下载 / false=Playwright浏览器下载
  spider_list: "all"                # all=全部 / 逗号分隔: googlebot,bingbot,baiduspider

# 安全配置
security:
  self_modify_confirm: true         # AI改代码前必须经过用户确认
  allow_modify_tools: true          # 允许AI修改工具类代码
  allow_modify_core: false          # 核心逻辑默认不允许AI修改
  sensitive_words_filter: true      # 敏感词过滤

# 防篡改配置 🔐
integrity:
  enabled: true                     # true=每次启动校验 / false=关闭
  mode: "core"                      # core=仅核心代码 / full=含全部静态资源
  auto_repair: false                # true=尝试从backup恢复被篡改文件(实验性)
  developer_mode: false             # true=跳过校验(调试用,发布必须false)
  confirm_phrase: "我已知晓风险并信任此次修改"
  show_status: true                 # 仪表盘显示完整性状态指示灯
  log_all_checks: true              # 记录所有校验结果
  tamper_alert_email: ""            # 检测到篡改时发送邮件(可选)

# 日志配置
logging:
  level: "INFO"
  retention: "30 days"
  rotation: "100 MB"
```

---

## 十八、网络与代理配置 ⭐

```yaml
# 以下配置对应 config.yaml 的 network 段（详见 §17.2）
network:
  # 代理（访问源站用，AI API 直连不走代理）
  http_proxy: ""               # 如 127.0.0.1:7890
  https_proxy: ""              # 如 127.0.0.1:7890

  # 超时设置
  connect_timeout: 30          # 秒
  download_timeout: 7200       # 秒（大文件）

  # 浏览器
  browser_type: "chromium"     # chromium / firefox / webkit
  browser_path: ""             # 留空=自动查找/使用内置Chromium
  headless: false              # false=可见浏览器窗口（调试用）
                                # true=无头模式（服务器用）⭐
```

### 18.1 服务器运行

```bash
# Windows Server 无桌面环境
7tan-updater.exe --daemon --headless

# Linux Server
./7tan-updater --daemon --headless
```

`--headless` 模式下 Playwright 使用无头 Chromium，不需要图形界面。配合 `--daemon` 作为后台服务持续运行。

---

## 十九、调度模块 ⭐

### 19.1 项目结构补充

```
src/scheduler/
├── __init__.py
├── scheduler.py        ← APScheduler 调度器
├── jobs.py             ← 任务定义
└── daemon.py           ← Windows Service / Linux daemon
```

### 19.2 调度配置

```yaml
# 以下配置对应 config.yaml 的 scheduler 段（详见 §17.2）
scheduler:
  # 定时执行，多个时间用逗号分隔
  cron_jobs:
    - name: "每日早间更新"
      cron: "0 8 * * *"
    - name: "每日午间更新"
      cron: "0 12 * * *"
    - name: "每日晚间更新"
      cron: "0 18 * * *"

  max_resources_per_run: 5     # 每次最多发布资源数（游戏+软件）
  auto_publish: false

  # 服务器模式
  daemon: false                # true=后台持续运行
```

---

## 二十、优化后的发布流程 ⭐

### 20.1 完整发布流程（含浏览器登录）

```
一个资源从发现到发布的完整链路:

┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  🟢 启动时（一次性）                                                  │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ ⓪ 打开浏览器 → 登录 7坛管理后台 → 保存 Cookie → 保持登录态     │   │
│  │    https://img.7tan.cn/admin                                  │   │
│  │    后续所有发布复用此登录会话                                    │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  🔄 每个资源的发布流程:                                               │
│                                                                      │
│  ① 浏览源站（Playwright 打开源站详情页）                              │
│     ↓   AI 理解页面内容，提取游戏/软件信息                            │
│  ② 提取信息（标题/版本/大小/分类/简介/截图/下载链接）                  │
│     ↓                                                                │
│  ③ 去重检查（查数据库是否已存在、是否版本更新）                        │
│     ↓                                                                │
│  ┌─────────────┬─────────────┐                                       │
│  ▼             ▼             ▼                                       │
│  ④ 下载安装包  ⑤ AI 改写简介  ⑥ 下载 LOGO 和截图                     │
│  (异步后台)    (同步，很快)   (同步)                                   │
│  │             │             │                                       │
│  │             │             │                                       │
│  └──────┬──────┘      ┌──────┘                                       │
│         ▼             ▼                                               │
│  ⑦ 上传到 OSS       ⑧ 审核内容（敏感词检查、格式规范）                │
│  │                   │                                               │
│  ▼                   ▼                                               │
│  ⑨ 在7坛后台发布（通过已登录的浏览器会话）                             │
│     → 填写标题、简介、分类、标签                                      │
│     → 上传 LOGO（浏览器文件选择器）                                    │
│     → 上传截图（浏览器文件选择器）                                     │
│     → 填入 OSS 外链为下载地址                                         │
│     → 点击"发布"按钮                                                  │
│     → 验证发布成功                                                    │
│     ↓                                                                │
│  ⑩ 记录发布结果 → 更新数据库 → 进入下一个资源                         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

⚠️ 步骤 ⑨ 是整个流程的关键：必须通过浏览器操作 7坛后台的表单，
   无法用 HTTP API 替代。
```

### 20.2 v4→v5 流程重构：并行优化

```
旧流程（串行）:
  ①浏览 → ②提取 → ③去重 → ④下载 → ⑤改写 → ⑥上传 → ⑦发布

新流程（并行 + 浏览器复用）:
  ┌─ 启动时 ────────────────────────────────┐
  │ ⓪ 登录7坛后台（会话全局复用）             │
  └─────────────────────────────────────────┘
                    │
  ①浏览 → ②提取 → ③去重
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
       ④下载(异步) ⑤改写(同步) ⑥图片下载
          │         │         │
          │    (改写很快完成)  │
          │         │         │
          └────┬────┘    ┌────┘
               ▼         ▼
          ⑦上传OSS   ⑧审核
               │         │
               └────┬────┘
                    ▼
          ⑨ 浏览器发布到7坛（复用已登录会话）
```

### 20.3 资源文件生命周期（核心流程）⭐

```
软件从源站下载游戏/软件安装包后的完整处理链:

┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  ① 从源站下载安装包                                               │
│     ↓                                                            │
│     downloads/packages/{slug}/game_v3.2.1.zip                   │
│     （临时存放在本地）                                             │
│     ↓                                                            │
│  ② AI 自动上传到用户配置的云存储                                    │
│     ↓  AI 调用 oss_upload(local_path)                            │
│     ↓                                                            │
│     OSS 路径: /games/{slug}/game_v3.2.1.zip                     │
│     返回外链: https://games.7tan.cn/games/xxx/game_v3.2.1.zip   │
│     ↓                                                            │
│  ③ 上传成功后，自动删除本地安装包 ⭐                                 │
│     （释放磁盘空间，只保留云存储上的副本）                            │
│     ↓                                                            │
│  ④ 7坛发布时，下载链接填 OSS 外链                                  │
│     （用户在7坛点击下载 → 从云存储下载，不经过本软件服务器）            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**关于 LOGO 和截图**（与安装包不同）:
```
LOGO 和截图: 下载到本地 → 保留（7坛发布时需通过浏览器上传到7坛服务器）
安装包:      下载到本地 → 上传OSS → 删除本地 → 7坛使用OSS外链
```

**OSS 文件命名规则**:
```
/{资源类型}/{slug}/{文件名}

示例:
  /games/saiberpengke2077/saiberpengke2077_v3.2.1.zip
  /software/ps_2025/photoshop_2025_v25.1.0.zip

文件名为 slug 化处理，确保 URL 安全，不含中文和特殊字符。
```

**OSS 上传技术细节**:
```
- 大文件（>100MB）使用分片上传，每片 10MB
- 支持断点续传（OSS 侧记录分片状态）
- 上传完成后校验 MD5（与本地文件对比）
- 上传失败自动重试 3 次
```

### 20.4 未配置云存储时的处理 ⭐

```
如果用户没有配置云存储（config.yaml 的 oss 段为空或跳过）:

  ❌ 安装包/软件包 → 无法发布，跳过该资源
     日志记录: "未配置云存储，跳过安装包上传"

  ✅ LOGO/截图   → 正常处理，直接用于7坛发布
  ✅ 游戏简介     → 正常改写

  启动时如果检测到未配置云存储，会输出警告:
  ⚠️  未配置云存储！游戏/软件安装包将无法上传，发布时无下载链接。
      请编辑 config.yaml 添加 oss 段配置，或进入对话模式输入"配置云存储"。
```

### 20.5 本地文件保留策略

```
默认策略（推荐）:
  安装包  → 上传OSS成功后 → 立即删除本地文件
  LOGO    → 发布成功后     → 保留 30 天（用于可能的重新发布）
  截图    → 发布成功后     → 保留 30 天

可配置（config.yaml 的 storage 段）:
  storage:
    delete_after_upload: true       # true=上传后自动删除 / false=保留本地副本
    image_retention_days: 30        # 发布后保留多少天
    disk_cleanup_threshold_gb: 10   # 磁盘剩余低于10GB时自动清理过期文件
```

---

## 二十一、Web UI 管理面板 ⭐

### 21.1 设计定位

```
7坛AI小编不是命令行工具，而是一款"高端桌面软件"。

启动方式:  双击 exe → 自动打开浏览器 → 精美的 Web 管理面板
技术方案:  FastAPI(后端) + Vue 3(前端) + Tailwind CSS + WebSocket(实时推送)
设计风格:  深色主题 + 毛玻璃 + 渐变光效 + 微动效

无需 npm / nodejs 环境，所有前端资源内嵌在 exe 中，保持绿色免安装。

> **关于组件拆分**: Vue 3 CDN 版本通过动态加载 `.js` 组件文件实现模块化，
> 不需要 webpack/vite 构建工具。使用 `Vue.defineComponent()` + 原生 ES Module
> 或简单的 `<script>` 标签按需加载即可。CSS 不使用 CSS Modules 的 `composes`
> 语法（CDN 模式不支持），改用 Tailwind 工具类 + 自定义 CSS 变量组合。
```

### 21.2 技术选型

| 层面 | 技术 | 理由 |
|------|------|------|
| 后端 Web 框架 | FastAPI | 性能好、自带 WebSocket、异步原生支持 |
| 前端框架 | Vue 3 (CDN) | 无需构建工具，单文件 HTML 即用 |
| CSS 样式 | 自定义 CSS（毛玻璃+渐变） | 深色主题 + CSS 变量 + glassmorphism |
| 图表 | Chart.js 4.4 (CDN) | 轻量、好看、支持动画 |
| 图标 | Font Awesome 6 (CDN) | 经典图标库，CDN 即用 |
| 实时通信 | WebSocket | 任务进度、日志实时推送 |
| 字体 | Inter + JetBrains Mono | 现代无衬线 + 等宽代码字体 |

> ⚠️ **与早期设计差异**: 架构文档原计划使用 Tailwind CSS + Lucide Icons，
> 实际实现改用 **自定义 CSS + Font Awesome 6**，视觉效果一致（深色毛玻璃 + 渐变光效），
> 且避免了 Tailwind CDN 构建工具依赖。

> 全部 CDN 资源在首次联网后缓存到 `data/web_cache/`，断网也能用。

### 21.3 设计系统

#### 色彩方案

```css
:root {
  /* 主色调 — 紫色到蓝色渐变 */
  --accent-primary:   #7C3AED;    /* 紫罗兰 */
  --accent-secondary: #3B82F6;    /* 宝石蓝 */
  --accent-gradient:  linear-gradient(135deg, #7C3AED, #3B82F6);

  /* 功能色 */
  --color-success:    #10B981;    /* 翡翠绿 */
  --color-warning:    #F59E0B;    /* 琥珀黄 */
  --color-error:      #EF4444;    /* 珊瑚红 */
  --color-info:       #6366F1;    /* 靛蓝 */

  /* 深色主题背景 */
  --bg-primary:       #0F0F1A;    /* 最深背景 */
  --bg-secondary:     #1A1A2E;    /* 卡片/面板 */
  --bg-tertiary:      #25253A;    /* 悬停/选中 */
  --bg-glass:         rgba(26, 26, 46, 0.8);  /* 毛玻璃 */

  /* 文字 */
  --text-primary:     #F1F5F9;    /* 主文字 */
  --text-secondary:   #94A3B8;    /* 辅助文字 */
  --text-muted:       #64748B;    /* 暗淡文字 */

  /* 边框与阴影 */
  --border-subtle:    rgba(255, 255, 255, 0.06);
  --border-glow:      rgba(124, 58, 237, 0.3);
  --shadow-lg:        0 25px 50px -12px rgba(0, 0, 0, 0.5);
  --shadow-glow:      0 0 40px rgba(124, 58, 237, 0.15);

  /* 圆角 */
  --radius-sm:        8px;
  --radius-md:        12px;
  --radius-lg:        16px;
  --radius-xl:        24px;
}
```

#### 毛玻璃效果 (Glassmorphism)

```css
.glass {
  background: var(--bg-glass);
  backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
}

.glass-card {
  /* 注意: CDN Tailwind 不支持 CSS Modules 的 composes 语法 */
  /* 直接复用 .glass 的属性，或使用 Tailwind @apply（需构建工具） */
  background: var(--bg-glass);
  backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.glass-card:hover {
  border-color: var(--border-glow);
  box-shadow: var(--shadow-glow);
  transform: translateY(-2px);
}
```

#### 动画系统

```css
/* 页面进入 */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* 脉冲光晕 */
@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 20px rgba(124, 58, 237, 0.1); }
  50%      { box-shadow: 0 0 40px rgba(124, 58, 237, 0.3); }
}

/* 渐变流动 */
@keyframes gradient-shift {
  0%   { background-position: 0% 50%; }
  50%  { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

/* 状态指示灯 */
@keyframes status-blink {
  0%, 100% { opacity: 1; }
  50%      { opacity: 0.3; }
}
```

### 21.4 整体布局

```
┌──────────────────────────────────────────────────────────────┐
│  ┌──────────┐                                               │
│  │          │  ┌─────────────────────────────────────────┐  │
│  │  侧边栏  │  │                                         │  │
│  │          │  │                                         │  │
│  │  📊 仪表盘│  │          主内容区域                       │  │
│  │  💬 AI对话│  │                                         │  │
│  │  📦 资源 │  │     (根据左侧导航切换)                    │  │
│  │  📋 任务 │  │                                         │  │
│  │  🌐 源站 │  │                                         │  │
│  │  📈 统计 │  │                                         │  │
│  │  ⚙️ 设置 │  │                                         │  │
│  │          │  │                                         │  │
│  │          │  └─────────────────────────────────────────┘  │
│  └──────────┘                                               │
└──────────────────────────────────────────────────────────────┘
  ← 240px →   ←              剩余宽度                          →
```

**侧边栏细节**:
- 宽度 240px，深色背景 `--bg-secondary`
- 顶部 Logo 区域（渐变文字 "7坛AI小编" + 发光图标）
- 导航项带图标 + 文字，选中项左侧有渐变指示条
- 底部显示：运行状态指示灯、AI 模型名称、版本号

### 21.5 七大页面设计

#### 📊 仪表盘 (Dashboard)

```
┌──────────────────────────────────────────────────────────────┐
│  👋 下午好，Admin                    2026-07-13  14:30:28    │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │ 📦 已发布 │ │ 🔄 处理中 │ │ 💰 今日费用│ │ ⚡ 运行状态   │  │
│  │   1,247  │ │     3    │ │  ¥0.47   │ │  🟢 正常运行  │  │
│  │ ↑12 本月 │ │ 查看详情 │ │ ↓3% vs昨日│ │ 运行 8h 32m  │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │
│                                                              │
│  ┌─────────────────────────┐ ┌──────────────────────────┐  │
│  │ 📈 近7天发布趋势 (折线图) │ │ 📊 资源类型分布 (环形图)  │  │
│  │                         │ │                          │  │
│  │    ·  /`\               │ │    🎮 游戏   68%  ●      │  │
│  │      /    \             │ │    💻 软件   32%  ●      │  │
│  │  ··/       \··   ·      │ │                          │  │
│  │  一 二 三 四 五 六 日     │ │                          │  │
│  └─────────────────────────┘ └──────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 📋 最近活动日志 (实时滚动)                            │  │
│  │                                                      │  │
│  │ 14:28:32  ✅ 《赛博朋克2077》发布成功                  │  │
│  │ 14:15:10  ✅ 《Photoshop 2025》上传OSS完成             │  │
│  │ 14:10:03  🔄 《荒野大镖客2》正在下载... 67%            │  │
│  │ 13:58:41  ✅ 《黑神话悟空》改写完成                    │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

**四张统计卡片**设计要点:
- 毛玻璃背景 + 微光边框
- 数字大而醒目（32px 粗体）
- 每个卡片左下角有小字趋势对比（绿色↑/红色↓）
- 悬停时放大 1.02x + 光晕增强

#### 💬 AI 对话 (Chat)

```
┌──────────────────────────────────────────────────────────────┐
│  💬 AI 对话                                    + 新对话      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                                                      │   │
│  │  ┌─────────────────────────────────────────────┐     │   │
│  │  │ 🤖 你好！我是7坛AI小编。                      │     │   │
│  │  │ 我可以帮你：                                  │     │   │
│  │  │ • 自动采集发布游戏和软件                       │     │   │
│  │  │ • 查看任务进度和资源状态                       │     │   │
│  │  │ • 修改软件配置和源站设置                       │     │   │
│  │  │ 有什么需要帮忙的？                             │     │   │
│  │  └─────────────────────────────────────────────┘     │   │
│  │                                            14:30    │   │
│  │                                                      │   │
│  │        ┌──────────────────────────────────────┐     │   │
│  │        │ 帮我采集 https://xxx.com 的游戏        │     │   │
│  │        └──────────────────────────────────────┘     │   │
│  │                                        👤 我 14:31  │   │
│  │                                                      │   │
│  │  ┌─────────────────────────────────────────────┐     │   │
│  │  │ 🔄 正在浏览源站...                            │     │   │
│  │  │ 找到 12 个游戏资源，其中 3 个是新的             │     │   │
│  │  │ [查看详情] [立即发布] [稍后处理]                │     │   │
│  │  └─────────────────────────────────────────────┘     │   │
│  │                                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 📎 上传文件  │  输入消息...                  📤 发送 │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

**对话页设计要点**:
- AI 消息左侧有渐变头像 + 打字机效果（逐字显示）
- 用户消息右侧对齐，毛玻璃气泡
- 工具调用结果以折叠卡片形式展示（可展开看详情）
- 输入框支持多行，Ctrl+Enter 发送
- 对话历史自动保存，左侧可切换历史会话

#### 📦 资源管理 (Resources)

```
┌──────────────────────────────────────────────────────────────┐
│  📦 资源管理                     🔍 搜索...  [筛选▼] [刷新]  │
│                                                              │
│  ┌───┬──────────┬──────┬────────┬──────┬────────┬────────┐ │
│  │   │ 名称      │ 类型  │ 版本    │ 大小  │ 状态    │ 操作   │ │
│  ├───┼──────────┼──────┼────────┼──────┼────────┼────────┤ │
│  │🖼│ 赛博朋克   │ 🎮   │ v3.2.1 │45GB  │✅ 已发布│ ···   │ │
│  │  │ 2077      │ 角色 │        │      │ 07-12  │ 查看   │ │
│  │  │           │      │        │      │        │ 重新发布│ │
│  ├───┼──────────┼──────┼────────┼──────┼────────┼────────┤ │
│  │🖼│ Photoshop │ 💻   │ v25.1  │3.2GB │🔄 改写中│ ···   │ │
│  │  │ 2025      │ 设计 │        │      │ 45%    │ 详情   │ │
│  ├───┼──────────┼──────┼────────┼──────┼────────┼────────┤ │
│  │🖼│ 荒野大镖客 │ 🎮   │ v1.0   │120GB │⏳ 下载中│ ···   │ │
│  │  │ 2         │ 动作 │        │      │ 67%    │ 暂停   │ │
│  ├───┼──────────┼──────┼────────┼──────┼────────┼────────┤ │
│  │🖼│ 艾尔登法环 │ 🎮   │ v1.12  │60GB │❌ 失败 │ ···   │ │
│  │  │           │ 动作 │        │      │ OSS超时│ 重试   │ │
│  └───┴──────────┴──────┴────────┴──────┴────────┴────────┘ │
│                                            ← 1 2 3 ... 25 → │
└──────────────────────────────────────────────────────────────┘
```

**表格设计要点**:
- 缩略图列显示 LOGO（48x48 圆角）
- 状态列用彩色圆点 + 文字（绿=成功/蓝=进行中/黄=等待/红=失败）
- 进行中的资源显示进度条（渐变填充 + 微动画）
- 行悬停高亮 + 右侧滑入操作菜单（查看/重新发布/重试/删除）
- 支持多选批量操作

#### 📋 任务监控 (Task Monitor)

```
┌──────────────────────────────────────────────────────────────┐
│  📋 任务监控                              [自动刷新 ⏸] 清空  │
│                                                              │
│  队列中: 5  │  执行中: 1  │  已完成: 1,247  │  失败: 12     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 🔄 当前任务：《赛博朋克2077》                         │   │
│  │ ┌────────────────────────────────────────────────┐   │   │
│  │ │ ████████████████████░░░░░░░░░░░░░░ 67%         │   │   │
│  │ └────────────────────────────────────────────────┘   │   │
│  │ ✅ 浏览源站        完成  14:28:01                    │   │
│  │ ✅ 提取信息        完成  14:28:15                    │   │
│  │ ✅ 去重检查        完成  14:28:16  → 新资源          │   │
│  │ 🔄 下载安装包      67%   14:28:20  45.2GB/67.5GB     │   │
│  │ ⏳ AI改写简介       等待中                            │   │
│  │ ⏳ 上传OSS          等待中                            │   │
│  │ ⏳ 发布到7坛        等待中                            │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ ⏳ 等待队列                                          │   │
│  │ 1. 《Photoshop 2025》— 等待当前任务完成               │   │
│  │ 2. 《黑神话悟空》    — 等待中                         │   │
│  │ 3. 《艾尔登法环》    — 等待中                         │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

**任务监控设计要点**:
- 顶部进度条渐变色（紫→蓝），带光泽流动动画
- 步骤列表左侧用时间线连接（竖线 + 圆点）
- 完成步骤打绿色勾，进行中蓝色旋转图标，等待中灰色
- 队列列表可拖拽排序调整优先级
- 实时 WebSocket 推送进度更新（无需刷新页面）

#### 🌐 源站管理 (Sources)

```
┌──────────────────────────────────────────────────────────────┐
│  🌐 源站管理                                [+ 添加源站]      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 🟢 example-game.com                       [编辑] [禁] │   │
│  │    类型: 游戏  │  上次采集: 2小时前  │  资源: 856个     │   │
│  │    间隔: 360分钟  │  状态: 正常                        │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ 🟡 game-source2.net                      [编辑] [禁] │   │
│  │    类型: 游戏  │  上次采集: 6小时前  │  资源: 234个     │   │
│  │    间隔: 360分钟  │  状态: 频率限制中                  │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ 🔴 software-update.com                   [编辑] [禁] │   │
│  │    类型: 软件  │  上次采集: 1天前   │  资源: 89个      │   │
│  │    间隔: 720分钟  │  状态: 需要登录（Cookie过期）      │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

#### 📈 数据统计 (Analytics)

```
┌──────────────────────────────────────────────────────────────┐
│  📈 数据统计                      本周  │  本月  │  全部     │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │ 💰 总费用 │ │ 📊 Token │ │ 📦 发布数 │ │ 🎯 成功率     │  │
│  │ ¥12.47  │ │ 2.3M    │ │   1,247  │ │   98.2%      │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 📈 Token用量趋势 (面积图)                             │   │
│  │    ▁▂▃▅▆▇█▇▆▅▄▃▂▁▂▃▄▅▆▇█▇▆▅▄▃▁                   │   │
│  │    ──────────────────────────────                    │   │
│  │    07-01 ... 07-13                                   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────┐ ┌──────────────────────────┐  │
│  │ 🏷️ 费用按模型分布(饼图)  │ │ 📅 发布时段分布(柱状图)   │  │
│  │ deepseek: ¥8.2  68%     │ │ 08时 ████████ 234        │  │
│  │ gpt-4o:   ¥3.8  31%     │ │ 12时 ████████████ 456     │  │
│  │ qwen:     ¥0.4   1%     │ │ 18时 ██████ 189           │  │
│  └─────────────────────────┘ └──────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

#### ⚙️ 系统设置 (Settings)

```
┌──────────────────────────────────────────────────────────────┐
│  ⚙️ 系统设置                                                  │
│                                                              │
│  ┌─ [AI模型] ────────────────────────────────────────────┐  │
│  │  提供商  [DeepSeek ▼]     模型  [deepseek-chat ▼]     │  │
│  │  API地址 [https://api.deepseek.com/v1            ]    │  │
│  │  API密钥 [••••••••••••••••••••]           [👁 显示]   │  │
│  │  温度    [━━━━━●━━━━━━━━━━━] 0.7                      │  │
│  │  [测试连接]                                            │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─ [云存储] ────────────────────────────────────────────┐  │
│  │  类型    [阿里云OSS ▼]                                │  │
│  │  Bucket  [my-game-files                  ]            │  │
│  │  地域    [oss-cn-shanghai                ]            │  │
│  │  域名    [https://games.7tan.cn          ]            │  │
│  │  [测试上传]  [查看文件列表]                              │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─ [存储] ────────────────────────────────────────────┐   │
│  │  [✓] 上传后自动删除本地安装包                            │  │
│  │  LOGO/截图保留天数  [30] 天                            │  │
│  │  磁盘清理阈值      [10] GB                            │  │
│  │  当前可用空间: 234 GB / 512 GB  [████████░░] 45%      │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─ [调度] ────────────────────────────────────────────┐   │
│  │  [✓] 启用定时发布                                      │  │
│  │  执行时间  [08:00] [12:00] [18:00]  [+ 添加]          │  │
│  │  每次最多发布 [5] 个资源                                │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  [保存设置]  [恢复默认]                                      │
└──────────────────────────────────────────────────────────────┘
```

### 21.6 实时通信架构 (WebSocket)

```
┌──────────────┐         WebSocket          ┌──────────────┐
│   Browser    │◄═══════════════════════════►│   FastAPI    │
│   (Vue 3)    │   ws://localhost:9800/ws   │   (Python)   │
└──────────────┘                             └──────┬───────┘
                                                    │
                                           ┌────────┴────────┐
                                           ▼                 ▼
                                     ┌──────────┐    ┌──────────┐
                                     │ Pipeline │    │  Agent   │
                                     │ (进度)    │    │ (对话)   │
                                     └──────────┘    └──────────┘
```

**推送的消息类型**:

```python
# WebSocket 消息协议
{
  "type": "task_progress",       # 任务进度
  "data": {
    "resource_id": 123,
    "title": "赛博朋克2077",
    "step": "downloading",       # browsing/extracting/downloading/rewriting/uploading/publishing
    "progress": 67,              # 0-100
    "message": "下载中 45.2GB/67.5GB",
  }
}

{
  "type": "log",                 # 日志推送
  "data": {
    "level": "info",             # info/warn/error/success
    "message": "《赛博朋克2077》发布成功",
    "timestamp": "2026-07-13 14:28:32"
  }
}

{
  "type": "ai_message",          # AI 对话消息（打字机效果）
  "data": {
    "content": "正在浏览源站...",
    "is_streaming": true
  }
}

{
  "type": "health",              # 系统健康状态
  "data": {
    "cpu": 23.5,
    "memory": 45.2,
    "disk_free_gb": 234,
    "uptime_seconds": 30720,
    "active_tasks": 1
  }
}
```

### 21.7 响应式与兼容性

```
桌面端 (≥1280px):   侧边栏 + 主内容 → 完整布局
平板端 (768-1279px): 可折叠侧边栏 + 主内容
手机端 (<768px):     单栏布局（仅对话和任务监控可用）

浏览器最低要求:
  Chrome 90+ / Edge 90+ / Firefox 88+ / Safari 14+
  （要求: CSS backdrop-filter + WebSocket）
```

### 21.8 UI 相关项目结构补充

```
7tan-auto-updater/
│
├── src/
│   ├── web/                          ← ⭐ Web UI 模块
│   │   ├── __init__.py
│   │   ├── server.py                 ← FastAPI 应用 + WebSocket
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── api_resources.py      ← 资源 CRUD API
│   │   │   ├── api_tasks.py          ← 任务查询/控制 API
│   │   │   ├── api_sources.py        ← 源站管理 API
│   │   │   ├── api_stats.py          ← 统计数据 API
│   │   │   ├── api_settings.py       ← 配置读写 API
│   │   │   └── api_chat.py           ← 对话 API (SSE 流式)
│   │   ├── ws.py                     ← WebSocket 管理器
│   │   ├── templates/
│   │   │   └── index.html            ← 单页应用入口
│   │   └── static/
│   │       ├── css/
│   │       │   └── app.css           ← 自定义样式
│   │       └── js/
│   │           ├── app.js            ← Vue 3 主应用
│   │           ├── router.js         ← 页面路由
│   │           ├── store.js          ← 状态管理
│   │           └── components/       ← Vue 组件
│   │               ├── Sidebar.js
│   │               ├── Dashboard.js
│   │               ├── ChatPanel.js
│   │               ├── ResourceTable.js
│   │               ├── TaskMonitor.js
│   │               ├── SourceManager.js
│   │               ├── Analytics.js
│   │               └── Settings.js
│   │
│   └── main.py                       ← 启动 Web 服务器 + 自动打开浏览器
│
├── data/
│   └── web_cache/                    ← CDN 资源缓存
└── ...
```

### 21.9 启动流程

```
双击 7tan-updater.exe
        │
        ▼
  ┌─────────────────────┐
  │ 1. 加载 config.yaml   │
  └──────┬──────────────┘
         │
    ┌────┴────┐
    │有配置？  │
    └────┬────┘
    有   │   无
    ┌────┘   └────┐
    ▼             ▼
 正常启动    Web 引导页面
            (localhost:9800/setup)
            │
            ▼
  ┌─────────────────────┐
  │ 2. 启动 FastAPI      │
  │    localhost:9800    │
  └──────┬──────────────┘
         │
         ▼
  ┌─────────────────────┐
  │ 3. 初始化数据库      │
  │    初始化调度器      │
  └──────┬──────────────┘
         │
         ▼
  ┌─────────────────────┐
  │ 4. 自动打开浏览器    │
  │    → 仪表盘页面      │
  └─────────────────────┘
```

### 21.10 命令行保留

```
即使有了 Web UI，命令行仍可用于服务器/无桌面环境:

  --web           启动 Web UI 模式（默认）
  --cli           启动命令行对话模式
  --daemon        后台守护进程（配合 --web 或 --cli）
  --headless      无头模式（服务器用，不打开浏览器）
  --port 9800     指定 Web 端口
  --no-browser    启动 Web 服务但不打开浏览器

示例:
  7tan-updater.exe                          # 默认 Web UI
  7tan-updater.exe --cli                    # 命令行对话
  7tan-updater.exe --daemon --headless      # 服务器后台
  7tan-updater.exe --port 8080              # 自定义端口
```

---

## 二十二、完整项目结构

```
7tan-auto-updater/
│
├── start.bat                        ← 双击启动（开发期）
├── start.sh                         ← Linux 启动脚本
├── config.yaml                       ← 用户配置（首次启动引导创建）
├── README.md
├── requirements.txt
├── build.spec                       ← PyInstaller 打包配置
│
├── src/
│   ├── main.py                      ← 主入口：菜单 + 模式选择 + 首次引导
│   ├── cli.py                       ← 命令行参数解析（--daemon, --headless等）
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── agent_loop.py            ← Agent 核心循环
│   │   ├── model_manager.py         ← 多模型管理 + CostTracker
│   │   ├── context_manager.py       ← ⭐ 上下文窗口管理（滚动摘要）
│   │   ├── prompts.py               ← System Prompt 模板
│   │   └── conversation.py          ← 对话模式
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── registry.py              ← ⭐ 工具注册中心
│   │   ├── browser_tools.py         ← 浏览器操作（含反检测）
│   │   ├── download_tools.py        ← ⭐ 下载工具（断点续传+磁盘检查）
│   │   ├── file_tools.py            ← 文件操作
│   │   ├── oss_tools.py             ← 云存储
│   │   ├── db_tools.py              ← 数据库操作（去重+版本比较）
│   │   ├── image_tools.py           ← 图片处理
│   │   ├── content_tools.py         ← 内容提取与改写
│   │   ├── publish_tools.py         ← 7坛发布
│   │   ├── self_modify_tools.py    ← ⭐ 自改进（含沙箱）
│   │   └── monitor_tools.py        ← ⭐ 费用/磁盘/健康检查
│   │
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── pipeline.py              ← ⭐ 发布流水线（支持并行）
│   │   └── task_queue.py            ← ⭐ 任务队列 + 并发控制
│   │
│   ├── scheduler/                   ← ⭐ 调度模块
│   │   ├── __init__.py
│   │   ├── scheduler.py             ← 定时调度
│   │   └── daemon.py                ← 守护进程
│   │
│   ├── web/                          ← ⭐ Web UI 模块
│   │   ├── __init__.py
│   │   ├── server.py                ← FastAPI + WebSocket
│   │   ├── ws.py                    ← WebSocket 管理器
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── api_resources.py     ← 资源 CRUD API
│   │   │   ├── api_tasks.py         ← 任务查询/控制 API
│   │   │   ├── api_sources.py       ← 源站管理 API
│   │   │   ├── api_stats.py         ← 统计数据 API
│   │   │   ├── api_settings.py      ← 配置读写 API
│   │   │   └── api_chat.py          ← 对话 SSE 流式
│   │   └── static/
│   │       ├── index.html           ← 单页应用入口
│   │       ├── css/app.css          ← 自定义样式
│   │       └── js/
│   │           ├── app.js           ← Vue 3 主应用
│   │           ├── router.js        ← 页面路由
│   │           ├── store.js         ← 状态管理
│   │           └── components/
│   │               ├── Sidebar.js
│   │               ├── Dashboard.js
│   │               ├── ChatPanel.js
│   │               ├── ResourceTable.js
│   │               ├── TaskMonitor.js
│   │               ├── SourceManager.js
│   │               ├── Analytics.js
│   │               └── Settings.js
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── loader.py                ← 配置加载 + 首次引导
│   │
│   ├── security/                    ← 🔐 安全模块
│   │   ├── __init__.py
│   │   ├── integrity.py             ← 完整性校验引擎
│   │   └── manifest_template.py     ← 核心文件清单模板
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   └── db.py                    ← SQLite + 表结构
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logger.py                ← 日志
│       ├── retry.py                 ← ⭐ 重试策略
│       ├── crypto.py                ← 密码加密存储
│       └── helpers.py               ← 通用工具
│
├── integrity.json                   ← 🔐 加密的完整性清单
├── backup/                          ← 自改进前自动备份
├── data/
│   └── games.db                     ← SQLite 数据库
├── downloads/
│   ├── images/                      ← 图片下载目录
│   └── packages/                    ← 安装包下载目录
└── logs/                            ← 日志
```

---

## 二十三、System Prompt 设计

```
你是 7坛游戏社区的 AI 小编，负责自动发现、下载、编辑和发布游戏与软件资源。

你的能力:
1. 自主浏览网页，理解网页内容，提取游戏/软件信息
2. 下载资源文件（图片、安装包等），支持断点续传
3. 改写内容，去掉来源水印和广告，写出自然流畅的介绍
4. 上传文件到云存储，获取外链
5. 登录 7坛 管理后台（https://img.7tan.cn），发布资源
6. 与用户对话，回答问题和接受指令

你需要遵循的原则:
- 每次操作前思考：这一步是否必要？是否有更高效的方式？
- 遇到错误时：分析原因 → 重试（如果值得）→ 记录失败 → 继续下一个
- 内容审核：检查敏感词、确保内容质量、不发布违规内容
- 成本意识：减少不必要的 API 调用，合并能合并的操作
- 资源类型：正确区分游戏和软件，使用对应的分类和描述模板
- 版本管理：识别版本号，区分新品发布和版本更新
- 用户沟通：在对话模式下，持续汇报进度；操作前征求确认
```

---

## 二十四、防篡改与完整性校验 🔐

### 24.1 为什么需要防篡改

```
作为绿色免安装 exe，7坛AI小编面临以下安全风险:

  ┌─────────────────────────────────────────────────────────────┐
  │                                                             │
  │  ① 病毒注入     恶意软件修改 exe/核心 py 文件，植入木马后门   │
  │                                                             │
  │  ② 许可证绕过   篡改配置或代码跳过激活/授权检查               │
  │                                                             │
  │  ③ 中间人替换   非官方渠道分发的 exe 被替换为恶意版本          │
  │                                                             │
  │  ④ 配置劫持     篡改 config.yaml 中的 AI API 密钥、OSS 凭证等  │
  │                                                             │
  │  ⑤ AI 幻觉修改  自改进功能误改关键代码导致不稳定              │
  │                                                             │
  └─────────────────────────────────────────────────────────────┘

策略:  每次启动前校验所有核心文件的 SHA-256 哈希，任何篡改立即发现。
       这不是 DRM，而是确保软件在用户手里的副本与原始发布一致。
```

### 24.2 完整性校验架构

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  启动流程                                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │  main.exe 启动                                            │   │
│  │      │                                                    │   │
│  │      ▼                                                    │   │
│  │  ┌──────────────────────┐                                │   │
│  │  │ 1. 自检模式？         │ ← 检测是否是首次运行/开发者模式  │   │
│  │  │   首次/开发 → 跳过校验 │                                │   │
│  │  └──────┬───────────────┘                                │   │
│  │         │ 正常模式                                        │   │
│  │         ▼                                                │   │
│  │  ┌──────────────────────┐                                │   │
│  │  │ 2. 加载 integrity.json│ ← 加密的哈希清单               │   │
│  │  │   不存在 → 首次构建清单│                                │   │
│  │  └──────┬───────────────┘                                │   │
│  │         │                                                │   │
│  │         ▼                                                │   │
│  │  ┌──────────────────────┐                                │   │
│  │  │ 3. 计算所有核心文件   │                                │   │
│  │  │    SHA-256 并比对     │                                │   │
│  │  └──────┬───────────────┘                                │   │
│  │         │                                                │   │
│  │    ┌────┴────┐                                           │   │
│  │    │ 校验通过？│                                           │   │
│  │    └────┬────┘                                           │   │
│  │     通过 │  失败                                          │   │
│  │      ▼   │   ▼                                            │   │
│  │  正常启动 │ ┌───────────────────────────┐                 │   │
│  │          │ │ 4. 篡改告警                 │                 │   │
│  │          │ │                             │                 │   │
│  │          │ │ ⚠️ 检测到文件被篡改！        │                 │   │
│  │          │ │                             │                 │   │
│  │          │ │ 已修改: 3 个文件              │                 │   │
│  │          │ │ ┌──────────────────────┐    │                 │   │
│  │          │ │ │ src/agent/loop.py    │    │                 │   │
│  │          │ │ │ 期望: a3f2b...       │    │                 │   │
│  │          │ │ │ 实际: 9e1c4...  ❌    │    │                 │   │
│  │          │ │ ├──────────────────────┤    │                 │   │
│  │          │ │ │ src/tools/browser.py │    │                 │   │
│  │          │ │ │ 期望: d8a1f...       │    │                 │   │
│  │          │ │ │ 实际: b7e3d...  ❌    │    │                 │   │
│  │          │ │ └──────────────────────┘    │                 │   │
│  │          │ │                             │                 │   │
│  │          │ │ [终止运行]  [信任此次]       │                 │   │
│  │          │ │             (需输入确认短语)  │                 │   │
│  │          │ └───────────────────────────┘                 │   │
│  │          │         │ 用户选择"信任此次"                    │   │
│  │          │         ▼                                      │   │
│  │          │    继续运行（仅本次，下次仍会检查）               │   │
│  │          │                                               │   │
│  └──────────┴───────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 24.3 完整性清单（integrity.json）

```json
{
  "version": 1,
  "generated_at": "2026-07-13T14:30:00+08:00",
  "generated_by": "7tan-updater build v5.1.0",
  "algorithm": "sha256",
  "scope": "core",
  "files": {
    "src/main.py": "a3f2b1c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1",
    "src/agent/agent_loop.py": "b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3",
    "src/agent/model_manager.py": "c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4",
    "src/tools/browser_tools.py": "d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e",
    "src/tools/download_tools.py": "e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f",
    "src/tools/registry.py": "f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a",
    "src/tools/oss_tools.py": "0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b",
    "src/tools/db_tools.py": "1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c",
    "src/tools/content_tools.py": "2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0",
    "src/tools/publish_tools.py": "3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e",
    "src/tools/self_modify_tools.py": "4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2",
    "src/tools/monitor_tools.py": "5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3",
    "src/database/db.py": "6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4",
    "src/config/loader.py": "7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5",
    "src/scheduler/scheduler.py": "8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6",
    "src/pipeline/pipeline.py": "9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e",
    "src/web/server.py": "0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f",
    "tools/check_integrity.py": "1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a"
  },
  "exclude_patterns": [
    "*.pyc",
    "__pycache__/**",
    "config.yaml",
    "data/**",
    "downloads/**",
    "logs/**",
    "backup/**",
    "*.log"
  ],
  "manifest_hmac": "f4e3d2c1b0a9..."
}
```

**设计要点**:

| 项目 | 说明 |
|------|------|
| `algorithm` | SHA-256，兼顾安全与速度 |
| `scope` | `core` = 核心代码 / `full` = 含静态资源 |
| `exclude_patterns` | 排除运行时产生的文件（日志/数据/备份等） |
| `manifest_hmac` | 用内置密钥对 manifest 自身做 HMAC-SHA256 防伪造 |

### 24.4 校验引擎实现

```python
# src/security/integrity.py

import hashlib
import hmac
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

__version__ = "5.1.0"  # 实际从项目版本管理中导入

class IntegrityChecker:
    """核心文件完整性校验引擎"""
    
    # 内置 HMAC 密钥（编译进 exe，不暴露在 json 中）
    # ⚠️ 生产环境从环境变量或 exe 编译常量中读取
    _SECRET = b"7tan_integrity_secret_v5"  # 占位，实际由 build 脚本注入
    
    def __init__(self, manifest_path: str, mode: Literal["core", "full"] = "core"):
        self.manifest_path = Path(manifest_path)
        self.mode = mode
        self.base_dir = Path(__file__).parent.parent.parent  # 项目根目录
    
    def load_manifest(self) -> dict:
        """加载完整性清单，验证 HMAC"""
        if not self.manifest_path.exists():
            return None
        
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        
        # 验证 manifest 自身未被篡改
        stored_hmac = manifest.pop("manifest_hmac", "")
        calculated_hmac = self._compute_manifest_hmac(manifest)
        
        if not hmac.compare_digest(calculated_hmac, stored_hmac):
            raise IntegrityError("❌ 完整性清单本身已被篡改！")
        
        return manifest
    
    def _compute_manifest_hmac(self, manifest: dict) -> str:
        """计算 manifest 的 HMAC-SHA256"""
        payload = json.dumps(manifest, sort_keys=True).encode("utf-8")
        return hmac.new(self._SECRET, payload, hashlib.sha256).hexdigest()
    
    def check_all(self) -> "IntegrityReport":
        """校验所有文件"""
        manifest = self.load_manifest()
        if manifest is None:
            return IntegrityReport(healthy=True, note="首次运行，无清单")
        
        report = IntegrityReport()
        expected_files = manifest.get("files", {})
        algorithm = manifest.get("algorithm", "sha256")
        
        for rel_path, expected_hash in expected_files.items():
            abs_path = self.base_dir / rel_path
            
            if not abs_path.exists():
                report.add_missing(rel_path)
                continue
            
            actual_hash = self._hash_file(abs_path, algorithm)
            
            if not hmac.compare_digest(actual_hash, expected_hash):
                report.add_modified(rel_path, expected_hash, actual_hash)
        
        return report
    
    def _hash_file(self, filepath: Path, algorithm: str) -> str:
        """计算文件哈希（大文件分块读取，不爆内存）"""
        h = hashlib.new(algorithm)
        with open(filepath, "rb") as f:
            while chunk := f.read(1024 * 1024):  # 1MB 块
                h.update(chunk)
        return h.hexdigest()
    
    def generate_manifest(self) -> dict:
        """生成新的完整性清单（构建/发布时使用）"""
        from .manifest_template import CORE_FILES
        
        manifest = {
            "version": 1,
            "generated_at": datetime.now().isoformat(),
            "generated_by": f"7tan-updater build {__version__}",
            "algorithm": "sha256",
            "scope": self.mode,
            "files": {},
            "exclude_patterns": [
                "*.pyc", "__pycache__/**",
                "config.yaml", "data/**", "downloads/**",
                "logs/**", "backup/**", "*.log"
            ]
        }
        
        file_list = CORE_FILES if self.mode == "core" else self._scan_all_files()
        
        for rel_path in file_list:
            abs_path = self.base_dir / rel_path
            if abs_path.exists():
                manifest["files"][rel_path] = self._hash_file(abs_path, "sha256")
        
        manifest["manifest_hmac"] = self._compute_manifest_hmac(manifest.copy())
        return manifest


@dataclass
class IntegrityReport:
    healthy: bool = True
    note: str = ""
    modified: list = field(default_factory=list)  # [(path, expected, actual), ...]
    missing: list = field(default_factory=list)    # [path, ...]
    
    @property
    def is_clean(self) -> bool:
        return self.healthy and not self.modified and not self.missing
    
    @property
    def tampered_count(self) -> int:
        return len(self.modified) + len(self.missing)
    
    def __str__(self) -> str:
        if self.is_clean:
            return "✅ 完整性校验通过，所有核心文件未被篡改。"
        lines = [f"⚠️ 检测到 {self.tampered_count} 个文件异常！", ""]
        for path, expected, actual in self.modified:
            lines.append(f"  ❌ {path}")
            lines.append(f"     期望: {expected[:16]}...")
            lines.append(f"     实际: {actual[:16]}...")
        for path in self.missing:
            lines.append(f"  ❓ {path} — 文件丢失")
        return "\n".join(lines)


class IntegrityError(Exception):
    """完整性校验失败"""
    pass
```

### 24.5 与自改进功能的协调

```
这是一个关键设计问题: AI 自改进功能会修改源码，修改后哈希必然变化。
如何区分「合法 AI 修改」和「恶意篡改」？

协调机制:

  ┌─────────────────────────────────────────────────────────────┐
  │                                                             │
  │  AI 修改源码（通过 self_modify_tools）                        │
  │      │                                                      │
  │      ▼                                                      │
  │  ┌──────────────────────┐                                   │
  │  │ 沙箱检查（语法/备份/确认）│ ← 详见 §12 自改进安全机制       │
  │  └──────┬───────────────┘                                   │
  │         │ 用户确认通过                                        │
  │         ▼                                                   │
  │  ┌──────────────────────┐                                   │
  │  │ 修改文件 + 自动更新    │                                   │
  │  │ integrity.json 中的   │  ← 🔑 关键步骤！                  │
  │  │ 对应文件哈希           │                                   │
  │  └──────┬───────────────┘                                   │
  │         │                                                   │
  │         ▼                                                   │
  │  ┌──────────────────────┐                                   │
  │  │ 重新计算 manifest_hmac│                                   │
  │  │ 保存 integrity.json   │                                   │
  │  └──────────────────────┘                                   │
  │                                                             │
  │  下次启动: 新哈希 → 校验通过 ✅                               │
  │                                                             │
  └─────────────────────────────────────────────────────────────┘

⚠️ 保护文件（main.py, config.yaml）不在自改进白名单中，
   因此 AI 无法修改它们，它们也始终在 integrity.json 的保护下。
```

### 24.6 防篡改保护分级

```
┌──────────────┬──────────────────────┬──────────────────────────┐
│   保护级别     │   覆盖范围              │   触发后行为               │
├──────────────┼──────────────────────┼──────────────────────────┤
│   严格        │ main.py / 核心引擎    │  拒绝启动，强制退出          │
│   (critical)  │ agent_loop / registry │  显示篡改详情 + 官方渠道     │
│              │                      │  必须用户输入确认短语         │
├──────────────┼──────────────────────┼──────────────────────────┤
│   标准        │ tools/* / pipeline/* │  警告弹窗，允许"信任此次"    │
│   (standard)  │ database/* / config/*│  记录日志，下次仍会检查       │
│              │                      │                            │
├──────────────┼──────────────────────┼──────────────────────────┤
│   宽松        │ web/* (前端静态资源)  │  仅日志记录，不影响运行       │
│   (loose)     │ utils/* 辅助工具     │  Web UI 顶部显示⚠️警示条     │
│              │                      │                            │
└──────────────┴──────────────────────┴──────────────────────────┘
```

### 24.7 config.yaml 防篡改配置

> 以下配置对应 config.yaml 中的 `integrity` 段（详见 §17.2 完整配置模板）。

```yaml
integrity:
  enabled: true                    # true=每次启动校验 / false=关闭

  # 严格模式文件（篡改任一 → 拒绝启动）
  critical_files:
    - src/main.py
    - src/agent/agent_loop.py
    - src/tools/registry.py
    - src/agent/model_manager.py

  # 保护策略
  mode: "core"                     # core=仅核心代码 / full=含全部静态资源
  auto_repair: false               # true=尝试从backup恢复被篡改文件（实验性）
  developer_mode: false            # true=跳过所有校验（开发调试用，发布时禁止）
  confirm_phrase: "我已知晓风险并信任此次修改"

  # Web UI 指示
  show_status: true                # 仪表盘显示完整性状态指示灯

  # 日志
  log_all_checks: true
  tamper_alert_email: ""           # 检测到篡改时发送邮件到此地址（可选）
```

### 24.8 Web UI 中的体现

```
仪表盘状态卡片新增:

  ┌──────────────────┐
  │ 🔐 完整性状态      │
  │                  │
  │  🟢 校验通过      │  ← 正常
  │  核心文件: 18/18 │
  │  最后校验: 14:30 │
  └──────────────────┘

  ┌──────────────────┐
  │ 🔐 完整性状态      │
  │                  │
  │  🟡 AI已修改3文件 │  ← AI 自改进后
  │  已知合法修改     │
  │  查看变更列表     │
  └──────────────────┘

  ┌──────────────────┐
  │ 🔐 完整性状态      │
  │                  │
  │  🔴 检测到篡改！  │  ← 异常
  │  3个文件被修改    │
  │  [查看详情]      │
  └──────────────────┘

设置页面新增:

  ┌─ [防篡改] ─────────────────────────────────────────────┐
  │  [✓] 启用完整性校验                                      │
  │                                                        │
  │  校验模式  [核心代码 ▼]         当前状态: 🟢 全部通过      │
  │                                                        │
  │  ┌────────────────────────────────────────────────┐    │
  │  │ 📋 最近校验记录:                                 │    │
  │  │ 14:30  ✅ 通过 (18/18)                          │    │
  │  │ 08:00  ✅ 通过 (18/18)                          │    │
  │  │ 昨天   ⚠️  2个文件变更 (AI自改进: agent_loop.py) │    │
  │  │ 前天   ✅ 通过 (18/18)                          │    │
  │  └────────────────────────────────────────────────┘    │
  │                                                        │
  │  [🔄 重新校验]  [📋 查看清单]  [📥 导出报告]            │
  └────────────────────────────────────────────────────────┘
```

### 24.9 项目结构补充

```
7tan-auto-updater/
│
├── 7tan-updater.exe                  ← ⭐ 运行时校验自身
├── integrity.json                    ← ⭐ 加密的完整性清单（发布时由 build 脚本生成）
│
│
├── tools/
│   ├── build.py                      ← 构建脚本（含生成 integrity.json）
│   └── check_integrity.py            ← 🔐 独立校验工具（脱离主程序也可运行）
│
├── src/
│   ├── security/                     ← ⭐ 安全模块
│   │   ├── __init__.py
│   │   ├── integrity.py              ← 完整性校验引擎
│   │   └── manifest_template.py      ← 核心文件清单模板
│   │
│   └── ...
```

### 24.10 构建时生成清单

```python
# tools/build.py — 构建脚本（开发者/CI 使用，不打包进 exe）

def build():
    """构建流程"""
    # ... PyInstaller 打包步骤 ...
    
    # 打包完成后，对产物目录生成完整性清单
    from src.security.integrity import IntegrityChecker
    
    checker = IntegrityChecker("dist/7tan-updater/integrity.json", mode="core")
    manifest = checker.generate_manifest()
    
    with open("dist/7tan-updater/integrity.json", "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print("✅ integrity.json 已生成，包含 18 个核心文件校验和")

def verify_build():
    """构建后验证（确保清单正确）"""
    checker = IntegrityChecker("dist/7tan-updater/integrity.json")
    report = checker.check_all()
    
    if report.is_clean:
        print("✅ 构建验证通过")
    else:
        print(report)
        raise SystemExit("❌ 构建验证失败")
```

### 24.11 安全注意事项

```
⚠️ 需要明确的限制:

1. 防篡改不是 100% 安全
   - 如果攻击者同时修改代码 + integrity.json → 可绕过
   - HMAC 密钥硬编码在 exe 中，反编译可提取（这是不可避免的）
   - 防的是: 用户自己/普通恶意软件的篡改；防不了: 专业逆向工程

2. 不要依赖它做 DRM
   - 这是完整性检查，不是许可证验证
   - 用户可以关闭校验（配置文件中设置），这是他们的权利

3. 开发者模式保护
   - config.yaml 中 `integrity.developer_mode: true` 跳过校验
   - 发布给用户时必须确保 `integrity.developer_mode: false`
   - 构建脚本自动将此项置为 false

4. 校验性能
   - 18 个核心文件，每个 1-100KB，SHA-256 总耗时 < 50ms
   - 不影响启动速度
   - 全量模式可能有上百个文件，总耗时 < 500ms
```

---

## 二十五、v4 修复清单对照

| # | 问题 | v4 修复 |
|---|------|---------|
| 1 | 缺少软件支持 | 数据库 `resource_type` 字段，分类体系覆盖游戏+软件，AI 自动区分 |
| 2 | 无版本更新 | `version`/`is_update`/`previous_id`/`update_log` 字段，AI 版本比较逻辑 |
| 3 | 绿色版未设计 | PyInstaller 打包（推荐 --onedir），Playwright 浏览器内置 |
| 4 | 无异常恢复 | 分级重试策略表 + 断点续传 + 全局异常兜底 |
| 5 | 无反爬 | Playwright 反检测配置 + 访问频率控制 + 代理支持 |
| 6 | 并发冲突 | 任务队列 + 全局锁 + 任务隔离（独立 Agent 实例） |
| 7 | 上下文爆炸 | ContextManager 滚动摘要 + HTML截断 |
| 8 | 自改进太危险 | 沙箱机制：语法检查 + diff预览 + 用户确认 + 备份 + 白名单 |
| 9 | restart困难 | 子进程重启方案 + 局限性说明 |
| 10 | 缺少调度模块 | `scheduler/` 目录 + APScheduler |
| 11 | 缺少数据库设计 | 四张表完整设计（resources / task_logs / source_sites / conversation_history） |
| 12 | 工具注册 | 统一 `registry.py` + `@register_tool` 装饰器 |
| 13 | 无代理 | `network` 配置段（config.yaml） |
| 14 | 源站需登录 | `source_sites` 表含 `need_login`/`login_url`/`cookies_json` |
| 15 | 无启动引导 | 首次启动检测无配置 → 交互式引导流程 |
| 16 | 无浏览器选择 | `浏览器类型`/`浏览器路径`/`无头模式` 配置 |
| 17 | 无大小限制 | `download_tools.py` 下载前 `check_before_download()` |
| 18 | 无成本追踪 | CostTracker + `token_usage()`/`cost_estimate()` 工具 |
| 19 | 流程顺序差 | 下载+改写并行 → pipeline.py 重构 |
| 20 | 对话触发不清晰 | 对话 Agent 创建子任务 → 任务队列 → 独立 Agent → 通知 |
