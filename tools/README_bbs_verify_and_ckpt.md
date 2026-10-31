# 发布验收 + 定稿快照（两个工具）

2026-11-01 新增。解决两个反复踩过的问题。

---

## 一、为什么要做

### 问题 1：发完帖靠"我自己读页面确认"

以前每次发布，流程最后一步是 AI 亲自抓 HTML、逐条打印、口头汇报"已核对"。
这种"自己查自己"的形式漏过三次：

| 发生过的事 | 缺的东西 |
|---|---|
| 汇报"文件 17.9 KB"，实际 18,913 B（没量） | 没有强制"量一遍再报" |
| `shots/` 留着改动前的旧截图，被当成新稿 | 没有"改了正文就清旧图"的规则 |
| 首页缓存漏清，新帖没出现在首页，却先说"已上线" | 没有"发完必须验首页"的断言 |

共同点：**不是不知道怎么做，是缺少一个独立于我、会说不的东西。**

### 问题 2：同一篇文章改五六轮，每轮从零重读全文

5000 字读五六遍，费 token 是小事，容易记错才是大事。
实际踩过：第三轮把"六句话六个喂"改对了，第五轮差点又写回"四个喂"，
因为每轮都在重读全篇，"已经定稿的部分"这个概念从来没落过盘。

---

## 二、`bbs_verify.py` —— 发布验收断言

纯 HTTP，从游客视角抓公开页面。**不连数据库、不需要服务器密码。**

```bash
# 最基本
python tools/bbs_verify.py 84149

# 推荐用法：直接从文章源推导期望值，形成「源文件 → 线上页面」闭环
python tools/bbs_verify.py 84149 --from-article D:\7tan\dsh-workspace\article-zcy

# 只验帖子页，不抓列表/首页/主页（快 3 倍）
python tools/bbs_verify.py 84149 --from-article <目录> --no-lists

# 结果存 JSON，便于以后接自动化
python tools/bbs_verify.py 84149 --json result.json
```

退出码：`0` 无 FAIL / `1` 有 FAIL / `2` 抓不到页面。

### 25 项检查

| # | 检查 | 判据 |
|---|---|---|
| 1 | HTTP 状态 | 200 |
| 2 | 页面 `<title>` | 非空 |
| 3 | h1 与 JSON-LD `headline` 一致 | 防标题渲染错位 |
| 4 | 标题与文章源一致 | md 的 `#` 行 / html 的 h1 / txt 首行，三级回退 |
| 5 | 标题不含"实测" | 用户铁律 |
| 6 | 正文字数 | ≥ 300 汉字 |
| 7 | 正文图片数 | > 0 |
| 8 | `background-image` 数与图片数一致 | 自洽 |
| 9 | 图注数与图片数一致 | 自洽 |
| 10 | 图片数与文章源一致 | 需 `--from-article` |
| 11 | 小标题数与文章源一致 | 需 `--from-article` |
| 12 | 副标题块 | 存在则报数 |
| 13 | 图片全部可访问 | 并发 HEAD，26～31 张约 2 秒 |
| 14 | UBB 标签已全部渲染 | `[title]` `[/caption]` `[divider]` 等 |
| 15 | 图片占位符已替换 | `{IMG01}` 残留 |
| 16 | PHP 无报错 | Warning/Notice/Fatal/Deprecated/Parse |
| 17 | 板块正确 | 从 breadcrumb 的 `/bbs/board/N/` 读 |
| 18 | 作者 uid 正确 | 从 `profile.php?id=` 读 |
| 19 | 无 AI 套话 | 综上所述 / 由此可见 / 值得一提的是 … |
| 20 | 无"按图写"表述 | 如上图 / 按图片 / 从图上 … |
| 21 | 关键串全部命中 | 需 `--expect` 配 `must_contain` |
| 22 | board 列表收录 | 列表页含 `/bbs/PID/` |
| 23 | 首页收录 | 首页含 `/bbs/PID/`（这条专门抓缓存漏清） |
| 24 | 作者主页收录 | `/bbs/user/N/` 含本贴 |
| 25 | div 配对 | 结构完整 |

### 一个坑，已经处理

站内会把 UBB 原文塞进内联 JSON，页面里能数到十几处字面 `[title]`。
不剔除 `<script>` 的话第 14 项会一直假阳性。脚本里 `strip_scripts()` 就是干这个的。

### `--expect` 文件格式

```json
{
  "title": "《xxx》测评：xxx",
  "images": 26,
  "sections": 14,
  "board": "游戏交流",
  "uid": "1",
  "must_contain": ["1668", "7.0", "本人未实测"]
}
```

