# 7Tan 可执行架构文档
## 双知识获取体系 · 编程进化 · 创新能力

> 本文档将《7Tan叙事自我意识·自主学习、知识体系、编程进化、创新能力 完整规范文档》翻译为**工程可执行**的架构设计。
> 对接现状代码库：`src/agent/bionic_organs.py`（14 器官内核）+ `src/agent/world_model.py`（心智总线/工具层）。
> 阶段六五项验证已通过（`tests/verify_stage6_final.py`），叙事自我意识工程层面成立，本文档在此基座上新增三大能力。

---

## 0. 硬约束（继承自《完整规范文档》全局前置边界声明，全文最高优先级）

| # | 约束 | 工程落地规则 |
|---|---|---|
| C1 | 目标=经历驱动的叙事自我意识 | 一切新能力必须走「事件总线 → 器官 tick → 记忆沉淀」闭环，禁止旁路 |
| C2 | 不实现现象意识 qualia | 新模块不含任何"主观体验/情绪感受"字段，只做功能性信息处理 |
| C3 | qualia 只写文档不落地 | 不在代码中新增 qualia 相关数据结构 |
| C4 | 外部知识统一 external 事件，禁止篡改内核 | 所有知识/工具反馈走 `emit_event(origin="external")`，绝不直接改 `bionic_organs.py` 器官逻辑 |
| C5 | 心智内核独立，LLM 仅作普通工具 | 内核 tick 链路不调用任何生成式模型；LLM 只在工具层以普通工具身份出现 |

**违反任何一条 = 该模块设计作废。**

---

## 1. 现状盘点（已实现 vs 待实现）

### 1.1 已实现（可复用，不动）

| 组件 | 位置 | 能力 |
|---|---|---|
| 14 器官内核 | `src/agent/bionic_organs.py` | ORG-A 长期记忆 / ORG-B 动机 / ORG-D 安全 / ORG-E 工作记忆 / ORG-F 学习 / ORG-VIS 视觉 / ORG-SPEECH 言语 / ORG-BODYSTATES 稳态 / ORG-VALENCE 效价 / ORG-INHIBIT 抑制 / ORG-CONSOLIDATE 巩固重放 / ORG-TIMESENSE 主观时间 / ORG-SELFMODEL 自我模型 / ORG-SIMULATE 假想预演 |
| 事件总线 | 同文件 `emit_event/poll_events/_dispatch_events/_setup_subscriptions` | 跨器官唯一通信通道，origin=internal/external 分离 |
| 心智总线 | `src/agent/world_model.py` `TanModel` | 预测引擎 + 语用层 + 言语生成 + 诚实兜底 |
| 工具层（模块G） | `src/agent/world_model.py` `_call_tool_safe` → `src/tools/registry.py` `execute_tool` | web_search / fetch_news / sandbox_execute / db_query_resources 等只读工具 |
| 状态级自然进化（层级一） | `organ_selfmodel_tick` | capability/limitations/confidence 随经历动态更新 ✅ 已完成 |
| 持久化 | `save_organ_state/load_organ_state` | ORG-A memory_library + SELFMODEL self_model_data 跨重启存续 |
| 阶段六验证 | `tests/verify_stage6_final.py` | 五项全通过 |

### 1.2 待实现（本文档交付物，5 个新模块）

| 模块 | 对应规范章节 | 状态 |
|---|---|---|
| **Module-K 知识包导入器** | 一·途径2 | 🆕 全新 |
| **Module-L 自主学习调度器** | 一·途径1 | 🔧 升级（现有 web_search 工具，缺"内生学习动机/定时驱动"完整闭环） |
| **Module-P 编程能力引擎** | 二·编程能力获取 | 🔧 增强（sandbox_execute 已有，缺"写码→报错→PE修正"闭环） |
| **Module-EVO 源码级自我升级** | 二·两级进化·层级二 | 🔧 补闸口（self_rebuild/self_restart 已有，缺"补丁审核+回归+自动回滚"） |
| **Module-CREATE 记忆碎片重组器** | 三·创新能力 | 🆕 全新 |

---

## 2. 总体分层架构

