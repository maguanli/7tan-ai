# 🪞 WebMirror · 网页镜像工具（Web 版）

自动抓取整站，并 **按原站 URL 的目录结构原样保存** 到本地；提供浏览器界面实时看进度、在线浏览文件、一键打包下载。

```
https://example.com/docs/guide.html    →   downloads/<任务ID>/example.com/docs/guide.html
https://example.com/list?page=2         →   downloads/<任务ID>/example.com/list/@page=2/index.html
https://example.com/img/logo.png        →   downloads/<任务ID>/example.com/img/logo.png
```

---

## 1. 安装 & 启动

```bash
cd webmirror
pip install -r requirements.txt
python run.py                 # 默认 http://127.0.0.1:8000
python run.py --port 9000     # 换端口
python run.py --host 0.0.0.0  # 允许局域网访问
```

浏览器打开 `http://127.0.0.1:8000` 即可使用。

## 2. 界面用法

1. 左侧填 **起始网址**（支持多行，一行一个站点，最多 20 个）；
2. 调 **抓取深度 / 页面上限 / 并发数**；
3. 「高级选项」里可关闭"同站限制"、选择 `?参数` 的落盘方式等；
4. 点 **🔍 预览落盘路径** 可以先确认某个网址会被保存到哪个路径（不联网、纯本地计算）；
5. 点 **▶ 开始镜像抓取** → 中间看实时进度与日志 → 右侧文件树点开即预览；
6. 抓完后点 **⬇ 打包下载** 得到 zip（含目录结构 + 对照表）。

## 3. 路径映射规则

| 原始 URL | 本地路径 | 说明 |
|---|---|---|
| `https://ex.com/` | `ex.com/index.html` | 根目录 |
| `https://ex.com/docs/` | `ex.com/docs/index.html` | 目录 → index.html |
| `https://ex.com/docs/a.html` | `ex.com/docs/a.html` | 原样 |
| `https://ex.com/about` | `ex.com/about/index.html` | 无扩展名 → 目录形式 |
| `https://ex.com/about` | `ex.com/about.html` | 切换为"文件形式"时 |
| `https://ex.com/list?page=2` | `ex.com/list/@page=2/index.html` | **参数转目录**（默认） |
| `https://ex.com/list?page=2` | `ex.com/list/@q=46589c7afd/index.html` | 参数取哈希 |
| `https://ex.com/i.php?id=9` | `ex.com/i@id=9.php` | 文件 + 参数 |
| `http://ex.com:8080/x` | `ex.com_8080/x/index.html` | 非默认端口带后缀 |

规则要点：

* **一一对应**：不同 URL 一定落到不同文件，不会互相覆盖；
* **安全净化**：把 `<>:"/\|?*`、控制字符、`..`、Windows 保留名（`CON`/`NUL`…）替换掉，杜绝目录穿越与非法文件名；中文原样保留；
* **超长路径自动折叠**：单段 > 100 字符、总路径 > 240 字符时加哈希，避免超出文件系统限制；
* **可选链接重写**：把 HTML/CSS 里的 `href/src/url()` 改写成相对本地的路径（含 `<style>` 内联、`style` 属性、`srcset`、CSS `@import`），这样离线打开镜像可以直接点着浏览；外部域名链接保持原样。

### 3.1 原样保真：只改该改的字节

早期版本用 `str(BeautifulSoup(html))` 输出，而 BeautifulSoup 的序列化会**重排整个文档**：
把标签属性按自己的规则排序（`<meta name="viewport" content="...">` 变成 `<meta content="..." name="viewport">`）、
给 `<meta>/<link>/<br>/<img>` 等 void 元素补自闭合斜杠 `/>`、统一引号与空白——
结果就是“镜像下来的代码和原站不一样”。

现在改为 **最小化改写**（`app/minimal_html.py`）：用 `html.parser` 定位每个标签在原文中的
精确偏移，**只替换真正需要改的字节**（链接属性值、字符集声明），其余一律保持原样：

| 项目 | 处理 |
|---|---|
| 标签属性顺序 | 原样保留 |
| 引号风格（单引号 / 双引号 / 无引号） | 原样保留 |
| void 元素写法（`<br>` 与 `<br/>`） | 原样保留 |
| 空白、换行符（CRLF/LF）、缩进、注释 | 原样保留 |
| `<script>` 内容与注释里的 `<a href=...>` 字符串 | 不误伤 |
| 需要本地化的 `href/src/srcset/style/url()` | 改写成相对路径 |
| 字符集声明 | 见 §6（必须改成 UTF-8，否则乱码）|