也可以直接 `--images 26 --board 游戏交流 --uid 1` 单传。

---

## 三、`article_ckpt.py` —— 定稿快照

```bash
# 存一次快照（文章改到某个可以定稿的状态时）
python tools/article_ckpt.py save D:\7tan\dsh-workspace\article-zcy --note 电话一节改为只留第一句

# 下一轮：只要摘要，不重读全文
python tools/article_ckpt.py show D:\7tan\dsh-workspace\article-zcy

# 这轮改了什么？逐段列出来
python tools/article_ckpt.py check D:\7tan\dsh-workspace\article-zcy

# 查 md 与公众号版 html 是否同步（防"改了源文件忘了重出 html"）
python tools/article_ckpt.py sync D:\7tan\dsh-workspace\article-zcy

# 只看含数字的段落（硬事实清单）
python tools/article_ckpt.py facts D:\7tan\dsh-workspace\article-zcy
```

### `show` 输出什么

标题、源文件、保存时间、字数/段数、14 个小节清单、**含数字的硬事实段落**（前 15 条）、
最近改动记录、以及"源文件已改动，快照过期"的警告。

下一轮读这个摘要 + 本轮新增要求就够，不用读 4600 汉字全文。

### `check` 输出什么

段落级差异，带新旧原文对照：

```
⚠️  正文已改动
   字符 7525 → 7529 (+4)    汉字 4609 → 4612 (+3)
   段落 133 → 133 (+0)      图片 26 → 26 (+0)

   ~ 旧53 → 新53  改写
      旧: 这六行只是每通电话的第一句，不是通话内容。
      新: 这是我后来改的句子……
```

原理：每段算 sha1 前 10 位存为指纹，用 `difflib.SequenceMatcher` 比对指纹序列。
只有指纹变了才算改动，纯格式调整不会误报。

退出码：`0` 未变 / `1` 有变更。

### 快照文件

存在文章目录下的 `_checkpoint.json`，约 30 KB（含段落预览）。
**不进 git**，跟着文章目录走。

---

## 四、`selftest.py` —— 证明工具会报错

一个永远返回 PASS 的检查脚本比没有检查更糟。

```bash
python tools/selftest.py            # 全部（含联网，约 40 秒）
python tools/selftest.py --offline  # 只测本地部分
```

做 7 项自证：

| 测什么 | 期望 |
|---|---|
| 假 pid（99999999） | 判 FAIL，退出码 1 |
| 正常帖子 84149 | 判 PASS，退出码 0 |
| 故意写错的期望值 | 至少 3 处 FAIL |
| `save` | 生成 `_checkpoint.json` |
| 未改动 `check` | 返回 0 |
| 改动一处 `check` | 返回 1，且能指出新旧段落 |
| html 未同步 `sync` | 返回 1，报缺失段号 |

当前状态：**7 项全通过**。

---

## 五、和其他脚本的关系

现有的 `publish_*.py`（在 `dsh-workspace/article-*/`）是**一次性发布脚本**，
里面把"资产检查 → 传图 → 写库 → 清缓存 → 页面核对"串成一条龙。
它的问题是核对部分散在脚本末尾，靠 print 给人看。

这两个工具是把那部分**抽出来做成通用断言**：

```
写 md  →  build_ubb  →  publish（传图+写库+清缓存）  →  bbs_verify（断言）
                                                          ↓
                                               FAIL 就当场停，不口头汇报
```

发布脚本里可以直接调：

```python
rc = subprocess.call([sys.executable, r'D:\7tan\7tanAI\tools\bbs_verify.py',
                      str(pid), '--from-article', str(WS)])
if rc != 0:
    raise SystemExit('验收未通过，看上面的 FAIL 项')
```

这么改之后，"内容错了但我说没错"这条路就断了。

---

## 六、已实测

| 帖子 | 板块 | 结果 |
|---|---|---|
| 84149 《我的总裁女友》 | board/18 游戏交流 | 25 项：24 PASS / 1 SKIP |
| 84142 《我在大清当皇帝》 | board/65 手机网游交流讨论区 | 25 项：21 PASS / 4 SKIP |
| 84127 《现代空战3D》 | board/18 游戏交流 | 25 项：21 PASS / 4 SKIP |

SKIP 是没配 `must_contain` / 用了 `--no-lists`，不是失败。

> 注意：`84142` 那篇的 md 里没有 `# 标题` 行（标题只在 html 里），
> 所以标题提取加了三级回退。不同文章的 md 格式不统一，这一条是必需的。