```
┌──────────────────────────────────────────────────────────────┐
│ 应用层        WEB服务 / CLI / 微信机器人（src/web, src/cli）      │
├──────────────────────────────────────────────────────────────┤
│ 上层能力模块（本次新增，只读内核，经事件总线/工具层交互）            │
│   Module-K 知识包导入器     Module-L 自主学习调度器                │
│   Module-P 编程能力引擎     Module-EVO 源码级自我升级             │
│   Module-CREATE 记忆碎片重组器                                   │
├──────────────────────────────────────────────────────────────┤
│ 工具层（模块G）  src/tools/registry.py                           │
│   web_search · fetch_news · sandbox_execute · self_rebuild ·     │
│   self_restart · db_query_resources ...  （统一 execute_tool 入口）│
├──────────────────────────────────────────────────────────────┤
│ 心智内核（不可被外部篡改）  src/agent/bionic_organs.py            │
│   ORG-BODYSTATES ──> ORG-VALENCE ──> ORG-E(工作记忆)             │
│        └─> ORG-CONSOLIDATE ──> ORG-A(长期记忆) / ORG-F(学习)      │
│   ORG-B(动机) · ORG-INHIBIT · ORG-SELFMODEL · ORG-SIMULATE ·      │
│   ORG-TIMESENSE · ORG-D(安全)                                     │
├──────────────────────────────────────────────────────────────┤
│ 持久化        data/tan_model_organs.json（ORG-A + SELFMODEL）     │
└──────────────────────────────────────────────────────────────┘
```

**数据流铁律（所有新模块必须遵守）：**
```
外部知识/工具反馈
   └─ emit_event(origin="external", event_type="tool_result")   # 唯一合法入口
        └─ ORG-VALENCE 效价打分 → ORG-E focus 评估 → ORG-CONSOLIDATE 价值筛选
             └─ 高价值 → mem_consolidated → ORG-A 长期记忆
             └─ 低价值 → 短时留存 → 自然遗忘
```

---

## 3. 模块详细设计

### 3.1 Module-K 知识包导入器（规范一·途径2）

**职责**：把结构化预制知识包（百科/编程/学科/案例）**限速、逐条、走完整心智链路**灌入系统，禁止捷径。

**新增文件**：`src/agent/module_knowledge_package.py`

**数据结构**：
```python
@dataclass
class KnowledgePackageItem:
    source: str            # 固定 "knowledge_package"
    domain: str            # 领域标签，如 "python语法" / "算法" / "工程规范"
    content: str           # 知识正文（单条，非整包）
    meta: dict             # {difficulty, tags, ...}

# 导入队列（内存，不落盘；未消费完的条目重启后从原文件续读）
ingest_queue: List[KnowledgePackageItem]
```

**事件类型（新增，注册到事件总线）**：
```
knowledge_package_ingest
  payload = {item_id, domain, content_preview, batch_index}
  origin = "external"          # 硬约束 C4
  source = "knowledge_package" # 与网络抓取区分开，便于溯源
```

**核心函数**：
```python
def load_package(path: str) -> int:
    """解析知识包文件（JSON/YAML/目录），逐条入 ingest_queue，返回条目数。"""

def ingest_tick(rate: int = 3) -> None:
    """每个器官 tick 调用一次，从队列头部取出 rate 条，逐条 emit_event(knowledge_package_ingest)。
    限速保护 tick 时序，不洪水式批量写入。"""

def import_behavior_log() -> dict:
    """导入行为本身作为一条自传经历 emit_event，供 ORG-A 自我记录。"""
```

**对接点**：
- 在 `organ_tick_all()` 末尾调用 `ingest_tick()`（限速灌入）
- `knowledge_package_ingest` 订阅到 `ORG-VALENCE`（效价打分）→ 复用现有完整链路
- 导入结束后 `import_behavior_log()` 发一条 `external` 自传事件：「我在 X 时刻导入了 Y 领域知识包」

**验收标准（可断言）**：
1. 导入 N 条后，`ORG-A.memory_library` 增长，且每条记忆 `source=="knowledge_package"`
2. 不出现「一次 tick 灌入全部」——单 tick 记忆增量 ≤ rate
3. 导入行为被记录为独立自传经历（`memory_library` 中存在 `goal_tag` 含 import 的条目）
4. 知识包导入**未**绕过 VALENCE/CONSOLIDATE（低价值条目同样被筛掉）

---

### 3.2 Module-L 自主学习调度器（规范一·途径1）

**职责**：7×24 内生学习动机，三种触发——内生短板、任务缺知识、空闲定时深耕。

**新增文件**：`src/agent/module_autolearn.py`