实测：对 `https://example.com/` 做字符级 diff，**全页只有 `src=/s.js` → `src=s.js` 一处改动**；
对 `wangming.293.net` 的 `<head>` 逐字节比对，**仅 `href="/style/main.css"` 被本地化**，属性顺序、
引号、void 写法、CRLF 换行全部与原站一致。

## 4. 抓取规则

* 广度优先（BFS）递归，可设深度与页面上限；
* 页面爬取默认 **只抓同站**（起始主机及其子域），可关闭；
* 静态资源（CSS/JS/图片）默认 **同主域**（含兄弟子域），可选「仅本主机」或「任意主机」，见 §4.1；
* 默认并发 8，支持每请求延迟（对目标站友好）；
* 失败自动重试（默认 2 次），5xx 才重试；
* 可选遵守 `robots.txt`；
* 支持 `include_patterns` / `exclude_patterns` 正则过滤（API 传参）。

### 4.1 静态资源抓取范围 `asset_scope`（重要）

很多站点的样式/脚本/图片并不在页面同一个主机上，而是放在**兄弟子域或第三方 CDN**，例如：

```html
<link href="//i.293.net/2018/style.css" rel="stylesheet">   <!-- 兄弟子域 -->
<script src="http://apps.bdimg.com/libs/jquery/1.9.1/jquery.min.js"></script>  <!-- CDN -->
```

若把「同站」简单理解成「同主机」，这些资源会被整站跳过 → 页面抓下来了却**没有任何样式**。
因此本工具把「页面范围」和「资源范围」拆开：

| `asset_scope` | 含义 | 适用 |
|---|---|---|
| `same_host` | 仅与起始页同一个主机 | 最保守 |
| **`same_site`（默认）** | 同**主域**，即允许兄弟子域（`quhao.293.net` ↔ `i.293.net`） | 大多数站点 |
| `any` | 任意主机，含第三方 CDN | 想要完全离线可用 |

> 页面链接始终受 `same_domain` 约束，**不会**因为放开资源范围而爬到别的站去。

跨主机抓下来的资源按 **URL → 路径** 规则落在各自的主机目录下，链接改写成相对路径：

```
downloads/<任务ID>/
├── quhao.293.net/index.html      # 引用 ../i.293.net/2018/style.css
└── i.293.net/2018/style.css
```

**已知边界**：由 JavaScript 在运行时拼出来的资源路径（如 `layer.m.js` 里的
`b + "need/layer.css"`）静态扫描看不到，不会被自动抓取，需要手动补。

### 4.2 断点续抓 & 为什么它不会「越抓越慢」（重要）

中断（关窗口 / 崩溃 / 重启）后重新提交同一输出目录即可续抓，进度不丢。
三个文件分工：

| 文件 | 作用 | 写法 |
|---|---|---|
| `_mirror_queue.tsv` | 入队流水账（TSV：`深度 \t 类型 \t URL`，每 URL 一行） | 同步逐行写 |
| `_mirror_manifest.ndjson` | 落盘清单（已下载的 URL ↔ 本地路径） | 后台每 0.5s 批量刷 |
| `_mirror_state.json` | 进度快照（**只含小标量**） | 每 3s 覆盖写 |
| `_case_safe.json` | 大小写安全表（`case_safe_paths` + `requeue_urls`） | 手工生成，续抓时加载 |

> **大小写安全**：Windows 文件系统大小写不敏感，源站若存在仅大小写不同的 URL（如 `id_ab.html` / `id_AB.html`），会互相覆盖。本任务曾发生 189,343 组冲突、208,163 个页面被覆盖。启用 `case_safe_file` 后，命中的落盘路径会在扩展名前附加该 URL 的 8 位 md5（如 `id_ab-1a2b3c4d.html`），并把受影响的 URL 强制重新抓取。

续抓时用 **`待抓 = 入队流水 − 已落盘`** 精确还原队列，一个都不丢；
`visited`（已处理）与 `saved`（URL→路径）也全部由落盘清单重建。

> ⚠️ **性能红线，勿把三个集合写回快照。**
> 早期版本把 `visited / queue / saved` **全量**塞进 `_mirror_state.json`，
> 体积随抓取量线性增长。实测某任务跑到 28.5 万 URL 时：
> 快照 **87.2 MB**、`json.dumps` 单次 **1.34 秒**，而且是在**事件循环线程**上
> 序列化的 → 每 5 秒把所有 worker 冻结 1.34 秒（占空比 27%），**越抓越慢**。
> 改成小标量快照后：**87.2 MB → 3.7 KB**，同一任务实测吞吐
> **3.59 → 5.32 个/秒（+48%）**，达到源站并发上限的 85%。
> 回归哨兵：`tests/test_state_snapshot.py`、`tests/test_resume.py`。

