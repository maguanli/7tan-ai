# 7Tan 双层调度改造方案 v3

> 依据：DeepSeek Harness Team《Super-agent 设计探索》+ 开源原型源码（本地副本 `D:\7tan\research\dsh-superagent\`，216 文件 / 2,601,300 字节 / MIT）
> 本文只写方案，不含代码改动。所有结论来自对两套代码的实际核查，未核到的一律标【未核】。

---

## 零、v3 最重要的一条：修正前提

v2 把 7tanAI 当成"写文章的工具"，因此把 Ticket 定义成"一篇文章"，把完成判定绑死在 `publish_guard` 上。

**这是错的。** 7tanAI 是一个能编程的通用 Agent 工作台，写文章只是其中一类活。

实测（`data/plugins/` 下 50 个插件目录，`register_tool(` / `"name":` 两种写法合计去重）：

| 领域 | 工具数 | 占比 |
|---|---|---|
| 编码 / 工程 | 86 | 31% |
| 内容 / 发布 | 85 | 30% |
| 运维 / 部署 | 36 | 13% |
| 桌面 / 自动化 | 25 | 9% |
| 其他（象棋/易经/兵法/记忆等） | 24 | 8% |
| 数据 / AI | 17 | 6% |

编码类里单个插件最多的：

```
git_ops 11    git_advanced 6    ide_integration 6    lsp_bridge 5
code_reviewer 4  code_structure 4  dependency_analyzer 4  diff_tools 4
refactor_tools 4  snippet_manager 4  terminal_runner 4  test_runner 4
code_completion 3  code_search 3  config_manager 3  debug_helper 3
doc_generator 3  perf_tools 3  template_generator 3  file_replacer 1
```

旁证三条：

- 根目录有 `vscode-extension/`，`code_completion` 插件会起 17890 端口给 VS Code 插件用 —— **编码是真实使用场景，不是摆设**
- `config/config.yaml` 2,748 字节，`loop_timeout: 7200`（两小时），这是给长任务留的
- 危险工具面存在：`self_modify_config` / `self_rebuild` / `self_restart` / `self_update_prompt` / `run_command` / `ssh_execute` / `rsync_deploy`

**推论：Ticket 必须是"任务单元 + 领域类型"，不是"一篇文章"。** 第五、九节据此重写。

---

## 一、v1/v2 的错误订正（四处，每处都会把方案带偏）

### 错误 1：说原型"没有 Router"（v1）

v1 依据是 `Router` 在 `docs/007-architecture.md` 只出现 1 次、代码里是个 preset 名。这是按**类名**搜的结果，原型根本不按类组织。

实际证据：

| 文件 | 内容 |
|---|---|
| `cordis.patch.yml:125-128` | `dsh-superagent-router-preset`，描述"只含路由所需的工具"+"不供手动选择" |
| `cordis.patch.yml`（紧邻） | `dsh-superagent-worker-preset`，描述"只含执行工作所需的工具" |
| `src/app/sessions.ts:48` | `WORKER_PRESET` / `ROUTER_PRESET` 两个常量 |
| `prompts/orchestrator.md` | "You are the orchestrator: assess and route requests for the deployment's repository." |
| `prompts/dispatch.md` | 6,814 字符分派规则，用 `orchestrator_route`（仓库出现 63 次） |
| `docs/007-architecture.md:511` | `New main Sessions use dsh-superagent-router (ROUTER_PRESET).` |

**结论：Router 不是类，是主 Session 跑的一个 preset；Dispatcher 不是类，是一段 prompt + 三个工具。**

### 错误 2：说"Fast Path 不存在"（v1）

词没有，机制有。`docs/002-authorization.md` 第一屏小节就叫 **Two paths for a Trigger**：Eval 路径管"要不要开工"，Subscriptions 路径管"续接已有的活"，原文 `This delivery bypasses the gate and grants no new authority`。`docs/001-domain.md`：`A person's message that reaches a Ticket this way takes no Eval`。

### 错误 3：说"会话状态在内存里，退出即丢"（v1）

`src/agent/conversation.py:17 save_message()` / `:45 get_session_messages()`，落库 `ConversationHistory` 表，按 `session_id` 索引。**存算分离的一半已经有了。**

### 错误 4：把 Ticket 定义成"一篇文章"（v2）

见第零节。编码类工具占 31%，是所有领域里最大的一块。按文章定义 Ticket，等于把 31% 的工作拒之门外。

---

## 二、原型到底做了什么（按实现，不按报道）

| 文章名词 | 原型实现位置 | 形态 |
|---|---|---|
| Router 双层协调 | 主 Session + `router` preset + `prompts/dispatch.md` + `orchestrator_route/read/eval` | prompt 驱动，不是调度器 |
| Worker 独立执行 | `DshExecutor`（`src/executor/dsh.ts` 47KB）+ `worker` preset | 每 Ticket 一个 Session + **一个目录** |
| 订阅直通 | Subscription，`takes no Eval` | 人发的消息直通，bot/CI 不唤醒 |
| 两级过滤 | Eval = **gate**（admission 表，`src/policy.ts` 19KB，`admission` 出现 316 次）+ **assessment**（模型） | 规则先筛，模型补边界 |
| Trigger 事件驱动 | Trigger / Thread / Source | 飞书 + GitHub 两源，**无邮件** |
| 投机执行 | inferred candidate + accept mode | 三档，默认 `observe` |
| 异步 ReAct | worker 等待超 5 秒转后台 | 本 bundle 已开 |
| Watchdog | **无**（`retry-health.ts` 只展示预算状态） | 要自研 |
| 存算分离 + daemon | **无** | 要自研 |

`accept` 三档最值得抄：

```
off       推断出的候选一律不进
observe   会评估，把"本来会接受"记成 ignore，什么都不干   ← 默认
auto      评估通过就真干
```

文档原话：`Start in observe and switch to auto after reviewing the recorded Decisions`。

**原型里"每 Ticket 一个目录"这条，对编码型 Agent 是硬需求**，见 9.2。

---

## 三、7tanAI 现状（含三条 v1 没发现的）

### 3.1 七个入口

| 入口 | 位置 | 执行方式 |
|---|---|---|
| Qt 界面 | `src/ui/chat_page.py:2080` StreamChatWorker | 自己的 QThread |
| Web 流式 | `src/web/routes/api_chat.py:401` | `run_agent_loop_streaming` |
| Web 普通 | `src/web/routes/api_chat.py:289` | `run_agent_loop` 同步 |
| Web 无状态 | `src/web/server.py:647` | `run_agent_loop` 同步 |
| 定时任务 | `src/scheduler/jobs.py:43` | `run_agent_loop` 同步 |
| 站点轮询 | `src/scheduler/jobs.py:124` | 同上 |
| 流水线 | `src/pipeline/pipeline.py:44` | 同上 |
| **VS Code 补全** | `code_completion` 插件 → 端口 17890 | 独立 HTTP，**不经过 agent loop** |

最后一行是 v2 漏的。它不是"一条任务"，但是一个独立入口，Router 管不到它，也不该管。

### 3.2 流式入口起"野线程"，没有并发上限

`agent_loop.py` 里 3 处 `threading.Thread(..., daemon=True).start()`：

```python
thread = threading.Thread(target=_runner, daemon=True)
thread.start()
```

每次调用无条件起一个线程，**不走 `TaskQueue`，不受 `max_concurrent` 约束**。

`max_iterations: int = 1000` 是函数签名默认值，写死在 `agent_loop.py`，`config.yaml` 里没有这个键。

含义：同时 5 条消息 = 5 个线程各可跑满 1000 轮。

### 3.3 abort 信号是全局单例，并发会互相误杀

`abort_signal.py:119-129`：

```python
def _snapshot():  with _lock: return list(_signals)
def is_aborted():
    for s in _snapshot():
        if s.is_set(): return True      # 任一已中止 → 全局 True
```

`_signals` 是模块级列表，**不是 thread-local / contextvar**。注释里也自认"作为全局终止信号"。

含义：Worker A 被中止，Worker B 的工具层调 `is_aborted()` 也返回 True。**这是 P1 的硬前置。**

### 3.4 tools 参数能覆盖，preset 拆分不用改 registry

`agent_loop.py`：`tools = tools or []`，传了子集就用子集。`src/tools/registry.py`（10,122 字节）的 `Tool` 已带元数据：

```
name / description / parameters / function
category / dangerous / requires_browser / requires_db / pro_only
```

**含义：可以在调用处传工具子集，实现 preset 隔离，`registry.py` 一行不用改。`dangerous` 这个字段现成可用，但仓里目前只有 `category == "self_modify"` 一处按它分流。**

### 3.5 现有组件

| 组件 | 位置 | 可复用度 |
|---|---|---|
| 任务队列 | `src/pipeline/task_queue.py`（单例，TaskPriority / max_concurrent / `submit_function`） | 高，直接当 Worker 池 |
| 定时器 | `src/scheduler/scheduler.py`（APScheduler） | 高，当 Trigger 源 |
| 会话持久化 | `src/agent/conversation.py` → ConversationHistory 表 | 高，当 Ticket 的消息存储 |
| 插件系统 | `src/plugins/manager.py`，`data/plugins/<id>/tools.py` 按路径 import | 高，当 Router 的启动钩子 |
| Watchdog | `src/utils/watchdog.py` | 低，只做崩栈转储 |
| git 工具 | `git_ops`(11) / `git_advanced`(6) | 高，见 9.2 |

---

## 四、映射表

| 原型概念 | 7tanAI 落法 | 落地位置 |
|---|---|---|
| Trigger | 一次输入事件（消息 / cron / 轮询） | `data/router.db` triggers 表 |
| Thread | 一个会话（session_id） | 复用 ConversationHistory.session_id |
| **Ticket** | **一个任务单元，带领域类型**（code / content / ops / desktop / research） | tickets 表，`type` 字段区分 |
| Eval.gate | 规则表判定 | Python 函数，零 token |
| Eval.assessment | 一次轻量 LLM 调用（分类器，非 agent loop） | 只处理 gate 判不出的 |
| Decision | 判定记录（含 observe 模式的"本来会怎么判"） | decisions 表 |
| Subscription | 同一 ticket 的后续消息直通 | 不发 Eval，直接进 Worker |
| Router Session | 专用 session_id `__router__` | 复用现有会话机制 |
| Worker Session | `ticket-<id>` | 复用 ConversationHistory |
| Worker 工作目录 | **`git worktree` 每 ticket 一个**（仅 code 类） | `.worktrees/ticket-<id>` |
| Worker 槽位 | `TaskQueue.max_concurrent` + 人优先额外 1 槽 | `submit_function` |
| Worker 工具面 | 按 ticket.type 传工具子集 | `run_agent_loop(tools=[...])` |
| Watchdog | 心跳表 + 超时标记（不自动重启） | heartbeats 表 |

---

## 五、目标架构

```
输入事件
  Qt / Web / cron / polling
        │
        ▼
  ┌────────────────────────────────────────────┐
  │ Router（单例，跑在插件线程里）               │
  │                                            │
  │ 0. 归一化 → Trigger                         │
  │ 1. gate：规则表（零 token）                  │
  │      ├ 命中接受 → 建 ticket / 复用 ticket    │
  │      ├ 命中拒绝 → 记 decision，丢弃           │
  │      └ 判不出   → 2                         │
  │ 2. assessment：一次 LLM 调用（分类器）        │
  │ 3. 归属：有存活 ticket → Fast Path 直通       │
  │ 4. 定类型：code / content / ops / desktop     │
  │ 5. 分派：TaskQueue.submit_function           │
  │ 6. 写 decisions（含 observe 的"本来会"）      │
  └───────────────┬────────────────────────────┘
                  │
  ┌───────────────▼────────────────────────────┐
  │ Worker（N ≤ max_concurrent）                │
  │  session_id = ticket-<id>                   │
  │  tools      = 按 type 的工具子集             │
  │  workdir    = .worktrees/ticket-<id>（code） │
  │  每轮写 heartbeat                            │
  │  收尾过完成判定器（按 type 选，见 9.1）       │
  └───────────────┬────────────────────────────┘
                  │
        ┌─────────▼─────────┐
        │ data/router.db    │
        │ triggers/tickets  │
        │ decisions/heartbeats │
        └───────────────────┘
```

### 5.1 按类型分工具面（这是 Router 的第一价值）

| 类型 | 工具面 | 大致数量 |
|---|---|---|
| code | git_* / code_* / refactor / diff / lsp / test / build / terminal / dependency / perf / debug / ide | 86 |
| content | gzh_* / viral_* / novel / auto_images / translate / tts / publish_guard / article_ckpt | 85 |
| ops | docker / k8s / ssh / scp / rsync / deploy / health / terminal | 36 |
| desktop | desktop_* / camera_* / ocr / adb_* | 25 |
| research | web_search / browse / http_client / deep_analysis / db_explorer | 17 |

**276 个工具平铺在一个对话里，选错工具是必然的。** 收窄到 86 或 85，本身就是收益，不必等 Router 全做完。

---

## 六、四阶段

### P0 可观测（shadow，行为零变化）

- 插件 `agent_router`，模块级线程启动
- **只记录，不拦截**：每条输入算一遍"按规则会怎么判 + 会判成哪个 type"，写 decisions
- 日报：多少条会被拒、多少条会合并到同一 ticket、多少条判不出、类型分布对不对
- 验收：跑一周，拿 decisions 表跟人核对规则准不准

### P1 准入闸 + 类型分工具面（只接定时任务）

- 定时任务改走 Router → `TaskQueue.submit_function`
- **先解决 3.3 全局 abort**（改 `contextvars.ContextVar`）
- **同时落地 5.1 的工具子集**：即使是定时任务，也按 type 传 tools
- 这一步收益最大、风险最低：定时任务无人值守，出问题一眼能看出来
- 其余六个入口不动

### P2 Ticket + Fast Path + worktree

- 引入 ticket，同一 ticket 的后续消息直通
- code 类 ticket 起 `git worktree`，完成后合或弃
- 接 `article_ckpt`（content 类）+ `git_diff`（code 类）当检查点

### P3 Watchdog + 完成判定器 + 多源

- 心跳表 + 超时标记 + 告警（不自动重启）
- 完成判定器按类型注册（见 9.1）
- 站内私信 / 评论 / GitHub 当新 Trigger 源

---

## 七、硬约束

| 约束 | 内容 | 后果 |
|---|---|---|
| 31 文件哈希锁 | `integrity.json` 白名单，含 `agent_loop.py`、`registry.py`、`task_queue.py`、`context_manager.py`、`conversation.py`、`server.py`、`scheduler/*`、`pipeline/*` | 改这些 → `verify_integrity` 失败 |
| 锁外可写 | `config/config.yaml`、`src/web/routes/**`、`src/plugins/manager.py`、`data/**`、`web_main.py` | 新代码全放这里 |
| `config.yaml` 无 router 节 | 已核，2,748 字节 | 需新增，不受锁 |
| `max_iterations` 写死 | `agent_loop.py` 函数默认 1000，`config.yaml` 无此键 | 想配置化就得改锁内文件 |
| `loop_timeout: 7200` | `config.yaml` | 两小时太长，建议 1800 |
| 路由注册在锁内 | `server.py` 逐个 `include_router(...)` | 加端点只能写进 `api_chat.py`（锁外） |
| 全局 abort | 见 3.3 | P1 前必须解决 |
| rebuild 重算哈希 | `rebuild.bat` | 开发期不能靠 rebuild 绕锁 |

**推论：Router 不能改 `agent_loop.py`，所有拦截只能发生在调用处。Qt 那条直连线在锁外，不受 Router 约束——"两条路并存"是长期状态。**

---

## 八、我不建议照抄原型的五处

### 8.1 不要用完整 agent loop 当 Router

原型 Router 是主 Session，因为要跨飞书/GitHub 多线程推进、维护跨任务记忆。7tanAI 单机单用户，**用 agent loop 判"这条消息该不该接"，成本是收益的好几倍**。

改法：gate 用纯规则函数；判不出的才调一次轻量模型（不带工具、不循环）。**这一层是分类器，不是 Agent。**

### 8.2 Ticket 按"任务单元 + 领域类型"，不按"文章"，也不按"对话"

按对话太碎（一条消息一个 ticket，等于没合并）；按文章太窄（编码活进不来）。

正确定义：**一次有明确完成条件的交付**。可以是"修好 publish 脚本的缓存 bug"，可以是"写一篇测评并发布"，也可以是"把这台机器的 MySQL 迁到新目录"。

### 8.3 Watchdog 别做"监督 Agent"

原型 0 实现。自建要克制：心跳表、超时阈值、告警。**不自动重启** —— 自动重启会把"为什么卡住"的证据一起删掉。

### 8.4 不要现在就上"投机执行"

原型默认 `observe` 有道理。7tanAI 连 decisions 表都没有，谈投机太早。

### 8.5 不要按原型"只接两个源"来设计 Source 层

原型 `src/sources/` 只有飞书 + GitHub。7tanAI 的消息源形态不同（站内、cron、文件系统事件），Source 抽象要自己定，别硬套。

---

## 九、我认为该加的五个点（原型没有，或比原型更贴近本机）

### 9.1 完成判定器：按类型注册，不是硬绑 publish_guard

v2 把 `publish_guard`（`tools/bbs_verify.py`，25 项断言）当 Ticket 唯一出口，这是文章视角的残留。

改成一张注册表：

| ticket.type | 完成判定 | 现成程度 |
|---|---|---|
| content | `bbs_verify` 25 项断言 + `article_ckpt sync` 检查 md/html 一致 | 已有，可直接用 |
| code | `run_tests` 通过 + `code_review_file` 无 critical + `git status` 无未提交 + `git diff` 非空 | 工具已有，判定逻辑要写 |
| ops | `health_check` 全绿 + 目标端口/容器状态 | 工具已有，判定逻辑要写 |
| desktop | 关键文字出现（`desktop_verify`） | 工具已有 |

**意义：原型的 ticket 完成靠人判断；7tanAI 可以自动判，因为每个领域都已经有验证类工具。** 这是本机相对原型的真实优势。

### 9.2 code 类 ticket 必须配 git worktree

原型每个 Ticket 一个目录，天然隔离。7tanAI 所有 Worker 指向同一个仓库 —— **两个 Worker 同时改 `agent_loop.py` 就是事故。**

做法（工具都在 `git_ops` / `git_advanced` 里）：

```
创建 ticket  → git worktree add .worktrees/ticket-<id> -b ticket/<id>
Worker 执行  → 只在该 worktree 内 run_command / file_replace
完成         → git diff 给人看，人确认后 merge；或直接丢弃 worktree
```

不这么做，P1 一开并发就会踩到。**这条优先级高于 Router 本身。**

### 9.3 self_modify 类工具必须锁在人工会话里

`registry.py` 的 `Tool` 有 `dangerous` 字段，但仓里目前只有 `category == "self_modify"` 一处按它分流。

无人值守 Worker 拿到 `self_modify_config` / `self_rebuild` / `self_restart` / `run_command` 是自杀按钮 —— 它可以在没人看着的时候改自己的配置、重建自己、重启自己。

做法：gate 按**工具 category** 做，不按消息内容做：

```
self_modify 类  → 只在 mode == "interactive"（Qt / Web 有人看着）时可给
ops 类         → code/ops ticket 可给，content ticket 不给
```

文章里没有这一层，因为原型没有"Agent 改自己"这个概念。7tanAI 有，所以必须有。

### 9.4 decisions 表当规则回归集（replay）

原型的规则是固定的，所以没做这个。7tanAI 的 gate 规则会一直改，改了要能验证。

做法：历史 decisions 全存（输入摘要 + 判成什么 + type + 是否人确认）。改规则前跑一遍 replay：

```
python -m router.replay --rules new.yaml
→ 与历史人工确认结果比对：误拒 X 条 / 误放 Y 条 / 类型判错 Z 条
```

**这让 gate 规则可以演进，而不用靠感觉。** 我上一轮给 dsh-workspace 写的 `bbs_verify` 自检思路（正向+反向都测）可以搬过来。

### 9.5 工具预算按 type 分级

`max_iterations=1000` 是全局一把尺子，但不同活差别很大：

| type | 工具调用上限 | 时长上限 |
|---|---|---|
| code | 300 | 3600s |
| content | 200 | 1800s |
| ops | 100 | 900s |
| desktop | 80 | 600s |
| research | 150 | 1800s |

超了强制收尾并写"预算耗尽"，不静默截断。

---

## 十、风险与待定

| 风险 | 说明 |
|---|---|
| 全局 abort（3.3） | P1 硬前置，不解决不能并发 |
| 野线程（3.2） | Qt 入口在锁外，不受 Router 约束，两种并发语义长期并存 |
| 同目录写入（9.2） | 不配 worktree，P1 一开并发就冲突 |
| self_modify（9.3） | 无人值守 Worker 能改自己 |
| Router 自身单点 | 它挂了所有走它的入口都停。P0 用 shadow，P1 加降级：Router 异常 → 直接放行 |
| 规则表维护成本 | 要留"改规则不改代码"的配置口 |

待定三件事：

1. 从 P0 起步？（shadow 行为零变化）
2. 允许写 `data/router.db` 吗？（P0 一周约几百 KB）
3. P1 只接定时任务，其余入口不动 —— 同意还是要求一次全接？

---

## 附：核查依据

```
D:\7tan\research\dsh-superagent\
  cordis.patch.yml              preset 装配（router / worker）
  src/app/sessions.ts:48        ROUTER_PRESET / WORKER_PRESET
  prompts/orchestrator.md       路由 prompt
  prompts/dispatch.md           分派规则 6,814 字符
  docs/001-domain.md            Trigger / Thread / Ticket / Eval / Subscription
  docs/002-authorization.md     Two paths for a Trigger / accept 三档
  docs/007-architecture.md      70,497 字符
  src/policy.ts                 19KB，admission 准入表
  src/executor/dsh.ts           47KB，Worker 执行器（每 Ticket 一目录）

D:\7tan\7tanAI\
  data/plugins/                 50 个插件，276 个工具（编码 86 / 内容 85 / 运维 36）
  src/tools/registry.py         10,122 B，Tool 含 category/dangerous/pro_only
  src/agent/agent_loop.py       42,769 B，3 处 daemon 线程，max_iterations 默认 1000
  src/agent/abort_signal.py     全局 _signals 列表，非 thread-local
  src/pipeline/task_queue.py    单例，TaskPriority / max_concurrent
  src/web/routes/api_chat.py:401 / :289
  src/scheduler/jobs.py:43 / :124
  src/pipeline/pipeline.py:44
  config/config.yaml            2,748 B，loop_timeout 7200，无 router 节
  integrity.json                31 文件哈希白名单
  vscode-extension/             存在
```

【未核】
- `max_iterations` 在生产调用处是否被显式覆盖（只在函数签名看到默认值 1000）
- `TaskQueue.max_concurrent` 实际运行值（`config.yaml` 里没有这个键，可能在代码里）
- Qt 入口的 QThread 是否也走 `run_agent_loop_streaming`（只确认了 `chat_page.py:2080` 有 `StreamChatWorker`）