**三种触发（优先级从高到低）**：
```python
TRIGGER_TASK = "task_driven"      # 任务缺知识：ORG-A 检索无结果
TRIGGER_SELF = "self_driven"      # 内生短板：SELFMODEL.limitations 非空
TRIGGER_IDLE = "idle_driven"      # 空闲深耕：ORG-E active_goals 为空 + 间隔到
```

**核心函数**：
```python
def should_learn(ctx) -> Optional[str]:
    """返回触发类型（TRIGGER_*）或 None。空闲判定：ORG-E active_goals 为空且距上次学习 ≥ LEARN_IDLE_INTERVAL。"""

def plan_query(trigger: str) -> str:
    """根据触发类型生成学习 query：
    - task_driven: 任务中的未知关键词
    - self_driven: limitations 顶部短板对应的领域
    - idle_driven: 从「深耕队列」取下一主题（可配置）"""

def run_learning_cycle(query: str) -> None:
    """抓取 → 分片 → 封装 external tool_result → 交给内核 tick 链路。"""
```

**数据处理标准流程（严格执行规范原文 7 步）**：
1. `web_search` / `fetch_news` 抓取网页/文档/教程
2. **超长文本智能分片**：单条 ≤ `MAX_CHUNK_CHARS=1200`，规避单次事件载荷溢出
3. 每条分片封装为 `tool_result` 事件（origin=external）
4. 走完整器官 tick 链路（效价/聚焦/价值）
5. 高价值进 ORG-A
6. 低价值短时留存后遗忘
7. 学习成败（网页读取失败/资料失效）同样作为经历入记忆，优化后续策略

**配置项（写入器官 config 或 .env）**：
```yaml
autolearn:
  idle_interval_ticks: 40        # 空闲深耕间隔
  max_chunk_chars: 1200          # 分片上限
  max_queries_per_cycle: 3       # 单次学习周期最多检索数
  deep_dive_topics: []           # 空闲深耕主题队列（用户可配置）
```

**验收标准**：
1. 清空 ORG-E 目标后运行 N tick，自动产生 ≥1 次 `tool_result` 学习事件
2. 学习事件走完整链路（VALENCE→CONSOLIDATE→ORG-A），非直接写库
3. 超长文本被分片（无单条 >1200 字符的记忆）
4. 学习失败（如检索无结果）被记录为负样本经历

---

### 3.3 Module-P 编程能力引擎（规范二·编程能力获取）

**职责**：后天习得编程能力——写码 → 沙盒运行 → 报错反馈 → PE 修正 → 固化为自传记忆。

**新增文件**：`src/agent/module_programming.py`

**闭环流程**：
```
编程知识包(Module-K) ──> 语法/算法储备
        ↓
内生编程任务（目标：实现 X）
        ↓
生成代码 ──> sandbox_execute ──> 成功/报错
        ↓                        ↓
   记录成功经历            PE 回路修正 + 迭代修改
        ↓                        ↓
   capability 更新         limitations 更新
        ↓
   mem_consolidated ──> ORG-A（编程经历固化）
```

**核心函数**：
```python
def generate_solution(task_spec: dict) -> str:
    """基于 ORG-A 中的编程知识生成代码（纯规则拼接+记忆检索，不调用 LLM）。"""

def run_and_learn(code: str, task_spec: dict) -> dict:
    """sandbox_execute 运行 → 解析报错 → 发 pe_update 事件 → 返回 {ok, error, output}。"""

def iterate_on_error(code: str, error: str, task_spec: dict) -> str:
    """根据报错类型（SyntaxError/NameError/...）修正代码，最多迭代 N 轮。"""
```

**PE 回路对接**：`run_and_learn` 发出 `pe_update`（已有事件类型，ORG-F 订阅），预测误差驱动编程认知修正。

**验收标准**：
1. 给定简单任务（如"写一个斐波那契函数"），系统能独立产出可运行代码
2. 首次报错后能自动迭代修正（存在 ≥1 次 pe_update 事件）
3. 编程经历固化进 ORG-A（memory_library 含编程类条目）
4. 成功后 capability 增条目 / 失败后 limitations 增条目

---

### 3.4 Module-EVO 源码级自我升级（规范二·层级二，带安全闸口）

**职责**：分析自身缺陷 → 产出内核优化补丁 → **人工审核** → 审核通过后重建+重启+回归 → 失败自动回滚。