顺带的两处优化：清单追加由「每个文件加锁 + 跳一次线程池」改为
**单写者 + 批量刷盘**（既省 syscall，也天然规避 Windows 上 `O_APPEND`
非原子导致的并发覆盖）；状态快照的节流判断前移到加锁之前。

### 4.3 面板速度指标：平均 vs 实时（为什么需要两个）

面板同时给出两个速度，**不要只看平均**：

| 指标 | 口径 | 用途 |
|---|---|---|
| `speed`（平均速度） | `已完成 / 自任务开始至今` | 总量估算、进度预测 |
| `speed_recent`（实时速度） | `最近 60 秒内完成数 / 窗口跨度` | **判断当下快慢、验证提速是否生效** |

> ⚠️ **长任务的累计平均会严重失真。** 实测 youbian 任务已跑 **25 小时**，
> 性能修复后真实吞吐已达 **5.2 个/秒**，面板上的平均速度却仍是 **3.3**
> —— 分子分母都被历史低谷期拖着，看起来像「提速没生效」。
> 加了实时速度后，同一时刻两个数字并排显示：**平均 3.3 / 实时 5.2**，「当下到底多快」一目了然。

实现要点（`Mirror._recent`）：

- `_write()` 每落盘一个页面/资源就打一个时间戳，口径与 `pages_ok + assets_ok` 一致；
- 只保留窗口内的打点（超出即淘汰），**内存不随任务时长增长**；
- 分母取 `min(60s, 实际已跑时长)`。任务刚启动不足 60 秒时，
  若直接用 60 秒做分母会把速度**严重低估**（预热期失真）；
- 任务结束后分母冻结在 `finished_at`，读数不再随时间衰减；
- 前端 `#m-speed-recent` 卡片用蓝色高亮，并在任务列表里对运行中的任务附带实时速度。

回归哨兵：`tests/test_speed_recent.py`（含「历史稀释」「预热期分母」「窗口淘汰」
「结束后冻结」等 7 项）。

## 5. 产出物结构

```
downloads/<任务ID>/
├── ex.com/                     ← 与源站一致的目录结构
│   ├── index.html
│   ├── about/index.html
│   ├── css/style.css
│   └── img/logo.png
├── _mirror_manifest.json       ← URL ↔ 本地路径 对照表（含大小/状态码/类型）
└── _mirror_report.txt          ← 人读版抓取报告（统计 + 对照表 + 失败列表）
```

## 6. 字符编码（重要）

**核心原则：镜像的所有文本文件一律以 UTF-8 落盘，并把文件里的编码声明同步改写成 UTF-8。**

只要这两件事有一件没做，浏览器就会拿旧编码去解析 UTF-8 字节 → 整页乱码。具体处理：

| 环节 | 处理 |
|---|---|
| 探测编码 | BOM → 整段合法 UTF-8 → 响应头/meta 声明（跳过 latin-1 这类不可靠的笼统声明）→ 高频汉字投票 → 兜底 |
| HTML | `<meta charset>` / `http-equiv` 一律改写为 utf-8；**完全没有声明时补上一个** |
| CSS | `@charset` 改写为 utf-8 |
| JS / JSON / XML / SVG | 非 UTF-8 的重新编码为 UTF-8；`<?xml encoding?>` 同步改写 |
| 图片等二进制 | 原样保存，不动 |
| 预览接口 `/serve` | 响应头显式带 `charset=utf-8` |

> ⚠️ 高频汉字投票这层是必要的：短样本下 `charset_normalizer` 会把 GBK 误判成 Big5
> （几个候选评分全都是 0.0，排序等于随机），解出来全是「笢恅拸汒」这类生僻字。

### 6.1 修复已有镜像（不用重抓）

旧版本虽然也是 UTF-8 落盘，但没同步改写声明。已经抓好的镜像可以就地修：

```bash
python repair_charset.py downloads/20261011-053631-387e4f            # 预演，只统计
python repair_charset.py downloads/20261011-053631-387e4f --apply    # 实际写入
python repair_charset.py downloads                                   # 整个目录
```