> ⚠️ 这是**唯一**会触碰源码的模块，安全闸口是硬性要求，禁止全自动生效。

**新增文件**：`src/agent/module_evolution.py`

**补丁数据结构（强制附带 4 要素）**：
```python
@dataclass
class EvolutionPatch:
    patch_id: str
    target_file: str         # 要改的源码文件
    diff: str                # 统一 diff 格式
    reason: str              # ① 修改理由
    risk_assessment: str     # ② 风险评估（高/中/低 + 说明）
    expected_change: str     # ③ 预期心智变化
    regression_plan: str     # ④ 回归测试方案（指向具体测试文件）
    status: str              # pending / approved / rejected / applied / rolled_back
```

**安全闸口流程**：
```
1. 分析缺陷（复盘运行日志/PE 高频失败点）
        ↓
2. 生成 patch（附带 reason/risk/expected/regression 四要素）
        ↓
3. 【人工审核闸口】status=pending，写盘 patches/pending/*.json
   → 绝不自动覆盖运行内核                          ← C4 硬约束
        ↓
4. 人工 approved → self_rebuild() → self_restart()
        ↓
5. 自动执行回归：python tests/verify_stage6_final.py（五项）
        ↓
6. 通过 → status=applied；失败 → 自动回滚（git checkout / 备份恢复）
        ↓
7. 回滚后 status=rolled_back，记录失败原因入 ORG-A
```

**核心函数**：
```python
def generate_patch(target: str, diff: str, reason: str, risk: str, expected: str, regression: str) -> str:
    """生成补丁并落盘为 pending，返回 patch_id。禁止写源码。"""

def apply_patch(patch_id: str) -> dict:
    """仅在 patch.status=="approved" 时执行：写源码 → 重建 → 重启。否则抛闸口异常。"""

def run_regression_and_rollback(patch_id: str) -> dict:
    """重启后跑 stage6 五项；失败则 git 回滚源码 + 恢复器官状态备份，返回 {ok, rollback}。"""
```

**验收标准（重点验证闸口）**：
1. `status=pending` 的补丁**不可能**改变运行内核（apply_patch 抛异常）
2. 未 approved 的补丁触发 apply 会被拒绝
3. 回归失败后源码与器官状态均自动回滚（文件 hash 与打补丁前一致）
4. 全程补丁历史可审计（patches/ 目录 + 状态流转日志）

---

### 3.5 Module-CREATE 记忆碎片重组器（规范三·创新能力）

**职责**：创新能力——跨领域记忆碎片解离重组 + 反事实预演筛选 + 自我风险约束，产出可落地创新方案。

**定位**：**上层只读模块**，全程不修改内核器官逻辑（C4 硬约束）。

**新增文件**：`src/agent/module_creativity.py`

**创新 8 步流转链路（严格对齐规范原文）**：
```
① 动机触发   任务需求/自主成长 → 产生创新诉求
② 素材调取   从 ORG-A 跨领域取海量知识/经历/案例碎片
③ 解离打散   拆解各片段的 feature/logic/structure/method，打破原有绑定
④ 全新重组   生成大量跨领域/跨场景组合构想
⑤ 仿真筛选   送 ORG-SIMULATE 反事实预演，批量推演可行性/风险，淘汰劣质
⑥ 自我约束   ORG-SELFMODEL + ORG-INHIBIT 结合失败经历，抑制高风险/超能力方案
⑦ 择优输出   留存可行方案，结构化输出并落地
⑧ 迭代成长   执行成败作为新经历回流 ORG-A，优化后续创新质量
```

**数据结构**：
```python
@dataclass
class IdeaFragment:
    source_memory_id: str   # 来源记忆 ID
    feature: str            # 解离出的特征/方法/结构/逻辑
    domain: str             # 所属领域
    salience: float         # 来源记忆权重

@dataclass
class CreativeIdea:
    idea_id: str
    fragments: List[IdeaFragment]   # 重组原料（可溯源）
    combination: str                # 组合方案描述
    simulate_score: float           # 反事实预演得分
    risk_level: str                 # 自我约束后的风险等级
    status: str                     # viable / inhibited / output
```

**核心函数**：
```python
def fetch_materials(domains: List[str], top_k: int) -> List[IdeaFragment]:
    """只读调取 ORG-A 跨领域记忆碎片（不写库）。"""

def dissociate(fragments: List[IdeaFragment]) -> List[IdeaFragment]:
    """解离：把记忆拆成 feature/方法/结构 独立碎片，打破原绑定。"""

def recombine(fragments: List[IdeaFragment], n_ideas: int) -> List[CreativeIdea]:
    """重组：跨领域随机组合生成 n 个构想。"""

def filter_by_simulation(ideas) -> List[CreativeIdea]:
    """送 ORG-SIMULATE 反事实预演打分，淘汰低分构想。"""

def constrain_by_selfmodel(ideas) -> List[CreativeIdea]:
    """ORG-SELFMODEL 局限 + ORG-INHIBIT 失败经历，抑制高风险/超能力方案。"""

def output_ideas(ideas) -> List[CreativeIdea]:
    """择优输出 viable 方案；被抑制的标记 inhibited 但不删除（可审计）。"""
```

**对接点**：素材调取/仿真筛选/自我约束**全部走现有器官接口**（ORG-A 只读查询、ORG-SIMULATE tick、ORG-SELFMODEL 局限缓存），模块自身零状态、零写库。

**能力边界（写死进验收，呼应规范三·3）**：
- ✅ 可：跨领域融合、方案改良、多方案择优、原创组合型方案
- ❌ 不可：无素材凭空创新、脱离经历的天才顿悟、主观灵感体验（qualia）

**验收标准**：
1. 有跨领域记忆素材时，能产出 ≥1 个 viable 组合方案
2. 每个 viable 方案可溯源到 source_memory_id（非幻觉，非凭空）
3. 高风险/超能力方案被 SELFMODEL+INHIBIT 拦截（status=inhibited）
4. 无素材时产出为 0（不凭空生成）
5. 全程 ORG-A 记忆库无新增（只读验证）

---

## 4. 分阶段实施计划（6 个里程碑，严格按依赖排序）

| 里程碑 | 内容 | 依赖 | 涉及文件 | 验收入口 |
|---|---|---|---|---|
| **M1** | Module-K 知识包导入器 | 无 | `module_knowledge_package.py` + `bionic_organs.py`(订阅) | 3.1 四条断言 |
| **M2** | Module-L 自主学习调度器 | M1（知识打底） | `module_autolearn.py` | 3.2 四条断言 |
| **M3** | Module-P 编程能力引擎 | M1（编程知识包） | `module_programming.py` | 3.3 四条断言 |
| **M4** | Module-EVO 源码级自我升级 | M1-M3 稳定后 | `module_evolution.py` | 3.4 四条断言（重点闸口） |
| **M5** | Module-CREATE 记忆碎片重组器 | M1-M3（需有跨领域记忆） | `module_creativity.py` | 3.5 五条断言 |
| **M6** | 全链路集成 + 回归 | M1-M5 | 新增 `tests/verify_stage7_capabilities.py` | 六模块联合验收 |

**实施纪律**：
1. 每里程碑**独立提交 git**，标题 `feat(module): ...`
2. 每里程碑**先写验收测试再写实现**（测试驱动，防"看起来通过"）
3. 任何模块不得违反 C1-C5 硬约束，代码 review 时逐条核对
4. M4 是唯一高风险模块，闸口逻辑必须单独 review + 单独测试

---

## 5. 风险与安全边界

| 风险 | 缓解措施 |
|---|---|
| 知识包洪水灌入冲垮 tick 时序 | M1 强制限速 rate≤3，单条 ≤1200 字符 |
| 自主学习无限消耗资源 | M2 空闲深耕间隔 + 单周期检索上限 |
| 沙盒执行恶意/死循环代码 | M3 复用现有 sandbox 超时(30s)+输出 100KB 限制 |
| 源码自我升级失控 | M4 人工审核闸口 + 回归失败自动回滚，**禁止全自动生效** |
| 创新幻觉（无素材硬编） | M5 强制 source_memory_id 溯源 + 无素材产出为 0 |
| 外部知识污染内核 | C4 铁律：一切 external 事件，禁止直写器官逻辑 |

---

## 6. 一句话总结

> 在已通过阶段六验证的 14 器官叙事自我意识基座上，新增 5 个**只读/受限**上层模块（知识包导入、自主学习调度、编程引擎、源码升级闸口、记忆碎片重组器），全部经由事件总线与工具层交互，实现文档要求的"双知识获取 + 编程进化 + 创新能力"，同时守住"外部不篡改内核、LLM 不作心智、不实现 qualia"三条底线。