它**只改声明、不动正文一个字节**；已经是 utf-8 的文件会被跳过。
注意：如果服务器谎报编码导致抓取时字节就已受损，这种内容无法修复，只能重抓。

### 6.2 用记事本打开是乱码？

镜像的 HTML 都自带 `<meta charset="utf-8">`，用**浏览器**打开一定正常。
但如果用老版记事本 / Excel / 默认 ANSI 的编辑器打开 `.txt`、`.json` 这类文件，
它们可能不认 UTF-8（没有 BOM）而按 GBK 显示 → 乱码。这类文件请用 VS Code 等
可指定编码的编辑器打开。

## 7. 就地修复已有镜像

### 7.1 补抓缺失的静态资源（不用重抓整站）

如果某次抓取因为资源范围设错（例如旧版本的 `same_host`）导致整站没有样式，
**不需要重新抓几千个页面**，用 `repair_assets.py` 就地补齐即可：

```bash
python repair_assets.py downloads/20261011-061903-338184 --dry-run   # 预演：只列出缺什么
python repair_assets.py downloads/20261011-061903-338184             # 补抓 + 改写链接
python repair_assets.py downloads/20261011-061903-338184 --scope any # 连第三方 CDN 一起补
```

它会：① 扫描所有 HTML 找出仍指向外部的 CSS/JS/图片；② 按原路径规则下载缺失文件；
③ 把引用改写成相对本地路径；④ 递归处理 CSS 里的 `url()` / `@import`。
已存在的文件不会重复下载，`dns-prefetch` / `preconnect` 这类主机提示不会被误改。

### 7.2 修复字符编码声明

见 §6.1（`repair_charset.py`）。

## 8. HTTP API

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/tasks` | 建任务并启动（JSON：`url`,`max_depth`,`max_pages`,`concurrency`,`same_domain`,`asset_scope`,`include_assets`,`rewrite_links`,`param_mode`,`extensionless`,`with_host_dir`,`obey_robots`,`delay`…）|
| GET | `/api/tasks` | 任务列表 |
| GET | `/api/tasks/{id}` | 任务详情 + 统计 |
| GET | `/api/tasks/{id}/events` | SSE 实时进度 + 增量日志 |
| GET | `/api/tasks/{id}/logs?since=N` | 增量日志（轮询用） |
| POST | `/api/tasks/{id}/cancel` | 停止任务 |
| POST | `/api/tasks/{id}/delete` | 删除任务（含文件） |
| GET | `/api/tasks/{id}/tree` | 文件树 JSON |
| GET | `/api/tasks/{id}/raw?path=X` | 预览文件（`as_text=true` 强制文本） |
| GET | `/api/tasks/{id}/serve?path=X` | 内联返回文件（兼容旧接口） |
| GET | `/mirror/{id}/<原路径>` | **按镜像原路径**提供文件（预览 iframe 用；页面内相对引用的 CSS/JS/图片才能正确加载）|
| GET | `/api/tasks/{id}/download` | 打包 zip 下载 |
| GET | `/api/tasks/{id}/manifest` | 对照表 |
| GET | `/api/pathpreview?url=X` | 只算路径不抓取 |

## 9. 测试

```bash
python -m pytest tests -q        # 全部 44 项（路径映射 + 字符编码 + 最小化改写 + 资源范围）
python tests/test_paths.py       # 路径映射 30 项断言（唯一性/净化/穿越防护）
python tests/test_encoding.py    # 编码单元测试（探测/声明改写/CSS/JS）
python tests/test_minimal_html.py # 最小化改写单测（保真/引号/void/script 不误伤）
python tests/repro_encoding.py   # 端到端：本地起 GBK 站点整站镜像后按浏览器方式读回
python tests/real_site_check.py  # 真实 GB2312 站点（www.cnr.cn）整站镜像后校验
python tests/api_e2e.py          # 完整 API 链路（建任务→预览接口→编码校验→清理）
```

结果分别写入 `tests/*_result.txt`，方便直接查看。

`tests/testsite/` 是一个本地测试站点，可用于离线端到端验证：

```bash
_start_services.bat            # 启动 8801 测试站 + 8000 服务
```

## 10. 注意事项

* 请遵守目标站点的 `robots.txt` 与服务条款，控制并发、不要用于商业抓取；
* 默认关闭 TLS 校验（兼容自签证书），如需严格校验可在 `crawler.py` 里把 `verify=False` 改为 `True`；
* 动态渲染（SPA）站点抓到的可能是空壳页，本工具只做静态镜像，不含浏览器渲染。
