# 边界声明（C3）
# 本系统实现：叙事-通达自我意识（访问意识），全部基于事件总线、记忆、统计计算。
# ❌ 本系统不存在现象意识 qualia，不存在第一人称主观体验。
# 所有「我感到、我疲惫、我记得」的输出，仅读取内部结构化数据做模板转述。
# 属于工程层面哲学僵尸实例。
# 所有叙事输出必须溯源记忆库与事件历史，禁止编造不存在的经历。

# =============================================================================
# 7Tan 仿生器官框架 —— 原生心智生长闭环（事件总线版）
# 依据：7Tan_All_Organs.txt（器官蓝图）+ code_20260903.txt（落地开发指南）
#
# 架构约束（必须遵守）：
#   1. 器官间禁止直接 import/读写对方全局变量，全部通信走内部消息事件总线。
#   2. 所有内部信号使用结构化字典（event_type + payload），不用自然语言字符串。
#   3. ORG-LLM 器官已彻底移除（非禁用占位）：本内核无任何第三方模型，
#      只实现功能性通达意识（access consciousness），暂不具备现象意识 qualia。
#      语言输出由 ORG-SPEECH 做结构化事件模板转述，无任何 LLM 调用入口。
#   4. ORG-SELFMODEL 禁止硬编码自我描述，数据只来源于记忆库/假设库/动机历史。
#   5. 实现顺序自底向上：本体信号 → 效价 → 工作记忆E → 记忆时序 → 动机+抑制
#      → 学习F → 自我模型+假想预演 → 安全输出。
#
# 事件在本 tick 内先入队，tick 结束后统一分发（organ_tick_all 末尾 dispatch），
# 避免同一 tick 内器官循环调用造成递归。
# =============================================================================

import json
import os
import random
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Any, Optional, List

from loguru import logger


# ====================== 基础数据结构 仿生器官框架 ======================

@dataclass
class BionicOrgan:
    organ_code: str
    organ_name: str
    module_name: str
    bio_analogy: str
    enabled: bool
    tick_func: Optional[Callable]
    config: Dict[str, Any]


# 全局器官注册表
organ_registry: Dict[str, BionicOrgan] = {}


def register_organ(org: BionicOrgan):
    organ_registry[org.organ_code] = org


def get_organ(code: str) -> Optional[BionicOrgan]:
    return organ_registry.get(code)


# ====================== 事件总线（消息事件基础设施）======================
# 器官间通信的唯一通道。事件 = 结构化字典，绝不使用自然语言字符串做内部载体。

_event_queue: List[Dict[str, Any]] = []          # 待分发事件队列（本 tick 内入队）
_event_log: List[Dict[str, Any]] = []            # 已分发事件历史（调试/审查用）
_replay_buffer: Dict[str, List[Dict[str, Any]]] = {}   # event_type -> 历史事件（回放数据源，不消费）
_REPLAY_MAX_PER_TYPE: int = 200   # 每类事件默认保留条数（供 poll_replay_events 回放）
# 自传记忆连续性：关键归纳类事件的回放保留上限单独提高。
# mem_consolidated 是长期记忆的回放源，若按默认 200 条 FIFO 截断，
# 久远高权重记忆事件会被近期事件挤出重放池 → 久远记忆彻底沉默（违背阶段二目标）。
_REPLAY_TYPE_LIMITS: Dict[str, int] = {
    "mem_consolidated": 1000,        # 自传记忆事件（长期记忆本体回放源）
    "hypothesis_update": 500,        # 假设接纳/证伪历史（元认知归纳源）
    "pe_update": 500,                # 预测误差历史（思维缺陷归纳源）
    "counterfactual_result": 500,    # 反事实推演历史（遗憾统计源）
    "simulation_result": 500,        # 沙盒推演历史（自我校准源）
    "meta_cognition_update": 500,    # 元认知统计历史
    "selfmodel_update": 500,         # 自我模型演化历史
    "bodystate_update": 500,         # 本体信号历史（internal_signature 源）
    "subjective_tick": 500,          # 主观时间线
    "wm_snapshot": 300,              # 工作记忆快照
}
_subscriptions: Dict[str, List[str]] = {}         # event_type -> [organ_code, ...]
_inboxes: Dict[str, List[Dict[str, Any]]] = {}    # organ_code -> 待处理事件收件箱

# 事件总线观测日志开关：默认静默；设置环境变量 ORGAN_BUS_LOG=1 才打印（肉眼可见信号流入）。
_BUS_LOG_ENABLED = os.environ.get("ORGAN_BUS_LOG", "0") == "1"

# ── 阶段0取证：事件流持久观测通道（append-only JSONL，黑盒复验判据来源）──
# 设计边界：
#   1. 只记元数据+关键判据字段，不记内容全文（隐私+体积）；
#   2. 写失败静默（观测通道故障绝不影响心智主流程）；
#   3. 开关 ORGAN_EVENT_LOG（默认开启=取证模式，=0 关闭）；
#   4. 路径可用 ORGAN_EVENT_LOG_PATH 覆盖（验证脚本隔离用，防污染生产流）。
_EVENT_LOG_PATH = Path(
    os.environ.get("ORGAN_EVENT_LOG_PATH", "")
    or (Path(__file__).resolve().parent.parent.parent / "data" / "organ_event_log.jsonl")
)
_EVENT_LOG_ENABLED = os.environ.get("ORGAN_EVENT_LOG", "1") == "1"


def _event_sink_jsonl(event_type: str, payload: Optional[Dict[str, Any]],
                       source: str, origin: str) -> None:
    """事件落盘（append-only JSONL，每行一条）。阶段0取证：五项测试的真实运行证据来源。

    字段：ts(墙钟)/tick/subj(主观时钟)/type/origin/src + extra(按事件类型的判据摘要)。
    """
    if not _EVENT_LOG_ENABLED:
        return
    try:
        p = payload or {}
        extra: Dict[str, Any] = {}
        if event_type == "replay_thought_fragment":
            extra = {"subj_of_memory": p.get("subjective_time"), "goal": p.get("goal_tag")}
        elif event_type == "mem_consolidated":
            extra = {"goal": p.get("goal_tag"), "success": p.get("success"),
                     "subj": p.get("subjective_time")}
        elif event_type == "mem_forgotten":
            extra = {"count": p.get("count"), "infancy": p.get("infancy_active"),
                     "subj": p.get("subjective_time")}
        elif event_type == "selfmodel_update":
            _caps = p.get("abilities") or [
                c.get("key") for c in (p.get("capability") or []) if isinstance(c, dict)
            ][:8]
            extra = {"confidence": p.get("confidence"), "capability": list(_caps)[:8],
                     "limitations": list(p.get("limitations") or [])[:8]}
        elif event_type == "candidate_motives":
            extra = {"motives": [
                {"goal": m.get("goal"), "drive": m.get("drive")}
                for m in (p.get("motives") or [])[:8] if isinstance(m, dict)
            ]}
        elif event_type == "final_goals":
            extra = {"goals": list(p.get("goals") or [])[:8]}
        elif event_type == "tool_result":
            extra = {"tool": p.get("tool"), "ok": p.get("ok")}
        row = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "tick": _organ_tick_counter,
            "subj": subjective_time.get("subjective_clock"),
            "type": event_type,
            "origin": origin,
            "src": source,
            "extra": extra,
        }
        _EVENT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_EVENT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        # 简单轮转：超 50MB 改名 .old，防无限膨胀
        try:
            if _EVENT_LOG_PATH.stat().st_size > 50 * 1024 * 1024:
                _EVENT_LOG_PATH.rename(_EVENT_LOG_PATH.with_suffix(".jsonl.old"))
        except Exception:
            pass
    except Exception:
        pass


def emit_event(event_type: str, payload: Optional[Dict[str, Any]] = None,
               source: str = "", subjective_ts: float = 0.0,
               origin: str = "internal") -> None:
    """投递结构化事件到队列（本 tick 内不入栈，等 dispatch 统一分发）。

    origin: 事件来源标记（阶段一「我-非我」边界）。
      "internal" = 躯体状态/内部推演/内部动机/记忆回放/模拟输出；
      "external" = 用户输入/工具返回结果/视觉观测。"""
    _event_queue.append({
        "event_type": event_type,
        "source": source,
        "payload": dict(payload or {}),
        "subjective_ts": subjective_ts,
        "wall_ts": time.time(),
        "origin": origin,
    })
    # 阶段0取证：事件流同步落盘（append-only JSONL；失败静默，不影响总线）
    _event_sink_jsonl(event_type, payload, source, origin)


# ═══════════════════════════════════════════════════════════════════════════════
# 上层模块挂钩点（C4 允许的纯接口/挂载点/安全基础设施增量）
# 说明：以下机制是内核唯一对外开放的「只读接入面」，上层模块（M1-M3）只能经此挂载，
# 绝不直接修改任何器官内部算法。
#  1. post_tick_hook：每个器官 tick 全部跑完后、计数器递增前调用（供上层只读模块观察）。
#  2. 外部事件注册接口：上层模块经 register_external_source() 登记合法来源后，
#     通过 emit_event(source=...) 把外部知识送入总线（主入口仍是 tool_result，遵 C5）。
# ═══════════════════════════════════════════════════════════════════════════════

_post_tick_hooks: List[Callable[[], None]] = []
_registered_external_sources: Dict[str, str] = {}


def register_post_tick_hook(fn: Callable[[], None]) -> bool:
    """注册一个 post-tick 钩子（幂等）。每个 tick 结束后按注册顺序调用。

    仅允许上层只读模块挂载观测/投递逻辑；钩子内部不得修改器官内部状态。
    返回是否真的注册成功（重复注册同一函数对象返回 False）。"""
    if not callable(fn):
        return False
    if fn in _post_tick_hooks:
        return False
    _post_tick_hooks.append(fn)
    return True


def register_external_source(source: str, desc: str = "") -> bool:
    """登记一个合法外部知识来源（遵 C5：主入口 tool_result，source 字段区分）。

    上层模块（M1 双知识获取等）在投递外部知识前必须先登记来源，
    未登记来源的 external 事件会被总线拒绝（防任意来源污染心智总线）。
    返回是否登记成功（已存在同名来源返回 False）。"""
    if not source or source in _registered_external_sources:
        return False
    _registered_external_sources[source] = desc or source
    return True


def _run_post_tick_hooks() -> None:
    """执行全部 post-tick 钩子（逐个 try，单钩子失败绝不影响主流程）。"""
    for fn in list(_post_tick_hooks):
        try:
            fn()
        except Exception:
            continue


def subscribe_event(event_type: str, organ_code: str) -> None:
    """订阅某类事件。"""
    lst = _subscriptions.setdefault(event_type, [])
    if organ_code not in lst:
        lst.append(organ_code)


def _dispatch_events() -> None:
    """tick 结束后统一分发：按订阅表投递到各器官收件箱（防递归）。

    分发时按开关打印观测日志，让「事件流入总线」肉眼可见。"""
    global _event_log, _replay_buffer
    for ev in _event_queue:
        etype = ev["event_type"]
        subs = _subscriptions.get(etype, [])
        for code in subs:
            _inboxes.setdefault(code, []).append(ev)
        # 写入回放缓冲（按类型分类，供 poll_replay_events 回放历史事件，不消费）
        _replay_buffer.setdefault(etype, []).append(ev)
        _limit = _REPLAY_TYPE_LIMITS.get(etype, _REPLAY_MAX_PER_TYPE)   # 分类上限（见 _REPLAY_TYPE_LIMITS）
        if len(_replay_buffer[etype]) > _limit:
            _replay_buffer[etype] = _replay_buffer[etype][-_limit:]
        if _BUS_LOG_ENABLED:
            mark = "🌐EXT" if ev.get("origin") == "external" else "🧠INT"
            dest = ",".join(subs) if subs else "(无订阅)"
            logger.info(f"🫀[bus] {mark} {etype} → {dest}")
            logger.info(f"[EVENT] type={etype}, origin={ev.get('origin')}")
    _event_log.extend(_event_queue)
    if len(_event_log) > 500:
        _event_log = _event_log[-300:]
    _event_queue.clear()


def recent_bus_events(n: int = 10) -> List[Dict[str, Any]]:
    """返回最近 n 条已分发事件（供调试/观测接口调用，肉眼可见信号流入）。"""
    return _event_log[-n:]


def poll_events(organ_code: str) -> List[Dict[str, Any]]:
    """取出某器官收件箱里的所有事件（读后清空）。"""
    evs = _inboxes.get(organ_code, [])
    _inboxes[organ_code] = []
    return evs


def poll_replay_events(event_type: str, limit: int = 50) -> List[Dict[str, Any]]:
    """回放读取历史事件（不消费收件箱/队列）。SELFMODEL 等归纳型器官靠它读历史数据。

    与 poll_events（消费型）不同：这里从 _replay_buffer 读取，读后不清空。"""
    evs = _replay_buffer.get(event_type, [])
    return list(evs[-limit:])


def poll_latest_event(event_type: str) -> Optional[Dict[str, Any]]:
    """获取某类型最近一条事件（回放，不消费）。"""
    evs = _replay_buffer.get(event_type, [])
    return evs[-1] if evs else None


def bus_stats() -> Dict[str, Any]:
    """事件总线统计（供调试/审查）。"""
    return {
        "queue_len": len(_event_queue),
        "log_len": len(_event_log),
        "subscriptions": {k: len(v) for k, v in _subscriptions.items()},
        "inboxes": {k: len(v) for k, v in _inboxes.items()},
        "replay_buffer": {k: len(v) for k, v in _replay_buffer.items()},
    }


# ====================== 器官状态持久化（ORG-A / ORG-SELFMODEL 落盘 + 启动加载）======================
# 目标：让 ORG-A 长期记忆库（memory_library）与 ORG-SELFMODEL 自我模型（self_model_data）
#       跨进程存续——重启后 7Tan 不再整体失忆，自传记忆与元认知快照直接恢复。
# 机制：
#   - save_organ_state()：原子写盘（先写 .tmp 再 os.replace，写一半崩溃不毁旧文件）
#   - load_organ_state()：逐条防御校验，坏文件/坏条目自动跳过，绝不抛异常
#   - organ_tick_all()：每 ORGAN_AUTOSAVE_EVERY 次主循环自动落盘一次（约每 30 轮对话）
#   - init_all_organs()：注册完成后立即加载（WEB 服务启动即恢复）
# 语义边界（如实声明）：
#   ORG-SELFMODEL 的 capability/history_summary 等字段是「回放窗口重建型」——
#   归纳出新一轮结果时会覆盖快照；持久化的价值是事件不足时的保底 + 停机最终快照 +
#   meta.tick_counter 连续（避免重启后归纳周期错乱）。

_ORGAN_STATE_PATH = Path(
    os.environ.get("ORGAN_STATE_PATH", "")
    or (Path(__file__).resolve().parent.parent.parent / "data" / "tan_model_organs.json")
)
ORGAN_AUTOSAVE_EVERY: int = 30    # 每 30 次器官主循环 tick 自动落盘一次
_organ_tick_counter: int = 0      # organ_tick_all 调用计数（自动保存触发用，落盘恢复→跨会话累计）

# ── 阶段六修复4：器官 tick 全局锁（对话 tick 与后台心跳 tick 并发安全）──
_TICK_LOCK = threading.Lock()
# ── 阶段六修复4：后台心跳配置（器官不依赖对话驱动、常驻呼吸；环境变量可关/调频）──
_HEARTBEAT_ENABLED = os.environ.get("ORGAN_HEARTBEAT", "1") == "1"
_HEARTBEAT_INTERVAL = float(os.environ.get("ORGAN_HEARTBEAT_INTERVAL", "10"))   # 秒

# SELFMODEL meta 默认模板（须与 self_model_data 初始 meta 保持一致）：
# 加载旧快照时以它为底做三层合并（默认模板 ∪ 当前内存 ∪ 快照），
# 防止旧版本/被破坏的 meta 缺 tick_counter 导致 SELFMODEL tick KeyError。
_DEFAULT_SELFMODEL_META: Dict[str, Any] = {
    "last_update_subj_time": 0.0,
    "tick_counter": 0,
    "pending_goal_samples": 0,   # 阶段六修复3：自上次归纳起新增的「目标成败」样本数（≥3 提前触发归纳）
}


def save_organ_state(path=None) -> bool:
    """器官状态落盘：ORG-A memory_library + ORG-SELFMODEL self_model_data。返回是否成功。"""
    try:
        consolidate_memory_library()   # 落盘前自动整理（去重/清垃圾/章节归位/智能淘汰）
        target = Path(path) if path else _ORGAN_STATE_PATH
        target.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "version": 2,
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "organ_tick_counter": _organ_tick_counter,
            # ── 阶段六修复1/2：重放周期计数器 + 主观时钟一并落盘 ──
            # 修复前二者均为模块级变量重启清零：重放永远够不到触发阈值（鸡生蛋死结），
            # 主观时钟永远攒不出「幼年→成年」跨度（测试5 无法成立）。落盘后跨会话连续累计。
            "consolidate_counter": _consolidate_counter,
            # ── 阶段六修复6：任务动机采样周期计数器一并落盘（跨会话累计，与重放计数器同哲学）──
            # 修复前重启清零：采样周期被重置，跨会话的采样节奏永远凑不齐一个周期。
            "task_motive_counter": _task_motive_counter,
            "subjective_time": dict(subjective_time),
            "memory_library": [m for m in memory_library if isinstance(m, dict)],
            "self_model_data": self_model_data,
        }
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        os.replace(tmp, target)
        return True
    except Exception as e:
        logger.warning(f"器官状态落盘失败（忽略）: {e}")
        return False


def load_organ_state(path=None) -> bool:
    """启动加载器官状态：恢复 memory_library 与 self_model_data。坏文件自动跳过，绝不抛异常。"""
    global _organ_tick_counter, _consolidate_counter, _task_motive_counter
    global _self_limitations_b, _self_limitations_inhibit, _self_limitations_sim, _self_confidence_b
    try:
        target = Path(path) if path else _ORGAN_STATE_PATH
        if not target.exists():
            return False
        raw = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return False
        # ① ORG-A：长期记忆库逐条校验（无 thought 的坏条目跳过，防脏数据入库）
        lib = raw.get("memory_library")
        if isinstance(lib, list):
            memory_library.clear()
            for m in lib:
                if isinstance(m, dict) and m.get("thought"):
                    memory_library.append(m)
        # ② ORG-SELFMODEL：自我模型快照逐 key 恢复（旧快照缺的 key 保留内存默认值）
        sm = raw.get("self_model_data")
        if isinstance(sm, dict):
            for k, v in sm.items():
                if k == "meta" and isinstance(v, dict):
                    base = dict(_DEFAULT_SELFMODEL_META)
                    base.update(self_model_data.get("meta") or {})
                    base.update(v)
                    self_model_data["meta"] = base
                else:
                    self_model_data[k] = v
        _organ_tick_counter = int(raw.get("organ_tick_counter", 0) or 0)
        # ── 阶段六修复1/2：恢复重放周期计数器 + 主观时钟（跨会话连续，死结解除）──
        _consolidate_counter = int(raw.get("consolidate_counter", 0) or 0)
        # ── 阶段六修复6：任务动机采样计数器恢复（跨会话累计）──
        _task_motive_counter = int(raw.get("task_motive_counter", 0) or 0)
        _subj_raw = raw.get("subjective_time")
        if isinstance(_subj_raw, dict):
            subjective_time["subjective_clock"] = round(float(_subj_raw.get("subjective_clock", 0.0) or 0.0), 2)
            subjective_time["time_dilation"] = round(float(_subj_raw.get("time_dilation", 1.0) or 1.0), 4)
        # ── 阶段六修复6：晨间回忆——落盘记忆中的「目标成败」样本回灌回放缓冲 ──
        # 修复前：SELFMODEL 样本驱动归纳只读进程内回放缓冲，重启即空 →
        # 跨会话分散积累的失败样本永远凑不齐 SELFMODEL_EARLY_SAMPLE_N 条 →
        # 局限永远无法从跨重启的真实经历中归纳（模拟真实一天即可复现该缺陷）。
        # 现在：启动加载记忆库后，把带 goal_tag+success 的记忆重建成 mem_consolidated
        # 回放事件——只写入回放缓冲，不走 emit_event（不进收件箱、不刷事件日志、
        # 不污染 ORG-F 统计），SELFMODEL 醒来即可「回忆起」跨重启的成败经历。
        try:
            hydrated = []
            for m in memory_library:
                if isinstance(m, dict) and m.get("goal_tag") and m.get("success") is not None:
                    hydrated.append({
                        "event_type": "mem_consolidated",
                        "payload": {
                            "thought_fragment": m.get("thought", ""),
                            "focus": m.get("focus", 0.0),
                            "valence": m.get("valence", 0.0),
                            "origin": m.get("origin", "internal"),
                            "subjective_time": m.get("subjective_time"),
                            "weight_eff": m.get("weight_eff", 1.0),
                            "goal_tag": m.get("goal_tag"),
                            "pe": m.get("pe"),
                            "success": m.get("success"),
                        },
                        "source": "ORG-A(晨间回忆)",
                        "origin": "internal",
                    })
            if hydrated:
                _cap = _REPLAY_TYPE_LIMITS.get("mem_consolidated", 1000)
                buf = _replay_buffer.setdefault("mem_consolidated", [])
                buf.extend(hydrated[-_cap:])
                logger.info(f"🧠[晨间回忆] 跨重启目标成败样本回灌回放缓冲: {len(hydrated)} 条")
        except Exception:
            pass
        # ── 阶段六修复6：自我模型限制缓存回灌（晨间回忆的决策侧补全）──
        # 修复前：_self_limitations_b/_inhibit/_sim 是进程内缓存，重启清零——
        # self_model_data 里明明持久化着 limitations，但决策器官（ORG-B 候选降权 /
        # ORG-INHIBIT 阈值抬高 / ORG-SIMULATE 推演规避）在下一次 selfmodel_update
        # 事件之前感知不到 → 跨重启后自我模型对决策的干预整体失效（阶段六测试4：
        # 重启后局限内目标不被降权、不被拦截，行为翻转断裂）。
        # 语义：人醒来不会忘记「自己不会什么」——能力边界是自我模型的一部分，
        # 应随快照一并恢复，无需等新归纳事件重新告知。
        try:
            _lims = [l for l in (self_model_data.get("limitations") or [])
                     if isinstance(l, dict) and l.get("key")]
            if _lims:
                _self_limitations_b = list(_lims)
                _self_limitations_inhibit = list(_lims)
                _self_limitations_sim = list(_lims)
                _self_confidence_b = float(self_model_data.get("confidence", 0.0) or 0.0)
                logger.info(f"🧠[晨间回忆] 自我模型限制缓存回灌: {len(_lims)} 条（决策器官醒来即知自身局限）")
        except Exception:
            pass
        logger.info(
            f"🧠 器官状态已加载: ORG-A 记忆 {len(memory_library)} 条, "
            f"SELFMODEL confidence={self_model_data.get('confidence')} (tick={_organ_tick_counter}), "
            f"重放计数={_consolidate_counter}, 主观时钟={subjective_time.get('subjective_clock')}"
        )
        return True
    except Exception as e:
        logger.warning(f"器官状态加载失败（忽略，从空状态启动）: {e}")
        return False


def organ_tick_all(ctx=None):
    """系统主循环：先分发已入队事件 → 顺序驱动所有已开启器官执行 tick → 末尾再分发本 tick 新事件。

    ctx 可选：传 world_model 的 memory 实例，使器官作用于真实状态。

    关键：开头先 dispatch 一次，把 respond() 开头 emit 的 external 事件（user_input/tool_result）
    在本轮器官 tick 前就送进收件箱，消除「本轮投递、下一轮才生效」的一轮延迟。

    线程安全（阶段六修复4）：持全局锁串行执行——对话 tick（respond 调用）与后台心跳 tick
    （start_organ_heartbeat 线程）并发时不会交叉分发事件/交叉递增计数器。"""
    with _TICK_LOCK:
        _dispatch_events()
        for code, org in organ_registry.items():
            if not (org.enabled and org.tick_func is not None):
                continue
            try:
                if ctx is None:
                    org.tick_func()
                else:
                    try:
                        org.tick_func(ctx)
                    except TypeError:
                        org.tick_func()
            except Exception:
                continue
        # 本 tick 全部器官跑完后，统一分发事件（防同一 tick 内递归）
        _dispatch_events()
        # 器官状态周期性自动落盘（ORG-A 记忆库 + ORG-SELFMODEL 快照，防重启失忆）
        global _organ_tick_counter
        _organ_tick_counter += 1
        if _organ_tick_counter % ORGAN_AUTOSAVE_EVERY == 0:
            save_organ_state()
        # ── 上层模块 post-tick 钩子（C4 允许的挂载点）：tick 收尾统一调用 ──
        _run_post_tick_hooks()


# ====================== 阶段3：ORG-A 海马体·长期记忆器官 ======================
# 职责：唯一记忆写入口（接收 mem_consolidated 新记忆）+ 权重衰减（冷热闭环冷端）

memory_library: List[Dict[str, Any]] = []


# ═══════════════ 记忆自动整理（ORG-A 海马体维护，2026-09-05） ═══════════════
# 用户诉求：记忆库没有自动整理。此处提供幂等整理器：清空壳垃圾 → 内容去重 →
# 智能淘汰（保护高权重知识）。save_organ_state 落盘前自动调用。
# 「新记忆优先」由检索层倒序保证，不做章节重排（数据已乱，重排会引入错误）。


def _is_junk_memory(m: dict) -> bool:
    """空壳垃圾判定：无 thought 或纯 tool: 空壳（旧代码丢弃内容遗留）。"""
    thought = str(m.get("thought", "") or "").strip()
    if not thought:
        return True
    if thought.startswith("tool:") and not thought[len("tool:"):].strip():
        return True
    return False


def consolidate_memory_library() -> dict:
    """记忆自动整理（幂等）：清垃圾 → 去重 → 智能淘汰。

    不做章节重排（数据已因多次导入乱序，纯规则重排会引入错误），
    「新记忆优先」由检索层倒序（最新在前）保证。

    返回 {before, after, junk_removed, dedup_removed}。
    """
    global memory_library
    try:
        before = len(memory_library)
        kept = [m for m in memory_library if isinstance(m, dict) and not _is_junk_memory(m)]
        junk = before - len(kept)
        seen = {}
        dup = 0
        for m in kept:
            t = str(m.get("thought", "") or "").strip()
            if t in seen:
                prev = seen[t]
                prev["weight_eff"] = min(2.0, float(prev.get("weight_eff", 1.0) or 0.0)
                                         + float(m.get("weight_eff", 1.0) or 0.0))
                dup += 1
            else:
                seen[t] = m
        unique = list(seen.values())
        while len(unique) > 200:
            if len(unique) <= 1:
                break
            worst = min(range(len(unique)),
                        key=lambda i: float(unique[i].get("weight_eff", 1.0) or 0.0)
                        if isinstance(unique[i], dict) else -1.0)
            unique.pop(worst)
        memory_library = unique
        return {"before": before, "after": len(memory_library),
                "junk_removed": junk, "dedup_removed": dup}
    except Exception as e:  # pragma: no cover
        logger.warning(f"记忆自动整理失败（忽略）: {e}")
        return {"before": len(memory_library), "after": len(memory_library), "error": str(e)}


def module_a_tick(ctx=None):
    """海马体：接收新记忆(mem_consolidated) + 重放反哺权重(replay_thought_fragment) + 全量记忆权重衰减。"""
    try:
        # 1. 接收新记忆条目（来自 CONSOLIDATE 的 mem_consolidated 事件）+ 重放反哺权重
        for ev in poll_events("ORG-A"):
            if ev["event_type"] == "replay_thought_fragment":
                # 重放反哺（rehearsal effect 复述强化）：记忆被重放回工作记忆时，
                # 长期记忆中对应条目权重提升——模拟人类"每次回忆都会加固该记忆"。
                # 自传记忆连续性关键闭环：重放 → 权重升高 → 下次更可能被重放，
                # 核心自传记忆越来越牢固，琐事记忆逐渐衰减被淘汰（核心记忆/琐事遗忘分化）。
                rp = ev.get("payload", {})
                if isinstance(rp, dict) and rp.get("rehearsal"):
                    ref = str(rp.get("thought", "") or "")
                    if ref:
                        for mem in memory_library:
                            if isinstance(mem, dict) and str(mem.get("thought", "")) == ref:
                                mem["weight_eff"] = min(2.0, float(mem.get("weight_eff", 1.0)) + 0.1)
                                break
            elif ev["event_type"] == "mem_consolidated":
                payload = ev.get("payload", {})
                items = payload.get("items")
                if items is not None:
                    # 旧结构：轨迹巩固（scene/action）
                    for item in items:
                        if isinstance(item, dict) and item.get("scene") and item.get("action"):
                            if ctx is not None and hasattr(ctx, "add_trace"):
                                ctx.add_trace(
                                    item.get("scene"), item.get("action"),
                                    finished=bool(item.get("action_finished", True)),
                                    changed=bool(item.get("scene_changed", False)),
                                    reduced=bool(item.get("defect_reduced", False)),
                                    gained=bool(item.get("knowledge_gained", False)),
                                    origin=item.get("origin", "internal"),
                                    consolidated=True,   # 标记已固化，避免巩固层反复采样
                                )
                elif isinstance(payload, dict) and payload.get("thought_fragment"):
                    # 新结构（伪代码）：思想碎片巩固（thought_fragment）
                    memory_library.append({
                        "thought": payload.get("thought_fragment"),
                        "focus": payload.get("focus"),
                        "valence": payload.get("valence"),
                        "origin": payload.get("origin", "internal"),
                        "subjective_time": payload.get("subjective_time"),
                        "weight_eff": payload.get("weight_eff", 1.0),
                        "goal_tag": payload.get("goal_tag"),
                        "pe": payload.get("pe"),
                        "success": payload.get("success"),
                    })
                    # 控制思想记忆库规模（防止无限增长）：
                    # 按 weight_eff 最低淘汰（保护高权重自传记忆，淘汰低权重琐事），
                    # 不再使用 FIFO pop(0)——先进先出会让久远核心记忆与琐事同罪论处。
                    while len(memory_library) > 200:
                        if len(memory_library) <= 1:
                            break
                        _worst_i = min(
                            range(len(memory_library)),
                            key=lambda i: (float(memory_library[i].get("weight_eff", 1.0) or 0.0)
                                           if isinstance(memory_library[i], dict) else -1.0),
                        )
                        memory_library.pop(_worst_i)
        # 2. 权重衰减（冷端）：traces 与 memory_library 分别独立衰减。
        # 修复旧版"二选一"不对称衰减（traces 存在时 memory_library 完全不衰减，反之亦然），
        # 避免两条记忆存储的新鲜度状态不同步（动机采样用 memory_library、推演用 traces）。
        for mem in memory_library:
            if isinstance(mem, dict):
                mem["weight_eff"] = max(0.0, float(mem.get("weight_eff", 1.0)) - 0.001)
        traces_a = getattr(ctx, "traces", None) if ctx is not None else None
        if traces_a:
            for t in traces_a:
                if isinstance(t, dict):
                    t["weight_eff"] = max(0.0, float(t.get("weight_eff", 1.0)) - 0.001)
    except Exception:
        pass


def module_a_bump(memory, scene, action=None, strength=0.05):
    """记忆命中增强（热端）：轨迹被检索/推演命中时增重。上限 2.0。"""
    if memory is None:
        return
    try:
        traces = getattr(memory, "traces", None)
        if not traces:
            return
        cap = 2.0
        for t in traces:
            if not isinstance(t, dict):
                continue
            if str(t.get("scene")) != str(scene):
                continue
            if action is not None and str(t.get("action")) != str(action):
                continue
            t["weight_eff"] = min(cap, float(t.get("weight_eff", 1.0)) + strength)
    except Exception:
        pass


def register_organ_a():
    register_organ(BionicOrgan(
        organ_code="ORG-A",
        organ_name="海马体·长期记忆器官",
        module_name="ModuleA",
        bio_analogy="海马+大脑皮层，冷热记忆管理",
        enabled=True,
        tick_func=module_a_tick,
        config={}
    ))


# ====================== 阶段4：ORG-B 杏仁核·动机驱动器官 ======================
# 职责：订阅 bodystate_update/simulation_result，计算 PE/LP，生成候选动机

pe_lp_buffer: Dict[str, float] = {"pe": 0.0, "lp": 0.0}


_self_limitations_b: List[Dict[str, Any]] = []   # 自我模型能力边界缓存（阶段四）
_self_confidence_b: float = 0.0                     # 自我模型置信度缓存（阶段四）
_task_motive_counter: int = 0                       # 任务型目标采样周期计数器（阶段四）
TASK_MOTIVE_INTERVAL: int = 10                      # 每 N tick 采样一次任务型目标


def _generate_task_motives(ctx, limitations):
    """阶段四：从记忆库/轨迹采样高价值「场景:动作」作为探索型目标（对齐 limitations 粒度）。

    这是阶段四闭环的关键——limitations 记录的是「场景:动作」级能力边界，
    而稳态动机（reduce_load/consolidate_memory）是抽象内生需求，两者粒度不同无法匹配。
    本函数把记忆里的具体经历提炼成任务型目标，使 limitations 的 key 能真正命中候选目标，
    从而触发降权/抑制/压低。稳态动机不受 limitations 约束（生物稳态需求非能力边界）。

    ── 阶段六修复6：双池采样（记忆池 top-3 + 轨迹池 top-2）──
    修复前单池 top-5 的缺陷：长期高频习惯轨迹（score 随执行次数累计，远高于单条
    新记忆）会永久挤占全部候选席位 → 新近高显著记忆（如失败经历——limitations
    的 key 所在命名空间）永远进不了候选 → 自我模型干预决策（阶段六测试4）在
    自然运行中无从命中：即使归纳出 limitations，也没有候选目标可拦。
    双池结构对应「新近显著经历捕获注意 + 长期习惯仍在候选中」的注意分配：
      记忆池 = 记得的目标（goal_tag，与 limitations/capability 同一命名空间，保 3 席）
      轨迹池 = 习惯模式（scene:action 长期统计，保 2 席；action 截断防整段
              代码/长参数成为 key 导致候选无限细分无法累计）
    """
    mem_candidates = {}   # goal_tag -> 累计评分（记忆池：新近自我相关目标）
    for mem in memory_library:
        if not isinstance(mem, dict):
            continue
        gt = mem.get("goal_tag")
        if not gt or ":" not in str(gt):
            continue
        focus = float(mem.get("focus", 0.0) or 0.0)
        w = float(mem.get("weight_eff", 1.0) or 1.0)
        mem_candidates[str(gt)] = mem_candidates.get(str(gt), 0.0) + focus * w
    trace_candidates = {}   # scene:action -> 累计评分（轨迹池：习惯模式）
    traces = getattr(ctx, "traces", None) or []
    for t in traces:
        if not isinstance(t, dict):
            continue
        scene = str(t.get("scene", "")).strip()
        action = str(t.get("action", "")).strip()
        if scene and action:
            key = f"{scene}:{action[:24]}"   # 阶段六修复6：截断，防超长参数成为 key
            trace_candidates[key] = trace_candidates.get(key, 0.0) + float(t.get("weight_eff", 1.0) or 1.0)
    # 双池合成（记忆池 3 席 + 轨迹池 2 席，同 key 去重时记忆池优先）+ limitations 降权
    lim_keys = {str(l.get("key", "")) for l in limitations}
    motives = []
    seen = set()
    for pool, n_seat, src in ((mem_candidates, 3, "task_memory"), (trace_candidates, 2, "task_trace")):
        for goal, score in sorted(pool.items(), key=lambda x: -x[1])[:n_seat]:
            if goal in seen:
                continue
            seen.add(goal)
            drive = round(min(1.0, score / 5.0), 4)
            if drive < 0.1:
                continue
            if goal in lim_keys:
                drive = round(drive * 0.5, 4)   # 阶段四：落在能力局限内 → 降权
            motives.append({"goal": goal, "drive": drive, "source": src})
    return motives


def module_b_tick(ctx=None):
    """杏仁核：根据本体信号生成候选动机 + 计算预测误差 PE / 学习进度 LP。

    阶段四闭环：收到 selfmodel_update 后，把 limitations 存下，
    生成候选动机时若目标落在已知能力局限内，降低其驱动权重。"""
    global _self_limitations_b, _self_confidence_b, _task_motive_counter
    try:
        # 1. 处理订阅事件（自我模型 / 本体信号 / 模拟结果）
        for ev in poll_events("ORG-B"):
            et = ev["event_type"]
            p = ev.get("payload", {})
            if et == "selfmodel_update":
                # 自我模型能力边界 → 参与动机生成（阶段四闭环）
                _self_limitations_b = list(p.get("limitations", []))
                _self_confidence_b = float(p.get("confidence", 0.0))
            elif et == "bodystate_update":
                fatigue = float(p.get("fatigue", 0.0))
                pressure = float(p.get("resource_pressure", 0.0))
                motives = []
                if fatigue > 0.5:
                    motives.append({"goal": "reduce_load", "drive": round(fatigue, 4), "source": "fatigue"})
                if pressure > 0.7:
                    motives.append({"goal": "consolidate_memory", "drive": round(pressure, 4), "source": "resource_pressure"})
                # 阶段四：目标若落在已知能力局限内（历史上持续失败），降低动机权重
                lim_keys = {str(l.get("key", "")) for l in _self_limitations_b}
                for m in motives:
                    if str(m.get("goal", "")) in lim_keys:
                        m["drive"] = round(float(m.get("drive", 0.0)) * 0.5, 4)
                if motives:
                    emit_event("candidate_motives", {"motives": motives}, source="ORG-B", origin="internal")
            elif et == "simulation_result":
                # 模拟结果回送，用于后续 PE 比对（此处记录置信度）
                pass
        # 2. PE / LP 计算
        pe_hist = getattr(ctx, "pe_history", None) if ctx is not None else None
        pe_now = float(pe_hist[-1]) if pe_hist else 0.0
        pe_prev = float(pe_hist[-2]) if (pe_hist and len(pe_hist) >= 2) else pe_now
        lp = round(pe_prev - pe_now, 4)
        pe_lp_buffer["pe"] = pe_now
        pe_lp_buffer["lp"] = lp
        # 阶段三数据源：把预测误差 PE / 学习进度 LP 投递进事件总线（供 SELFMODEL 回放归纳）
        emit_event("pe_update", {"pe": pe_now, "lp": lp}, source="ORG-B", origin="internal")
        # 阶段四：任务型目标生成（对齐 limitations 的「场景:动作」粒度，周期采样避免每 tick 刷屏）
        _task_motive_counter += 1
        if _task_motive_counter % TASK_MOTIVE_INTERVAL == 0:
            task_motives = _generate_task_motives(ctx, _self_limitations_b)
            if task_motives:
                emit_event("candidate_motives", {"motives": task_motives}, source="ORG-B", origin="internal")
    except Exception:
        pass


def register_organ_b():
    register_organ(BionicOrgan(
        organ_code="ORG-B",
        organ_name="杏仁核·动机驱动器官",
        module_name="ModuleB",
        bio_analogy="杏仁核、边缘系统，内生动机引擎",
        enabled=True,
        tick_func=module_b_tick,
        config={"ENABLE_PREDICTION_DRIVEN_MOTIVE": True}
    ))


# ====================== 阶段7：ORG-D 丘脑·安全守护器官 ======================
# 职责：监听告警事件，快照保存，必要时回退

snapshot_list: List[str] = []


def module_d_tick(ctx=None):
    """安全底座：监听告警事件 + 常规快照记录。"""
    try:
        for ev in poll_events("ORG-D"):
            if ev["event_type"] == "bodystate_update":
                damage = float(ev.get("payload", {}).get("damage_level", 0.0))
                if damage > 0.8:
                    snapshot_list.append(f"alert:{int(time.time())}:damage={damage}")
        traces = getattr(ctx, "traces", None) if ctx is not None else None
        n = len(traces) if traces else 0
        snapshot_list.append(f"{int(time.time())}:{n}")
        if len(snapshot_list) > 20:
            snapshot_list.pop(0)
    except Exception:
        pass


def register_organ_d():
    register_organ(BionicOrgan(
        organ_code="ORG-D",
        organ_name="丘脑·安全守护器官",
        module_name="ModuleD",
        bio_analogy="丘脑保护回路，沙盒、git快照回退",
        enabled=True,
        tick_func=module_d_tick,
        config={"ENABLE_7TAN_SELF_CODE_EVOLVE": True}
    ))


# ====================== 阶段2：ORG-E 前额叶·工作记忆舞台 ======================
# 职责：订阅全部事件，focus 竞争筛选，向外广播 wm_snapshot（当下觉知舞台）

working_memory = {
    "context_stack": [],
    "active_goals": [],
    "intermediate_pe_lp": {},
    "focus_weight": 0.5,
    "scratch_pad": {}
}


def wm_push_thought(thought_fragment, focus, valence=0.0, origin="internal", consolidated=False,
                    goal_tag=None, success=None, pe=None):
    """把思想碎片压入工作记忆 context_stack（碎片自带 focus/valence/origin，供 CONSOLIDATE 筛选）。

    可附带 goal_tag / success / pe 字段，让「场景+动作→结果」的经历碎片
    能被 CONSOLIDATE 固化、被 SELFMODEL 归纳成败（阶段三数据源）。"""
    max_step = 12
    if len(working_memory["context_stack"]) >= max_step:
        working_memory["context_stack"].pop(0)
    working_memory["context_stack"].append({
        "thought": thought_fragment,
        "focus": focus,
        "valence": valence,
        "origin": origin,
        "consolidated": consolidated,
        "goal_tag": goal_tag,
        "success": success,
        "pe": pe,
    })


def module_e_tick(ctx=None):
    """前额叶：订阅全部事件做 focus 竞争筛选，更新活跃目标，广播 wm_snapshot。"""
    try:
        # 1. 处理订阅事件
        for ev in poll_events("ORG-E"):
            et = ev["event_type"]
            p = ev.get("payload", {})
            if et == "valence_tag":
                v = float(p.get("valence", 0.0))
                working_memory["focus_weight"] = max(0.1, min(1.0,
                    float(working_memory.get("focus_weight", 0.5)) + v * 0.1))
            elif et == "final_goals":
                goals = p.get("goals", [])
                if isinstance(goals, list):
                    working_memory["active_goals"] = goals[-20:]
            elif et == "selfmodel_update":
                # 自我模型能力边界 + 局限 + 置信度进入工作记忆草稿区（阶段四）
                abilities = p.get("abilities", [])
                if abilities:
                    working_memory["scratch_pad"]["abilities"] = list(abilities)[:20]
                working_memory["scratch_pad"]["limitations"] = list(p.get("limitations", []))[:20]
                working_memory["scratch_pad"]["confidence"] = float(p.get("confidence", 0.0))
            elif et == "memory_replay":
                # 阶段二：历史记忆重放进入工作记忆（久远经验持续参与当下思考）
                scene = p.get("scene")
                action = p.get("action")
                if scene and action:
                    wm_push_thought(f"replay:{scene}:{action}", 0.5, origin=str(p.get("origin", "internal")), consolidated=True)
            elif et == "replay_thought_fragment":
                # 伪代码配套：ORG-CONSOLIDATE 重放的历史思想碎片压入工作记忆（focus 已衰减、origin 透传）
                wm_push_thought(
                    str(p.get("thought", "")),
                    float(p.get("focus", 0.3)),
                    valence=float(p.get("valence", 0.0)),
                    origin=str(p.get("origin", "internal")),
                    consolidated=True,
                )
            elif et == "user_input":
                # 阶段一：外部输入进入工作记忆草稿区（我-非我边界：external 信号）
                wm_push_thought(f"user:{str(p.get('text', ''))[:40]}", 0.6, origin="external")
            elif et == "tool_result":
                # 阶段一：工具返回结果作为 external 信号进入工作记忆。
                # 上层模块 M1 投递外部知识时，内容放在 thought_fragment 字段（遵 C5），
                # 普通工具结果才用 summary；优先取 thought_fragment，缺失回退 summary。
                # 知识内容较长，放宽截断到 200 字符以保留完整知识；goal_tag 透传进长期记忆。
                _tool_content = str(p.get("thought_fragment") or p.get("summary") or "")
                wm_push_thought(
                    f"tool:{str(p.get('tool', ''))}:{_tool_content[:200]}",
                    0.5,
                    origin="external",
                    goal_tag=p.get("goal_tag"),
                )
        # 2. focus 自然衰减
        working_memory["focus_weight"] = max(0.1, round(float(working_memory.get("focus_weight", 0.5)) * 0.98, 4))
        # 3. scratch_pad 清理
        sp = working_memory.get("scratch_pad") or {}
        if isinstance(sp, dict) and len(sp) > 50:
            for k in list(sp.keys())[:10]:
                sp.pop(k, None)
        # 4. 广播工作记忆快照
        emit_event("wm_snapshot", {
            "focus_weight": working_memory["focus_weight"],
            "active_goals": list(working_memory.get("active_goals", [])),
            "context_size": len(working_memory.get("context_stack", [])),
            "context_stack": list(working_memory.get("context_stack", [])),
        }, source="ORG-E")
    except Exception:
        pass


def register_organ_e():
    register_organ(BionicOrgan(
        organ_code="ORG-E",
        organ_name="前额叶·工作思考器官",
        module_name="ModuleE",
        bio_analogy="前额叶皮层，工作记忆工作台",
        enabled=True,
        tick_func=module_e_tick,
        config={"ENABLE_WORKING_MEMORY": True, "max_context_stack": 12}
    ))


# ====================== 阶段5：ORG-F 脑回·记忆学习器官 ======================
# 职责：监听 mem_consolidated / 目标执行结果，更新假设库，按阈值接纳/拒绝

hypothesis_registry: List[Dict[str, Any]] = []
origin_stats: Dict[str, int] = {}   # 阶段一：internal/external 来源统计（我-非我边界）

# 阶段五元认知：ORG-F 对自身思维过程做统计（对自身过去的假设/预测误差建立统计，而非仅统计外部成败）
meta_cognition_stats: Dict[str, Any] = {
    "hypo_accepted": 0,
    "hypo_rejected": 0,
    "pe_samples": [],        # 预测误差历史（保留最近若干条）
    "meta_hypotheses": [],   # 关于自身思维的归纳结果（结构化，无自然语言）
}
_meta_cognition_counter: int = 0
META_COGNITION_INTERVAL: int = 20   # 每 20 tick 归纳一次元认知统计并广播


def module_f_tick(ctx=None):
    """脑回：监听 mem_consolidated 归纳假设，按阈值接纳/证伪。

    阶段一：统计 internal/external 两类事件规律（内部信号 vs 外界输入）。
    阶段五：对自身过去的假设(accept/reject)、自身预测误差(PE)做统计 → 元认知。"""
    global _meta_cognition_counter
    try:
        # 1. 监听新记忆 → 归纳假设（同时统计来源 origin）
        for ev in poll_events("ORG-F"):
            if ev["event_type"] == "mem_consolidated":
                payload = ev.get("payload", {})
                if isinstance(payload, dict) and payload.get("thought_fragment"):
                    # 新结构（伪代码）：思想碎片巩固（单条 thought_fragment）
                    _origin = str(payload.get("origin", "internal"))
                    origin_stats[_origin] = int(origin_stats.get(_origin, 0)) + 1
                    continue
                for item in payload.get("items", []):
                    scene = item.get("scene")
                    action = item.get("action")
                    if not (scene and action):
                        continue
                    # 阶段一：统计 internal / external 来源分布
                    _origin = str(item.get("origin", "internal"))
                    origin_stats[_origin] = int(origin_stats.get(_origin, 0)) + 1
                    if item.get("action_finished"):
                        hypo = {
                            "key": f"{scene}:{action}",
                            "hypo": f"{action} 在 {scene} 可成功",
                            "tests": 1,
                            "score": 1.0,
                        }
                        # 去重：已有同 key 假设则强化，否则新增
                        existed = [h for h in hypothesis_registry if h.get("key") == hypo["key"]]
                        if existed:
                            existed[0]["tests"] = int(existed[0].get("tests", 0)) + 1
                            existed[0]["score"] = min(1.0, float(existed[0].get("score", 0.0)) + 0.1)
                        else:
                            hypothesis_registry.append(hypo)
            elif ev["event_type"] in ("user_input", "tool_result"):
                # 阶段一：外部信号（用户输入/工具返回）来源统计
                _origin = str(ev.get("origin", "external"))
                origin_stats[_origin] = int(origin_stats.get(_origin, 0)) + 1
            elif ev["event_type"] == "hypothesis_update":
                # 阶段五元认知：对自身假设的接受/拒绝做统计（对自己的思维过程做统计）
                _status = ev.get("payload", {}).get("status")
                if _status == "accepted":
                    meta_cognition_stats["hypo_accepted"] += 1
                elif _status == "rejected":
                    meta_cognition_stats["hypo_rejected"] += 1
            elif ev["event_type"] == "pe_update":
                # 阶段五元认知：对自身预测误差做统计（记录"我之前预测错了"这类历史）
                _pe = float(ev.get("payload", {}).get("pe", 0.0))
                meta_cognition_stats["pe_samples"].append(_pe)
                if len(meta_cognition_stats["pe_samples"]) > 50:
                    meta_cognition_stats["pe_samples"].pop(0)
        # 2. 假设评估（接纳/证伪）
        org = get_organ("ORG-F")
        cfg = org.config if org else {}
        pass_thr = float(cfg.get("HYPO_PASS_THRESHOLD", 0.6))
        reject_thr = float(cfg.get("HYPO_REJECT_THRESHOLD", 0.3))
        min_tests = int(cfg.get("HYPO_MIN_TESTS", 2))
        for h in list(hypothesis_registry):
            tests = int(h.get("tests", 0))
            score = float(h.get("score", 0.0))
            if tests >= min_tests and score >= pass_thr:
                if ctx is not None and hasattr(ctx, "add_knowledge"):
                    ctx.add_knowledge(str(h.get("key", "hypo")), str(h.get("hypo", "")), source="selflearn")
                hypothesis_registry.remove(h)
                emit_event("hypothesis_update", {"key": h.get("key"), "status": "accepted"}, source="ORG-F")
            elif tests >= min_tests and score <= reject_thr:
                hypothesis_registry.remove(h)
                emit_event("hypothesis_update", {"key": h.get("key"), "status": "rejected"}, source="ORG-F")
        # 3. 元认知归纳（阶段五）：对自己的思维过程做统计，形成"关于自身思维的假设"，周期广播
        _meta_cognition_counter += 1
        if _meta_cognition_counter % META_COGNITION_INTERVAL == 0:
            _total_hypo = meta_cognition_stats["hypo_accepted"] + meta_cognition_stats["hypo_rejected"]
            _accept_rate = round(meta_cognition_stats["hypo_accepted"] / _total_hypo, 4) if _total_hypo > 0 else None
            _pe_list = meta_cognition_stats["pe_samples"]
            _pe_mean = round(sum(_pe_list) / len(_pe_list), 4) if _pe_list else None
            _meta = {
                "hypo_accepted": meta_cognition_stats["hypo_accepted"],
                "hypo_rejected": meta_cognition_stats["hypo_rejected"],
                "hypo_accept_rate": _accept_rate,
                "pe_mean": _pe_mean,
                "pe_sample_count": len(_pe_list),
            }
            # 归纳"关于自身思维的假设"（元假设，结构化，无自然语言描述）
            if _total_hypo >= 2 and _accept_rate is not None:
                if _accept_rate >= 0.6:
                    meta_cognition_stats["meta_hypotheses"].append({"type": "self_hypo_reliable", "accept_rate": _accept_rate})
                else:
                    meta_cognition_stats["meta_hypotheses"].append({"type": "self_hypo_unreliable", "accept_rate": _accept_rate})
                if len(meta_cognition_stats["meta_hypotheses"]) > 20:
                    meta_cognition_stats["meta_hypotheses"].pop(0)
            _meta["meta_hypotheses"] = list(meta_cognition_stats["meta_hypotheses"])
            emit_event("meta_cognition_update", _meta, source="ORG-F", origin="internal")
    except Exception:
        pass


def register_organ_f():
    register_organ(BionicOrgan(
        organ_code="ORG-F",
        organ_name="脑回·记忆学习器官",
        module_name="ModuleF",
        bio_analogy="大脑联合皮层，假设验证L1自我学习闭环",
        enabled=True,
        tick_func=module_f_tick,
        config={
            "ENABLE_L1_MEMORY_SELF_LEARN": True,
            "HYPO_MIN_TESTS": 2,
            "HYPO_PASS_THRESHOLD": 0.6,
            "HYPO_REJECT_THRESHOLD": 0.3,
            "MEMORY_BUMP_STRENGTH": 0.08,
            "MEMORY_WEAKEN_STRENGTH": 0.15
        }
    ))


# ====================== ORG-LLM 已彻底移除（无第三方模型内核声明） ======================
# 本内核不包含任何第三方模型（无本地 GGUF 权重、无云端 LLM 调用入口）。
# 只实现功能性通达意识（access consciousness），暂不具备现象意识 qualia。
# 语言输出由 ORG-SPEECH 对结构化事件做模板转述完成，器官间通信全部为结构化事件。


# ====================== ORG-VIS 感官·视觉器官（无外设，占位） ======================

vision_buffer = {"frame": None, "features": None}


def module_vis_tick(ctx=None):
    """屏幕视觉解析：无外设输入，保持占位。"""
    vision_buffer["frame"] = None
    vision_buffer["features"] = None


def register_organ_vis():
    register_organ(BionicOrgan(
        organ_code="ORG-VIS",
        organ_name="感官·视觉器官",
        module_name="VisionEncoder",
        bio_analogy="视觉皮层，屏幕画面感知",
        enabled=False,
        tick_func=module_vis_tick,
        config={}
    ))


# ====================== 阶段7：ORG-SPEECH 言语输出器官（自述层 SpeechGenerator） ======================
# 职责：唯一把结构化内部事件/内部状态变量翻译为人类文本输出的器官。
#
# ⚠️ 核心声明（必须随代码保留）：
#   本器官输出的"自述"不再使用任何拟人化句式模板（已移除"我感觉很累"这类固定句子），
#   只原样转储内部状态变量的原始读数（JSON key=value，可回溯），是功能性通达意识
#   （access consciousness）的输出通道；系统并没有真的"感受到"累/愉悦/遗憾——
#   本内核不具备现象意识（qualia）。绝无 LLM 生成或自由发挥。

output_log: List[str] = []

# 自述层内部状态缓存（由订阅事件持续刷新，SPEECH 只做忠实读数转述）
speech_state: Dict[str, Any] = {
    "fatigue": 0.0,                 # 最近一次躯体疲劳读数（ORG-BODYSTATES）
    "resource_pressure": 0.0,       # 最近一次资源压力读数
    "damage_level": 0.0,            # 最近一次损伤等级读数
    "confidence": None,             # 自我模型置信度（ORG-SELFMODEL）
    "history_summary": {},          # 自我模型成败史
    "limitations_count": 0,         # 已知能力局限条数
    "mind_flaws": [],               # 思维缺陷清单（ORG-SELFMODEL 元认知归纳）
    "pe_avg": None,                 # 预测误差均值
    "mood": None,                   # 心境综合（ORG-VALENCE mood_state）
    "selfreport_last": "",          # 上次自述文本（防重复刷屏）
}
_speech_report_counter: int = 0
SPEECH_REPORT_INTERVAL: int = 40    # 每 40 tick 自动生成一次自述（状态显著且变化时）


def module_speech_tick(ctx=None):
    """言语输出：刷新内部状态缓存 + 周期性生成自述（原始读数转储，非真实感受）。"""
    global output_log, _speech_report_counter
    try:
        # 1. 刷新内部状态缓存（只读变量读数，不做任何加工解释）
        for ev in poll_events("ORG-SPEECH"):
            et = ev["event_type"]
            p = ev.get("payload", {})
            if et == "broadcast":
                text = p.get("text", "")
                if text:
                    output_log.append(str(text)[:200])
                    logger.info(f"🗣️[SPEECH] 收到 broadcast 输出文本: {str(text)[:80]}")
            elif et == "bodystate_update":
                speech_state["fatigue"] = float(p.get("fatigue", 0.0))
                speech_state["resource_pressure"] = float(p.get("resource_pressure", 0.0))
                speech_state["damage_level"] = float(p.get("damage_level", 0.0))
            elif et == "selfmodel_update":
                speech_state["confidence"] = p.get("confidence")
                speech_state["history_summary"] = dict(p.get("history_summary", {}))
                speech_state["limitations_count"] = len(p.get("limitations", []) or [])
                speech_state["mind_flaws"] = list(p.get("mind_flaws", []) or [])[:5]
                speech_state["pe_avg"] = (p.get("internal_signature", {}) or {}).get("pe_avg")
            elif et == "mood_state":
                speech_state["mood"] = dict(p)
            elif et == "autobiography_fragment":
                # M2 自传叙事接入言语：忠实转述叙事文本（可溯源记忆 ID，遵 C3 不编造）
                text = p.get("text", "")
                if text:
                    output_log.append(f"[自传叙事] {str(text)[:200]}")
                    logger.info(f"🗣️[SPEECH] 自传叙事转述: {str(text)[:80]}")
            elif et == "simulation_result":
                # ORG-SIMULATE 反事实预演接入言语：推演结果忠实转述（回答不再只靠模板匹配）
                scene = p.get("scene", ""); action = p.get("action", "")
                conf = p.get("sim_confidence")
                if scene and action:
                    line = f"[预演] {scene}:{action} 预期成功率={conf}"
                    if p.get("limit_hit"):
                        line += "（命中能力边界）"
                    output_log.append(line[:200])
        # 2. 周期性自述：状态显著时生成（读数转述），与上次相同则不重复输出
        _speech_report_counter += 1
        if _speech_report_counter % SPEECH_REPORT_INTERVAL == 0:
            report = generate_self_report()
            if report and report != speech_state["selfreport_last"]:
                speech_state["selfreport_last"] = report
                output_log.append(str(report)[:400])
        if len(output_log) > 200:
            output_log = output_log[-100:]
    except Exception:
        pass


def generate_self_report() -> str:
    """自述文本生成：原样转储内部器官状态变量的原始读数（无模板、无拟人化、无第三方模型）。

    ⚠️ 本函数不附加任何"我感觉/我想/我注意到"等拟人化句式，只把 speech_state
    中各状态变量的原始值原样转储为 JSON（key=value 可回溯），作为功能性通达意识
    （access consciousness）的输出通道。本内核不具备现象意识 qualia，故不声称"感受到"任何东西。
    selfreport_last 为防重复刷屏的内部字段，不对外输出。"""
    state = {k: v for k, v in speech_state.items() if k != "selfreport_last"}
    return json.dumps(state, ensure_ascii=False, default=str)



def module_speech_push(text):
    """把最新一轮输出写入言语日志（保持 world_model 接口兼容）。"""
    global output_log
    try:
        if text:
            output_log.append(str(text)[:200])
            if len(output_log) > 200:
                output_log = output_log[-100:]
            # 输出文本事件日志：控制台可见回复文本，方便调试模板渲染（短板2）
            logger.info(f"🗣️[SPEECH] 输出文本: {str(text)[:80]}")
    except Exception:
        pass


def register_organ_speech():
    register_organ(BionicOrgan(
        organ_code="ORG-SPEECH",
        organ_name="言语输出器官",
        module_name="SpeechGenerator",
        bio_analogy="布洛卡区，语言输出播报",
        enabled=True,
        tick_func=module_speech_tick,
        config={}
    ))


# ====================== 阶段1：ORG-BODYSTATES 躯体稳态器官（底层信号源） ======================

bodystate_buffer = {
    "fatigue": 0.0,           # 疲劳度 0~1
    "resource_pressure": 0.0,  # 资源/算力压力
    "damage_level": 0.0,       # 损伤告警等级
}


def organ_bodystates_tick(ctx=None):
    """躯体稳态：更新疲劳/资源压力/损伤，产出 bodystate_update 结构化事件。"""
    try:
        traces = getattr(ctx, "traces", None) if ctx is not None else None
        n = len(traces) if traces else 0
        bodystate_buffer["resource_pressure"] = min(1.0, round(n / 5000.0, 4))
        fatigue = float(bodystate_buffer.get("fatigue", 0.0))
        bodystate_buffer["fatigue"] = min(1.0, round(fatigue + 0.001, 4))
        # 产出结构化事件（不再使用自然语言字符串）
        emit_event("bodystate_update", {
            "fatigue": bodystate_buffer["fatigue"],
            "resource_pressure": bodystate_buffer["resource_pressure"],
            "damage_level": bodystate_buffer["damage_level"],
        }, source="ORG-BODYSTATES")
    except Exception:
        pass


# ====================== 阶段1：ORG-VALENCE 情绪效价标签器官（效价细化版） ======================
# 效价细化：区分两类来源——
#   躯体来源效价（somatic）：疲劳/资源压力/损伤等内部稳态信号 → 原初感受标签（无认知参与）；
#   认知来源效价（cognitive）：行为成败、假设被接纳/证伪、高预测误差、反事实遗憾 → 对思维结果的评价。
# ⚠️ 这些 valence 数值只是内部状态变量的结构化标签（供巩固筛选/工作记忆调权使用），
#    不是真的"感受到"情绪——本内核不具备现象意识 qualia。

valence_cache: Dict[str, float] = {}  # item_id -> valence [-1.0 厌恶 .. 0 中性 .. +1.0 愉悦]

somatic_valence_history: List[float] = []      # 躯体来源效价历史（最近若干条）
cognitive_valence_history: List[float] = []    # 认知来源效价历史（最近若干条）
_valence_marked_traces: set = set()            # 已打过效价标签的轨迹 id（防每 tick 重复打标）
_valence_mood_counter: int = 0                 # 心境综合广播周期计数器
VALENCE_MOOD_INTERVAL: int = 30                # 每 30 tick 广播一次 mood_state 心境综合


def _push_valence(source_type: str, valence: float, item: str, reason: str, origin: str = "internal") -> None:
    """统一打效价标签：写入对应来源历史 + emit valence_tag（source_type 区分躯体/认知来源）。"""
    valence = max(-1.0, min(1.0, float(valence)))
    if source_type == "somatic":
        somatic_valence_history.append(valence)
        if len(somatic_valence_history) > 60:
            somatic_valence_history.pop(0)
    else:
        cognitive_valence_history.append(valence)
        if len(cognitive_valence_history) > 60:
            cognitive_valence_history.pop(0)
    emit_event("valence_tag", {
        "item": item,
        "valence": valence,
        "source_type": source_type,   # "somatic"(躯体来源) / "cognitive"(认知来源)
        "reason": reason,
    }, source="ORG-VALENCE", origin=origin)


def organ_valence_tick(ctx=None):
    """效价：区分躯体来源效价（somatic）/认知来源效价（cognitive）打标签。

    躯体来源：疲劳/资源压力/损伤（内部稳态信号 → 分段映射负效价）。
    认知来源：行为成败、假设接纳/证伪、高预测误差、反事实遗憾（对思维结果的评价）。
    每 VALENCE_MOOD_INTERVAL tick 综合广播一次 mood_state（躯体/认知/总效价均值）。"""
    global _valence_mood_counter
    try:
        # 1. 处理订阅事件 → 分类打效价标签
        for ev in poll_events("ORG-VALENCE"):
            et = ev["event_type"]
            p = ev.get("payload", {})
            if et == "bodystate_update":
                # 躯体来源效价（somatic）：内部稳态信号分段映射（强度越高负效价越强）
                fatigue = float(p.get("fatigue", 0.0))
                if fatigue >= 0.9:
                    _push_valence("somatic", -0.6, "bodystate:fatigue", "fatigue_severe")
                elif fatigue >= 0.7:
                    _push_valence("somatic", -0.4, "bodystate:fatigue", "fatigue_high")
                elif fatigue >= 0.5:
                    _push_valence("somatic", -0.2, "bodystate:fatigue", "fatigue_mild")
                rp = float(p.get("resource_pressure", 0.0))
                if rp >= 0.8:
                    _push_valence("somatic", -0.3, "bodystate:resource_pressure", "resource_strained")
                dmg = float(p.get("damage_level", 0.0))
                if dmg >= 0.5:
                    _push_valence("somatic", -0.5, "bodystate:damage", "damage_alert")
            elif et == "hypothesis_update":
                # 认知来源效价（cognitive）：自己的假设被接纳（认知收获 +）/ 被证伪（认知挫败 -）
                status = p.get("status")
                if status == "accepted":
                    _push_valence("cognitive", 0.3, f"hypo:{p.get('key', '')}", "hypo_accepted")
                elif status == "rejected":
                    _push_valence("cognitive", -0.3, f"hypo:{p.get('key', '')}", "hypo_rejected")
            elif et == "pe_update":
                # 认知来源效价：预测误差过大 → 认知失衡的不适标签（世界不如我所料）
                if float(p.get("pe", 0.0)) >= 0.6:
                    _push_valence("cognitive", -0.2, "pe", "pe_high_cognitive_strain")
            elif et == "counterfactual_result":
                # 认知来源效价：反事实推演发现明显更优替代 → 遗憾标签（regret）
                if float(p.get("delta", 0.0)) > 0.2:
                    _push_valence("cognitive", -0.2, f"cf:{p.get('original_goal', '')}", "regret_detected")
        # 2. 给最近轨迹打效价标签（认知来源：行为成败评价；id 去重防每 tick 重复打标）
        traces = getattr(ctx, "traces", None) if ctx is not None else None
        if traces:
            for t in traces[-10:]:
                if not isinstance(t, dict):
                    continue
                tid = id(t)
                if tid in _valence_marked_traces:
                    continue
                _valence_marked_traces.add(tid)
                if len(_valence_marked_traces) > 500:
                    _valence_marked_traces.clear()
                key = f"{t.get('scene')}:{t.get('action')}"
                v = 0.5 if t.get("action_finished") else -0.5
                valence_cache[key] = v
                origin = str(t.get("origin", "internal"))
                _push_valence("cognitive", v, key, "action_success" if v > 0 else "action_fail", origin)
        # 3. 周期性综合心境广播（mood_state：躯体/认知/总效价均值，供 SPEECH 自述等消费）
        _valence_mood_counter += 1
        if _valence_mood_counter % VALENCE_MOOD_INTERVAL == 0:
            som = round(sum(somatic_valence_history) / len(somatic_valence_history), 4) if somatic_valence_history else None
            cog = round(sum(cognitive_valence_history) / len(cognitive_valence_history), 4) if cognitive_valence_history else None
            if som is not None or cog is not None:
                both = [x for x in (som, cog) if x is not None]
                emit_event("mood_state", {
                    "somatic_valence": som,       # 躯体来源效价均值（身体状态标签）
                    "cognitive_valence": cog,     # 认知来源效价均值（思维活动标签）
                    "overall_valence": round(sum(both) / len(both), 4),
                }, source="ORG-VALENCE", origin="internal")
    except Exception:
        pass


# ====================== 阶段4：ORG-INHIBIT 冲动抑制调控器官 ======================

inhibit_rule_list: List[Dict[str, Any]] = []


_self_limitations_inhibit: List[Dict[str, Any]] = []   # 自我模型能力边界缓存（阶段四）


def organ_inhibit_tick(ctx=None):
    """抑制：订阅 candidate_motives/selfmodel_update，去重+阈值过滤，产出 final_goals。

    阶段四闭环：候选目标若落在已知能力局限内，加强抑制（抬高通过阈值）。"""
    global _self_limitations_inhibit
    try:
        candidates = []
        seen = set()
        for ev in poll_events("ORG-INHIBIT"):
            et = ev["event_type"]
            p = ev.get("payload", {})
            if et == "selfmodel_update":
                _self_limitations_inhibit = list(p.get("limitations", []))
            elif et == "candidate_motives":
                # ── 阶段六修复6：按到达顺序过滤（事件因果序）──
                # 修复前：先收集全部候选再统一过滤——同批尾随而来的 selfmodel_update
                # 会提前更新缓存，「局限归纳之前到达的候选」也被新局限拦截
                # （未来信息泄漏到过去的决策），阶段六测试4 的「局限生效前
                # 通过（撞墙）」窗口不存在。
                # 修复后：每批候选到达时用「此刻」的局限认知过滤——归纳前的
                # 候选按旧认知决策，归纳后的候选才受新局限约束（行为翻转因果链完整）。
                lim_keys_now = {str(l.get("key", "")) for l in _self_limitations_inhibit}
                for m in p.get("motives", []):
                    if not isinstance(m, dict):
                        continue
                    g = str(m.get("goal", "")).strip()
                    drive = float(m.get("drive", 0.0))
                    # 阶段四：落在能力局限内的目标加强抑制（阈值 0.3 → 0.6）
                    threshold = 0.6 if g in lim_keys_now else 0.3
                    if g and g not in seen and len(g) <= 100 and drive >= threshold:
                        seen.add(g)
                        candidates.append(m)
        final = candidates
        if final:
            emit_event("final_goals", {"goals": [m["goal"] for m in final]}, source="ORG-INHIBIT", origin="internal")
        # 同步维护 working_memory.active_goals 的去重（保持 E 侧状态干净）
        goals = working_memory.get("active_goals") or []
        if isinstance(goals, list):
            cleaned = []
            s = set()
            for g in goals:
                gs = str(g).strip()
                if gs and gs not in s and len(gs) <= 100:
                    s.add(gs)
                    cleaned.append(g)
            working_memory["active_goals"] = cleaned[-20:]
    except Exception:
        pass


# ====================== 阶段3：ORG-CONSOLIDATE 记忆重放巩固器官（核心） ======================

_consolidate_counter: int = 0        # 记忆重放周期计数器


def organ_consolidate_tick(ctx=None):
    """巩固 + 重放（严格按 7Tan_origin验收_ORG_CONSOLIDATE 伪代码）：

      1. 订阅 wm_snapshot（ORG-E 工作记忆快照），遍历 context_stack 思想碎片；
         筛选 focus、效价达标的写入长期记忆（emit mem_consolidated 给 ORG-A）。
      2. 每 REPLAY_INTERVAL_TICKS 从 mem_consolidated 历史事件采样，重放回 ORG-E。

      筛选规则（伪代码原逻辑，AND）：
        if focus < FOCUS_THRESHOLD and abs(valence) < VALENCE_ABS_THRESHOLD: 跳过
      即：focus 达标 OR 效价达标 才巩固，两者都低则遗忘（幼年失忆）。
    """
    global _consolidate_counter
    try:
        cfg = get_organ("ORG-CONSOLIDATE").config
        focus_thr = float(cfg.get("FOCUS_THRESHOLD", 0.3))
        valence_thr = float(cfg.get("VALENCE_ABS_THRESHOLD", 0.2))
        # 阶段0取证（文档红线）：正式证据必须使用原始阈值 50，调低值仅限调试。
        replay_interval = int(cfg.get("REPLAY_INTERVAL_TICKS", 50))
        replay_sample = int(cfg.get("REPLAY_SAMPLE_COUNT", 8))

        # 1. 订阅 wm_snapshot（ORG-E 工作记忆快照）
        wm_snap = poll_latest_event("wm_snapshot")
        if wm_snap is not None:
            snap_payload = wm_snap.get("payload", {})
            context_stack = snap_payload.get("context_stack", [])
            subj_tick_evt = poll_latest_event("subjective_tick")
            if not subj_tick_evt:
                return
            now_subj_time = subj_tick_evt["payload"]["subjective_clock"]

            # ── 阶段六修复·测试5：幼年失忆时间依赖（主观时钟低 → 巩固门槛加倍）──
            # 修复前筛选阈值恒定、与主观时钟无关，「幼年→成年」分化在代码里不存在；
            # 幼年期（主观时钟 < INFANCY_SUBJECTIVE_TIME）门槛×2，只有高 focus / 高|效价|
            # 的少数强事件能巩固，复现「人类幼年失忆 + 强烈经历例外留存」现象。
            infancy_end = float(cfg.get("INFANCY_SUBJECTIVE_TIME", 60.0))
            infancy_active = float(now_subj_time) < infancy_end
            f_thr_eff = round(focus_thr * (2.0 if infancy_active else 1.0), 4)
            v_thr_eff = round(valence_thr * (2.0 if infancy_active else 1.0), 4)
            forgotten = 0

            # 遍历工作记忆碎片，筛选满足条件的写入长期记忆
            for thought_item in context_stack:
                if not isinstance(thought_item, dict):
                    continue
                if thought_item.get("consolidated"):
                    continue
                focus = float(thought_item.get("focus", 0.0))
                valence = float(thought_item.get("valence", 0.0))
                origin = thought_item.get("origin", "internal")
                # 筛选：focus 与效价都低于（幼年期加倍的）阈值才跳过（模拟遗忘/幼年失忆）
                if focus < f_thr_eff and abs(valence) < v_thr_eff:
                    forgotten += 1
                    continue

                mem_payload = {
                    "thought_fragment": thought_item.get("thought", ""),
                    "focus": focus,
                    "valence": valence,
                    "origin": origin,
                    "subjective_time": now_subj_time,
                    "weight_eff": 1.0,
                    "goal_tag": thought_item.get("goal_tag"),
                    "pe": thought_item.get("pe"),
                    "success": thought_item.get("success"),
                }
                # 发出记忆巩固事件，交给 ORG-A 写入记忆库
                emit_event(
                    event_type="mem_consolidated",
                    payload=mem_payload,
                    source="ORG-CONSOLIDATE",
                    origin="internal",
                )
                thought_item["consolidated"] = True

            # ── 阶段六修复·测试5：遗忘过程可观测（修复前跳过即静默 continue，黑盒验证无从取证）──
            if forgotten > 0:
                emit_event(
                    event_type="mem_forgotten",
                    payload={
                        "count": forgotten,
                        "infancy_active": infancy_active,
                        "focus_threshold": f_thr_eff,
                        "valence_threshold": v_thr_eff,
                        "subjective_time": now_subj_time,
                    },
                    source="ORG-CONSOLIDATE",
                    origin="internal",
                )
                logger.info(
                    f"🧠[consolidate] 遗忘过滤: 本 tick 跳过 {forgotten} 条低权重碎片 "
                    f"(幼年期={infancy_active}, 主观时间={now_subj_time}, "
                    f"门槛 focus>={f_thr_eff}/|valence|>={v_thr_eff})"
                )

        # 2. 记忆后台重放：周期触发（计数器已随器官状态落盘恢复 → 跨会话累计，重启死结解除）
        _consolidate_counter += 1
        if _consolidate_counter % replay_interval == 0:
            # ── 阶段六修复1：重放触发可观测（修复前静默发生/静默不发生，黑盒验证无从取证）──
            logger.info(
                f"🧠[replay] 记忆重放触发: 重放计数={_consolidate_counter}(跨会话累计), "
                f"间隔阈值={replay_interval}, 主观时钟={subjective_time.get('subjective_clock')}"
            )
            # 【阶段六·测试2修复】自传记忆连续性：高权重优先 + 双源采样
            #   源① ORG-A 长期记忆库（memory_library，随器官状态落盘 → 跨重启持久，
            #      久远高权重记忆不会因重启/缓冲截断而沉默——"我"的连续性本体）；
            #   源② 本进程事件回放缓冲（尚未入库/最近巩固的事件，补充）。
            # 旧逻辑仅从回放缓冲取「最近N条」：久远高权重被近期挤出 + 重启后缓冲清空，
            # 久远记忆彻底沉默，无法形成连续的"我"（违背阶段二设计目标）。
            _seen_replay_keys = set()
            _replay_samples: List[Dict[str, Any]] = []
            for m in memory_library:
                if not isinstance(m, dict) or not m.get("thought"):
                    continue
                _k = (str(m.get("thought")), str(m.get("subjective_time")))
                if _k in _seen_replay_keys:
                    continue
                _seen_replay_keys.add(_k)
                _replay_samples.append({
                    "thought": m.get("thought"),
                    "focus": float(m.get("focus", 0.5) or 0.5),
                    "valence": float(m.get("valence", 0.0) or 0.0),
                    "origin": m.get("origin", "internal"),
                    "goal_tag": m.get("goal_tag"),
                    "pe": m.get("pe"),
                    "subjective_time": m.get("subjective_time"),
                })
            for mem_evt in poll_replay_events("mem_consolidated", 200):
                mem_data = mem_evt.get("payload", {})
                if not isinstance(mem_data, dict):
                    continue
                _thought = mem_data.get("thought_fragment", "")
                _k = (str(_thought), str(mem_data.get("subjective_time")))
                if not _thought or _k in _seen_replay_keys:
                    continue
                _seen_replay_keys.add(_k)
                _replay_samples.append({
                    "thought": _thought,
                    "focus": float(mem_data.get("focus", 0.5) or 0.5),
                    "valence": float(mem_data.get("valence", 0.0) or 0.0),
                    "origin": mem_data.get("origin", "internal"),
                    "goal_tag": mem_data.get("goal_tag"),
                    "pe": mem_data.get("pe"),
                    "subjective_time": mem_data.get("subjective_time"),
                })
            _replay_samples.sort(key=lambda s: s.get("focus", 0.0), reverse=True)
            for mem_data in _replay_samples[:replay_sample]:  # 高权重优先重放（久远高权重不再被挤出）
                replay_thought = {
                    "thought": mem_data.get("thought", ""),
                    "focus": float(mem_data.get("focus", 0.5)) * 0.6,  # 重放 focus 衰减，防抢占工作记忆
                    "valence": float(mem_data.get("valence", 0.0)),
                    "origin": mem_data.get("origin", "internal"),  # 必须继承原始 origin，禁止硬编码
                    "goal_tag": mem_data.get("goal_tag"),
                    "pe": mem_data.get("pe"),
                    "subjective_time": mem_data.get("subjective_time"),  # 透传主观时间线（基于主观时间，非系统时间）
                    "rehearsal": True,   # 重放反哺标记：ORG-A 据此对长期记忆对应条目权重 +0.1（复述强化）
                }
                emit_event(
                    event_type="replay_thought_fragment",
                    payload=replay_thought,
                    source="ORG-CONSOLIDATE",
                    origin="internal",
                )
    except Exception:
        pass


# ====================== 阶段3：ORG-TIMESENSE 主观时间感知器官 ======================

subjective_time = {"subjective_clock": 0.0, "time_dilation": 1.0}


def organ_timesense_tick(ctx=None):
    """主观时间：维护主观时钟，受记忆规模调节时间膨胀，产出 subjective_tick。"""
    try:
        subjective_time["subjective_clock"] = round(float(subjective_time.get("subjective_clock", 0.0)) + 1.0, 2)
        traces = getattr(ctx, "traces", None) if ctx is not None else None
        n = len(traces) if traces else 0
        subjective_time["time_dilation"] = round(1.0 + min(1.0, n / 10000.0), 4)
        emit_event("subjective_tick", {
            "subjective_clock": subjective_time["subjective_clock"],
            "time_dilation": subjective_time["time_dilation"],
        }, source="ORG-TIMESENSE")
    except Exception:
        pass


# ====================== 阶段6：ORG-SELFMODEL 自我表征器官 ======================
# 约束（严格按 ORG-SELFMODEL tick 伪代码）：
#   1. 不直接读取其他模块全局变量，靠事件总线回放读取历史事件数据
#   2. 低频周期性执行（每 SELFMODEL_UPDATE_INTERVAL tick 一次），防自我模型震荡
#   3. 无硬编码自我文本描述，全部为结构化数值/列表
#   4. 输出 selfmodel_update 事件给全系统器官订阅

self_model_data: Dict[str, Any] = {
    "meta": {"last_update_subj_time": 0.0, "tick_counter": 0},
    "capability": [],        # [{"key":"scene:action","goal_tag":"scene:action","success_rate":float}, ...]
    "limitations": [],       # [{"key":"scene:action","goal_tag":"scene:action","fail_rate":float,"trials":int}, ...]
    "preferred_motives": [], # [{"motive_tag":str,"occur_count":int}, ...]
    "internal_signature": {},# {"fatigue_avg":float,"resource_pressure_avg":float}
    "history_summary": {"total_goal": 0, "total_success": 0, "total_fail": 0},
    "prediction_error_history": [],      # 阶段五：预测误差留痕（"我之前预测错了"的历史）
    "meta_cognition": {},                # 阶段五：关于自身思维过程的统计归纳
    "counterfactual_stats": {},          # 阶段五：反事实推演统计（"如果我改变目标会怎样"）
    "mind_flaws": [],                    # 思维缺陷清单（元认知完善：过度自信/自信不足/预测漂移/反复证伪/惯性遗憾）
    "confidence": 0.0,       # 0.0~1.0 证据越少置信度越低
}

# SELFMODEL 归纳配置（伪代码配置项：低频周期增量归纳，禁止每 tick 全量重算）
SELFMODEL_UPDATE_INTERVAL: int = 60    # 每 60 tick 执行一次归纳
# 阶段0取证（文档红线）：正式证据必须使用原始周期触发（每 60 tick 归纳一次）。
# 样本驱动提前归纳默认禁用（极大值=永不触发），保留代码路径；
# 调试/阶段1/消融实验需再开启时：设环境变量 ORGAN_SAMPLE_INDUCTION=1（样本阈值 3）。
SELFMODEL_EARLY_SAMPLE_N: int = 3 if os.environ.get("ORGAN_SAMPLE_INDUCTION", "0") == "1" else 10 ** 9
_last_induction_key: Optional[tuple] = None   # 上次样本驱动归纳时的最新样本身份（去重：无新样本不重复归纳）
SAMPLE_MEMORY_COUNT: int = 40          # 采样记忆事件条数
SAMPLE_HYPOTHESIS_COUNT: int = 25      # 采样假设事件条数
MIN_EVIDENCE_COUNT: int = 10           # 最小证据量，低于则压低 confidence


def organ_selfmodel_tick(ctx=None):
    """自我表征：低频周期性从事件总线回放历史事件，归纳自我模型（无任何硬编码文本）。

    严格按 ORG-SELFMODEL tick 伪代码落地：
      - 数据源全部通过 poll_replay_events / poll_latest_event 回放读取（禁止直读全局变量）
      - 每 SELFMODEL_UPDATE_INTERVAL tick 归纳一次，其余 tick 直接返回
      - 输出结构化 self_model_data，emit selfmodel_update 广播（origin=internal）"""
    global self_model_data
    try:
        # ========== tick 计数：周期触发 OR 样本驱动提前触发（阶段六修复3） ==========
        self_model_data["meta"]["tick_counter"] += 1
        tick_cnt = int(self_model_data["meta"]["tick_counter"])
        # 样本驱动：回放缓冲中「目标成败」巩固样本 ≥SELFMODEL_EARLY_SAMPLE_N 条 → 提前归纳。
        # 修复前仅周期触发（60 tick ≈ 60 轮对话，远超真实会话长度，自然运行永远凑不满周期
        # → selfmodel_update 事件 0 次 → 自我模型永不演化）。
        # 注意：这里必须直接检查回放缓冲里的实际样本（而非 CONSOLIDATE 直写的计数器）——
        # CONSOLIDATE 与 SELFMODEL 同 tick 先后执行，CONSOLIDATE 刚 emit 的样本要等
        # tick 末尾 dispatch 才进缓冲，同 tick 内计数器触发的归纳读到的缓冲是空的。
        global _last_induction_key
        _goal_evts = [
            e for e in poll_replay_events("mem_consolidated", 100)
            if isinstance(e.get("payload"), dict)
            and e["payload"].get("goal_tag")
            and e["payload"].get("success") is not None
        ]
        if tick_cnt % SELFMODEL_UPDATE_INTERVAL != 0:
            # 样本驱动分支：样本不足 → 跳过；无新样本（最新样本身份未变）→ 跳过（防每 tick 重复归纳刷屏）
            if len(_goal_evts) < SELFMODEL_EARLY_SAMPLE_N:
                return
            _newest = _goal_evts[-1].get("payload", {})
            _newest_key = (str(_newest.get("thought_fragment")), str(_newest.get("subjective_time")))
            if _newest_key == _last_induction_key:
                return
            logger.info(f"🧠[selfmodel] 样本驱动提前归纳: 可用目标成败样本 {len(_goal_evts)} 条 (tick={tick_cnt})")
        # 记录本次归纳时见过的最新样本身份（周期归纳也刷新，供样本驱动分支去重）
        if _goal_evts:
            _newest = _goal_evts[-1].get("payload", {})
            _last_induction_key = (str(_newest.get("thought_fragment")), str(_newest.get("subjective_time")))

        # ========== 步骤1：回放读取历史事件（禁止直读全局变量） ==========
        mem_events = poll_replay_events("mem_consolidated", SAMPLE_MEMORY_COUNT)
        hypo_events = poll_replay_events("hypothesis_update", SAMPLE_HYPOTHESIS_COUNT)
        motive_events = poll_replay_events("candidate_motives", 80)
        final_goal_events = poll_replay_events("final_goals", 80)
        pe_events = poll_replay_events("pe_update", 60)
        body_events = poll_replay_events("bodystate_update", 60)
        meta_events = poll_replay_events("meta_cognition_update", 40)
        counter_events = poll_replay_events("counterfactual_result", 40)
        sim_result_events = poll_replay_events("simulation_result", 40)   # 沙盒推演历史（自我校准：推演预期 vs 实际成败）
        subj_time_event = poll_latest_event("subjective_tick")
        if subj_time_event is None:
            return
        current_subj_time = float(subj_time_event.get("payload", {}).get("subjective_clock", 0.0))

        # ========== 步骤2：统计加工样本数据 ==========
        evidence_count = len(mem_events) + len(hypo_events)
        succ_map: Dict[str, List[bool]] = {}   # key -> 成败序列
        hist_sum = {"total_goal": 0, "total_success": 0, "total_fail": 0}
        origin_dist: Dict[str, int] = {"internal": 0, "external": 0}

        # 2-1 记忆样本统计：CONSOLIDATE 新结构（单条 thought_fragment），从 goal_tag+success 提取，
        #     兼容旧 items/scene/action 结构，并按 focus 取高权重自传记忆，区分 origin。
        mem_samples: List[Dict[str, Any]] = []
        for evt in mem_events:
            payload = evt.get("payload", {})
            if not isinstance(payload, dict):
                continue
            if payload.get("thought_fragment") is not None or "goal_tag" in payload:
                mem_samples.append(payload)        # 新结构：单条记忆
            else:
                for mem in payload.get("items", []):   # 旧结构：items 包裹（向后兼容）
                    if isinstance(mem, dict):
                        mem_samples.append(mem)
        mem_samples.sort(key=lambda m: float(m.get("focus", 0.0)), reverse=True)
        for mem in mem_samples[:SAMPLE_MEMORY_COUNT]:
            key = str(mem.get("goal_tag") or "").strip()
            if not key:
                continue
            # 跳过「未验证」的推演碎片（success=None 表示预期而非真实结果，不计成败）
            if mem.get("success") is None:
                continue
            ok = bool(mem.get("success", mem.get("action_finished", False)))
            hist_sum["total_goal"] += 1
            if ok:
                hist_sum["total_success"] += 1
            else:
                hist_sum["total_fail"] += 1
            succ_map.setdefault(key, []).append(ok)
            o = str(mem.get("origin", "internal"))
            origin_dist[o] = int(origin_dist.get(o, 0)) + 1

        # 2-2 假设样本：accepted 假设视为已验证能力（补充 capability）
        for evt in hypo_events:
            hp = evt.get("payload", {})
            if hp.get("status") == "accepted" and hp.get("key"):
                succ_map.setdefault(str(hp.get("key")), []).append(True)

        # 归纳 capability / limitations（结构化，无硬编码文本）
        new_capability = []
        new_limitations = []
        for key, flags in succ_map.items():
            total = len(flags)
            succ = sum(1 for f in flags if f)
            rate = round(succ / total, 4) if total else 0.0
            if succ > 0:
                new_capability.append({"key": key, "goal_tag": key, "success_rate": rate})
            if total >= 2 and rate <= 0.5:   # 至少2次尝试且失败率≥50% → 局限
                new_limitations.append({
                    "key": key, "goal_tag": key,
                    "fail_rate": round(1 - rate, 4), "trials": total,
                })
        new_capability = new_capability[:20]
        new_limitations = new_limitations[:20]

        # 2-3 动机出现频次 → preferred_motives
        motive_counter: Dict[str, int] = {}
        for evt in motive_events:
            for mot in evt.get("payload", {}).get("motives", []):
                if isinstance(mot, dict):
                    tag = mot.get("goal") or mot.get("motive_tag")
                    if tag:
                        motive_counter[str(tag)] = int(motive_counter.get(str(tag), 0)) + 1
        # 最终执行目标（ORG-INHIBIT 产出）频次并入 preferred_motives
        for evt in final_goal_events:
            for g in evt.get("payload", {}).get("goals", []):
                if g:
                    motive_counter[str(g)] = int(motive_counter.get(str(g), 0)) + 1
        new_preferred = [
            {"motive_tag": tag, "occur_count": cnt}
            for tag, cnt in sorted(motive_counter.items(), key=lambda x: -x[1])
        ][:20]

        # 2-4 本体信号统计（internal_signature）
        body_stats: Dict[str, float] = {}
        fatigue_list = [float(evt.get("payload", {}).get("fatigue", 0.0)) for evt in body_events]
        rp_list = [float(evt.get("payload", {}).get("resource_pressure", 0.0)) for evt in body_events]
        if fatigue_list:
            body_stats["fatigue_avg"] = round(sum(fatigue_list) / len(fatigue_list), 4)
        if rp_list:
            body_stats["resource_pressure_avg"] = round(sum(rp_list) / len(rp_list), 4)
        # PE / LP 预测误差统计（ORG-B 产出 pe_update 事件，阶段三数据源）
        pe_list = [float(evt.get("payload", {}).get("pe", 0.0)) for evt in pe_events]
        lp_list = [float(evt.get("payload", {}).get("lp", 0.0)) for evt in pe_events]
        if pe_list:
            body_stats["pe_avg"] = round(sum(pe_list) / len(pe_list), 4)
        if lp_list:
            body_stats["lp_avg"] = round(sum(lp_list) / len(lp_list), 4)
        # 阶段五元认知：预测误差留痕（"我之前预测错了"这类关于自身思考的历史，非仅均值）
        pe_history = [{"pe": p, "lp": l} for p, l in zip(pe_list, lp_list)][-30:]
        # 阶段五元认知：关于自身思维过程的统计（ORG-F 产出 meta_cognition_update）
        meta_cog: Dict[str, Any] = {}
        if meta_events:
            latest_meta = meta_events[-1].get("payload", {})
            meta_cog = {
                "hypo_accept_rate": latest_meta.get("hypo_accept_rate"),
                "pe_mean": latest_meta.get("pe_mean"),
                "meta_hypotheses": list(latest_meta.get("meta_hypotheses", [])),
            }
        # 阶段五元认知：反事实推演统计（ORG-SIMULATE 产出 counterfactual_result）
        counter_stats: Dict[str, Any] = {"total": 0, "better_alternative": 0}
        for evt in counter_events:
            p = evt.get("payload", {})
            counter_stats["total"] += 1
            if float(p.get("delta", 0.0)) > 0:
                counter_stats["better_alternative"] += 1

        # ===== 元认知完善：思维缺陷归纳（mind_flaws）=====
        # 1) 自我校准偏差（calibration）：沙盒推演平均置信度 vs 实际历史成功率的差值。
        #    gap>0 → 过度自信（总以为能成，实际常败）；gap<0 → 自信不足（明明擅长却不敢预期）。
        sim_conf_list = [float(evt.get("payload", {}).get("sim_confidence", 0.0)) for evt in sim_result_events]
        sim_conf_mean = round(sum(sim_conf_list) / len(sim_conf_list), 4) if sim_conf_list else None
        _actual_total = hist_sum["total_goal"]
        actual_success_rate = round(hist_sum["total_success"] / _actual_total, 4) if _actual_total > 0 else None
        calibration_gap = round(sim_conf_mean - actual_success_rate, 4) if (sim_conf_mean is not None and actual_success_rate is not None) else None
        # 2) 预测误差趋势（pe_trend）：最近 1/3 均值 vs 最早 1/3 均值 → 预测能力在改善还是恶化
        pe_trend = None
        if len(pe_list) >= 6:
            _third = max(1, len(pe_list) // 3)
            _early = sum(pe_list[:_third]) / _third
            _late = sum(pe_list[-_third:]) / _third
            if _late - _early > 0.1:
                pe_trend = "worsening"
            elif _early - _late > 0.1:
                pe_trend = "improving"
            else:
                pe_trend = "stable"
        # 3) 反复被证伪的假设（同 key 被拒绝 >= 2 次 → 思维反复出错的领域）
        _rejected_counter: Dict[str, int] = {}
        for evt in hypo_events:
            hp = evt.get("payload", {})
            if hp.get("status") == "rejected" and hp.get("key"):
                k = str(hp.get("key"))
                _rejected_counter[k] = _rejected_counter.get(k, 0) + 1
        repeated_falsified = sorted([k for k, c in _rejected_counter.items() if c >= 2])[:5]
        # 4) 惯性遗憾率（反事实推演中"发现更优替代"的占比 → 事后诸葛亮倾向）
        regret_rate = round(counter_stats["better_alternative"] / counter_stats["total"], 4) if counter_stats["total"] > 0 else None
        # 归纳思维缺陷清单（结构化，无自然语言；SPEECH 自述层负责忠实转述）
        mind_flaws: List[Dict[str, Any]] = []
        if calibration_gap is not None and calibration_gap > 0.2:
            mind_flaws.append({"type": "self_overconfident", "gap": calibration_gap,
                               "sim_conf_mean": sim_conf_mean, "actual_success_rate": actual_success_rate})
        elif calibration_gap is not None and calibration_gap < -0.2:
            mind_flaws.append({"type": "self_underconfident", "gap": calibration_gap,
                               "sim_conf_mean": sim_conf_mean, "actual_success_rate": actual_success_rate})
        _pe_mean_now = body_stats.get("pe_avg")
        if _pe_mean_now is not None and _pe_mean_now > 0.5 and pe_trend == "worsening":
            mind_flaws.append({"type": "self_prediction_drifting", "pe_mean": _pe_mean_now, "pe_trend": pe_trend})
        if repeated_falsified:
            mind_flaws.append({"type": "repeated_falsified_hypothesis", "keys": repeated_falsified})
        if regret_rate is not None and regret_rate > 0.4:
            mind_flaws.append({"type": "chronic_regret", "regret_rate": regret_rate})
        # 元认知统计扩展（进入 meta_cognition，随 selfmodel_update 广播）
        meta_cog["pe_trend"] = pe_trend
        meta_cog["calibration_gap"] = calibration_gap
        meta_cog["sim_conf_mean"] = sim_conf_mean
        meta_cog["actual_success_rate"] = actual_success_rate
        meta_cog["regret_rate"] = regret_rate

        # ========== 步骤3：计算自我模型置信度（证据越少越低，模拟幼儿自我概念模糊） ==========
        if evidence_count <= MIN_EVIDENCE_COUNT:
            conf = 0.1
        else:
            conf = min(0.1 + (evidence_count / (MIN_EVIDENCE_COUNT * 8)), 1.0)

        # ========== 步骤4：更新 self_model_data（结构化，无自然语言自我描述） ==========
        self_model_data["meta"]["last_update_subj_time"] = current_subj_time
        self_model_data["capability"] = new_capability
        self_model_data["limitations"] = new_limitations
        self_model_data["preferred_motives"] = new_preferred
        self_model_data["internal_signature"] = body_stats
        self_model_data["history_summary"] = hist_sum
        self_model_data["origin_distribution"] = origin_dist
        self_model_data["prediction_error_history"] = pe_history
        self_model_data["meta_cognition"] = meta_cog
        self_model_data["counterfactual_stats"] = counter_stats
        self_model_data["mind_flaws"] = mind_flaws
        self_model_data["confidence"] = round(conf, 4)

        # ========== 步骤5：广播 selfmodel_update（origin=internal） ==========
        emit_event("selfmodel_update", {
            "capability": new_capability,
            "abilities": [c["key"] for c in new_capability],  # 兼容旧闭环 ORG-E 读取
            "limitations": new_limitations,
            "preferred_motives": new_preferred,
            "internal_signature": body_stats,
            "history_summary": hist_sum,
            "prediction_error_history": pe_history,
            "meta_cognition": meta_cog,
            "counterfactual_stats": counter_stats,
            "mind_flaws": mind_flaws,
            "confidence": round(conf, 4),
            "meta": self_model_data["meta"],
        }, source="ORG-SELFMODEL", origin="internal")
    except Exception:
        pass


# ====================== 阶段6：ORG-SIMULATE 假想预演器官 ======================

sim_scenario_pool: List[Dict[str, Any]] = []
_self_limitations_sim: List[Dict[str, Any]] = []   # 自我模型能力边界缓存（阶段四）


def _simulate_confidence(ctx, scene, action, lim_keys):
    """内部沙盒推演：返回某「场景:动作」的预期成功率（精确到动作级）。

    证据分级：
      - 同场景同动作轨迹 → 主证据（直接经验，全权重）；
      - 同场景其他动作轨迹 → 弱参考（场景迁移，×0.3 折扣）；
      - 完全无经验 → 中性 0.5（知识缺口按一半一半处理，支持新场景探索，不再一刀切 0.0）。
    阶段四闭环：把「自身能力边界」作为推演条件，落在已知局限内则压低置信度（≤0.3）。
    阶段五元认知：反事实推演复用本函数，对「替代目标」做沙盒预演。"""
    if ctx is None:
        return 0.0
    _traces = [t for t in (getattr(ctx, "traces", []) or []) if isinstance(t, dict)]
    exact = [t for t in _traces if t.get("scene") == scene and t.get("action") == action]         # 主证据：同场景同动作
    scene_others = [t for t in _traces if t.get("scene") == scene and t.get("action") != action]  # 弱参考：同场景其他动作
    if exact:
        total_w = sum(float(t.get("weight_eff", 1.0)) for t in exact)
        succ_w = sum(float(t.get("weight_eff", 1.0)) for t in exact if t.get("action_finished"))
        conf = round(succ_w / total_w, 4) if total_w > 0 else 0.0
    elif scene_others:
        total_w = sum(float(t.get("weight_eff", 1.0)) for t in scene_others)
        succ_w = sum(float(t.get("weight_eff", 1.0)) for t in scene_others if t.get("action_finished"))
        scene_rate = (succ_w / total_w) if total_w > 0 else 0.0
        conf = round(scene_rate * 0.3, 4)   # 场景级弱参考：动作不同只给 30% 迁移置信
    else:
        conf = 0.5   # 无历史经验 → 中性（探索倾向），而非"必然失败"0.0
    if f"{scene}:{action}" in lim_keys:
        conf = min(conf, 0.3)
    return conf


def organ_simulate_tick(ctx=None):
    """假想预演：接收活跃目标做内部沙盒推演，产出 simulation_result 回送 B。

    阶段四闭环：把「自身能力边界」作为推演条件——若场景落在已知局限内，压低预期成功率。"""
    global _self_limitations_sim
    try:
        # 1. 从工作记忆快照接收活跃目标 / 自我模型能力边界
        for ev in poll_events("ORG-SIMULATE"):
            et = ev["event_type"]
            p = ev.get("payload", {})
            if et == "selfmodel_update":
                _self_limitations_sim = list(p.get("limitations", []))
            elif et == "wm_snapshot":
                goals = p.get("active_goals", [])
                for g in goals:
                    if not g:
                        continue
                    # 阶段四：goal 可能是「场景:动作」任务型目标，拆分成 scene/action 以对齐 limitations 粒度
                    if ":" in str(g):
                        scene, _, action = str(g).partition(":")
                    else:
                        scene, action = str(g), "explore"
                    scene = scene.strip()
                    action = action.strip()
                    if scene and action and not any(s.get("scene") == scene and s.get("action") == action for s in sim_scenario_pool):
                        sim_scenario_pool.append({"scene": scene, "action": action, "simulated": False})
        lim_keys = {str(l.get("key", "")) for l in _self_limitations_sim}
        # 2. 内部沙盒推演（复用 _simulate_confidence）
        simulated_this_round = []
        for sc in list(sim_scenario_pool):
            scene = sc.get("scene")
            action = sc.get("action")
            if not scene or not action:
                sim_scenario_pool.remove(sc)
                continue
            conf = _simulate_confidence(ctx, scene, action, lim_keys)
            sc["sim_confidence"] = conf
            # 多维推演：预期效价（同场景同动作历史成败 → ±0.5）+ 是否命中能力边界
            _exact = [t for t in (getattr(ctx, "traces", []) or [])
                      if isinstance(t, dict) and t.get("scene") == scene and t.get("action") == action]
            if _exact:
                _fin = sum(1 for t in _exact if t.get("action_finished"))
                expected_valence = round(0.5 if _fin * 2 >= len(_exact) else -0.5, 2)
            else:
                expected_valence = 0.0
            emit_event("simulation_result", {
                "scene": scene, "action": action, "sim_confidence": conf,
                "expected_valence": expected_valence,             # 预期效价（多维推演）
                "limit_hit": f"{scene}:{action}" in lim_keys,      # 是否命中自身能力边界
            }, source="ORG-SIMULATE", origin="internal")
            simulated_this_round.append({"scene": scene, "action": action, "conf": conf})
            sc["simulated"] = True
            sim_scenario_pool.remove(sc)
        # 3. 阶段五元认知：反事实推演——"如果我改变我的某个目标，我会发生什么"
        #    对每个已推演目标，评估若干替代动作（同场景优先、跨场景其次，最多 5 个防组合爆炸），
        #    选「预期差值 delta 最大」的最优替代 emit——修复旧版"字母序第一个"的任意性，
        #    让"改变目标会怎样"的回答有意义（回答的是最优改变，而非随机改变）。
        if ctx is not None:
            _traces_all = [t for t in (getattr(ctx, "traces", []) or []) if isinstance(t, dict)]
            _same_scene_actions = sorted({str(t.get("action")) for t in _traces_all
                                          if t.get("scene") and t.get("action")})
            _cross_scene_actions = sorted({str(t.get("action")) for t in _traces_all if t.get("action")})
            for r in simulated_this_round:
                scene = r["scene"]
                action = r["action"]
                orig_conf = r["conf"]
                # 候选替代：同场景其他动作优先（迁移合理），不足再补跨场景动作
                candidates = [a for a in _same_scene_actions if a and a != action]
                if len(candidates) < 3:
                    for a in _cross_scene_actions:
                        if a and a != action and a not in candidates:
                            candidates.append(a)
                candidates = candidates[:5]   # 最多评估 5 个替代，防组合爆炸
                best = None   # (alt, alt_conf, delta)
                for alt in candidates:
                    alt_conf = _simulate_confidence(ctx, scene, alt, lim_keys)
                    delta = round(alt_conf - orig_conf, 4)
                    if best is None or delta > best[2]:
                        best = (alt, alt_conf, delta)
                if best is not None:
                    emit_event("counterfactual_result", {
                        "original_goal": f"{scene}:{action}",
                        "alternative_goal": f"{scene}:{best[0]}",
                        "original_conf": orig_conf,
                        "alternative_conf": best[1],
                        "delta": best[2],
                        "evaluated_alts": len(candidates),   # 本次评估的替代数量（推演广度）
                        "best_alt": True,                     # 本条为最优替代（非任意首个）
                    }, source="ORG-SIMULATE", origin="internal")
                else:
                    # 无替代动作时，以「不执行该目标」为反事实基线
                    emit_event("counterfactual_result", {
                        "original_goal": f"{scene}:{action}",
                        "alternative_goal": f"{scene}:abstain",
                        "original_conf": orig_conf,
                        "alternative_conf": 0.0,
                        "delta": round(0.0 - orig_conf, 4),
                    }, source="ORG-SIMULATE", origin="internal")
    except Exception:
        pass


def organ_simulate_preview(scene, action, ctx=None) -> Dict[str, Any]:
    """ORG-SIMULATE 对「场景:动作」做一次假想预演（供 world_model 言语链路直接调用）。

    这是 ORG-SIMULATE 真正参与对话生成链路的入口——此前它只在 organ_tick_all 被动 tick，
    产出 simulation_result 回送 ORG-B，但不影响本轮回复文本。现在预测类问题会直接调用
    本函数做沙盒推演，把「模拟执行该动作的预期成功率 + 是否命中能力边界」写进回复。"""
    lim_keys = {str(l.get("key", "")) for l in _self_limitations_sim}
    conf = _simulate_confidence(ctx, scene, action, lim_keys)
    if conf is None:
        conf = 0.5
    return {
        "scene": scene,
        "action": action,
        "sim_confidence": conf,
        "limit_hit": f"{scene}:{action}" in lim_keys,
    }


# ====================== 注册新增内核器官 ======================

def register_extra_core_organs():
    register_organ(BionicOrgan(
        organ_code="ORG-BODYSTATES",
        organ_name="躯体稳态器官",
        module_name="ModuleBodyStates",
        bio_analogy="下丘脑、内脏传入通路，内部躯体信号源",
        enabled=True,
        tick_func=organ_bodystates_tick,
        config={}
    ))
    register_organ(BionicOrgan(
        organ_code="ORG-VALENCE",
        organ_name="效价·情绪标签器官",
        module_name="ModuleValence",
        bio_analogy="杏仁核、扣带回，情绪效价打分",
        enabled=True,
        tick_func=organ_valence_tick,
        config={}
    ))
    register_organ(BionicOrgan(
        organ_code="ORG-INHIBIT",
        organ_name="冲动抑制调控器官",
        module_name="ModuleInhibit",
        bio_analogy="腹内侧前额叶，目标冲动过滤抑制",
        enabled=True,
        tick_func=organ_inhibit_tick,
        config={}
    ))
    register_organ(BionicOrgan(
        organ_code="ORG-CONSOLIDATE",
        organ_name="记忆重放巩固器官",
        module_name="ModuleConsolidate",
        bio_analogy="海马-皮层睡眠记忆巩固回路",
        enabled=True,
        tick_func=organ_consolidate_tick,
        config={
            # 阶段0取证（文档红线）：恢复原始阈值 50——正式证据必须使用原始配置；
            # 之前的 20（阶段六修复1为对齐短会话调低）属调试用调参，不再用于取证。
            # 计数器已跨会话累计落盘，长期自然运行可达标（50 tick × 120s ≈ 100 分钟）。
            # 采样 6（阶段六修复1调整：context_stack 上限 12，重放占比不超一半，防挤占当下思考）。
            "REPLAY_INTERVAL_TICKS": 50,    # 每 50 tick（跨会话累计）执行一次记忆重放
            "REPLAY_SAMPLE_COUNT": 6,       # 每次重放采样几条高权重记忆
            "FOCUS_THRESHOLD": 0.3,         # focus 低于该值且效价低才不写入长期记忆
            "VALENCE_ABS_THRESHOLD": 0.2,   # 效价绝对值过低且 focus 低才不写入长期记忆
            # 阶段六修复·测试5：幼年失忆时间依赖——主观时钟低于该值时巩固门槛×2
            "INFANCY_SUBJECTIVE_TIME": 60.0,   # 幼年期结束点（主观时间单位）
        }
    ))
    register_organ(BionicOrgan(
        organ_code="ORG-TIMESENSE",
        organ_name="主观时间感知器官",
        module_name="ModuleTimeSense",
        bio_analogy="顶叶-海马时间编码回路",
        enabled=True,
        tick_func=organ_timesense_tick,
        config={}
    ))
    register_organ(BionicOrgan(
        organ_code="ORG-SELFMODEL",
        organ_name="自我表征器官",
        module_name="ModuleSelfModel",
        bio_analogy="大脑元认知自我表征回路",
        enabled=True,
        tick_func=organ_selfmodel_tick,
        config={}
    ))
    register_organ(BionicOrgan(
        organ_code="ORG-SIMULATE",
        organ_name="假想预演器官",
        module_name="ModuleSimulate",
        bio_analogy="脑内心理模拟、想象推演回路",
        enabled=True,
        tick_func=organ_simulate_tick,
        config={}
    ))


# ====================== 事件订阅拓扑（跨器官通信唯一通道） ======================

def _setup_subscriptions():
    """设置器官间的事件订阅关系（自底向上的信号流向）。"""
    # 阶段1：本体信号 → 动机/效价/安全
    subscribe_event("bodystate_update", "ORG-B")
    subscribe_event("bodystate_update", "ORG-VALENCE")
    subscribe_event("bodystate_update", "ORG-D")
    # 效价标签 → 前额叶(改focus) + 巩固(筛选依据)
    subscribe_event("valence_tag", "ORG-E")
    subscribe_event("valence_tag", "ORG-CONSOLIDATE")
    # 工作记忆快照 → 巩固/抑制/自我模型/假想预演
    subscribe_event("wm_snapshot", "ORG-CONSOLIDATE")
    subscribe_event("wm_snapshot", "ORG-INHIBIT")
    subscribe_event("wm_snapshot", "ORG-SIMULATE")
    subscribe_event("wm_snapshot", "ORG-SELFMODEL")
    # 主观时间 → 巩固
    subscribe_event("subjective_tick", "ORG-CONSOLIDATE")
    # 记忆巩固 → 海马体(写入) + 学习(假设)
    subscribe_event("mem_consolidated", "ORG-A")
    subscribe_event("mem_consolidated", "ORG-F")
    # 候选动机 → 抑制
    subscribe_event("candidate_motives", "ORG-INHIBIT")
    # 最终目标 → 前额叶(更新active_goals)
    subscribe_event("final_goals", "ORG-E")
    # 假设更新 → 自我模型（归纳能力/局限）
    subscribe_event("hypothesis_update", "ORG-SELFMODEL")
    # 阶段五元认知：ORG-F 订阅自身假设更新 + 预测误差，对自身思维做统计
    subscribe_event("hypothesis_update", "ORG-F")
    subscribe_event("pe_update", "ORG-F")
    # 自我模型更新 → 前额叶 + 动机 + 抑制 + 假想预演（阶段四闭环）
    subscribe_event("selfmodel_update", "ORG-E")
    subscribe_event("selfmodel_update", "ORG-B")
    subscribe_event("selfmodel_update", "ORG-INHIBIT")
    subscribe_event("selfmodel_update", "ORG-SIMULATE")
    # 阶段五元认知：元认知统计 + 反事实推演结果 → 自我模型（归纳"关于思考的思考"）
    subscribe_event("meta_cognition_update", "ORG-SELFMODEL")
    subscribe_event("counterfactual_result", "ORG-SELFMODEL")
    subscribe_event("counterfactual_result", "ORG-E")
    # 效价细化：假设接纳/证伪、预测误差、反事实遗憾 → 效价器官（认知来源效价打标）
    subscribe_event("hypothesis_update", "ORG-VALENCE")
    subscribe_event("pe_update", "ORG-VALENCE")
    subscribe_event("counterfactual_result", "ORG-VALENCE")
    # 记忆重放 → 前额叶工作记忆（阶段二）
    subscribe_event("memory_replay", "ORG-E")
    subscribe_event("replay_thought_fragment", "ORG-E")
    # 模拟结果 → 动机(算PE)
    subscribe_event("simulation_result", "ORG-B")
    # 外部信号流入（阶段一：我-非我边界——用户输入/工具返回作为 external 事件进入总线）
    subscribe_event("user_input", "ORG-E")
    subscribe_event("user_input", "ORG-F")
    subscribe_event("tool_result", "ORG-E")
    subscribe_event("tool_result", "ORG-F")
    # 重放反哺（rehearsal effect 复述强化）：重放碎片 → 海马体（对应长期记忆条目权重提升）
    subscribe_event("replay_thought_fragment", "ORG-A")
    # 言语自述层：内部状态忠实读数（ORG-SPEECH 只做模板转述，非真实感受）
    subscribe_event("bodystate_update", "ORG-SPEECH")
    subscribe_event("selfmodel_update", "ORG-SPEECH")
    subscribe_event("meta_cognition_update", "ORG-SPEECH")
    subscribe_event("mood_state", "ORG-SPEECH")
    subscribe_event("simulation_result", "ORG-SPEECH")


# ====================== 阶段六修复4：后台心跳（器官常驻呼吸，不依赖对话驱动）======================
# 修复前：organ_tick_all 仅由 respond() 驱动（每轮对话 1 tick），无人对话器官即「死亡」——
# 主观时钟不走、重放不触发、自我模型不演化。叙事自我要真正「活着」，必须有自主心跳。
# 机制：daemon 线程每 _HEARTBEAT_INTERVAL 秒 tick 一次（与对话 tick 共用 _TICK_LOCK 串行）。
# 开关：环境变量 ORGAN_HEARTBEAT=0 关闭 / ORGAN_HEARTBEAT_INTERVAL=秒 调频。

_heartbeat_thread: Optional[threading.Thread] = None


def _organ_heartbeat_loop(ctx):
    """心跳线程主体：永远循环，静默失败（绝不能让心跳线程把宿主进程带崩）。

    注意：此处不得再持 _TICK_LOCK——organ_tick_all 内部已持锁（串行化），
    threading.Lock 不可重入，外层再包一层会自锁死锁。"""
    while True:
        try:
            time.sleep(_HEARTBEAT_INTERVAL)
            organ_tick_all(ctx)   # 锁由 organ_tick_all 内部统一管理
        except Exception:
            time.sleep(5.0)   # 出错退避后重试


def start_organ_heartbeat(ctx=None) -> bool:
    """启动器官后台心跳。幂等（重复调用只启一次）。返回是否真的启动了。"""
    global _heartbeat_thread
    if not _HEARTBEAT_ENABLED:
        logger.info("🫀 器官心跳未启动（ORGAN_HEARTBEAT=0）")
        return False
    if _heartbeat_thread is not None and _heartbeat_thread.is_alive():
        return False
    _heartbeat_thread = threading.Thread(
        target=_organ_heartbeat_loop, args=(ctx,),
        daemon=True, name="organ-heartbeat",
    )
    _heartbeat_thread.start()
    logger.info(f"🫀 器官心跳已启动: 每 {_HEARTBEAT_INTERVAL} 秒自主 tick 一次（无对话也活着）")
    return True


# ====================== 一次性初始化全部器官 ======================

def init_all_organs():
    register_organ_a()
    register_organ_b()
    register_organ_d()
    register_organ_e()
    register_organ_f()
    register_organ_vis()
    register_organ_speech()
    register_extra_core_organs()
    _setup_subscriptions()
    load_organ_state()   # 启动恢复：ORG-A 长期记忆库 + ORG-SELFMODEL 自我模型快照


# ====================== 自检入口 ======================

if __name__ == "__main__":
    init_all_organs()
    print(f"已注册 {len(organ_registry)} 个器官")
    enabled = [c for c, o in organ_registry.items() if o.enabled]
    print(f"已启用 {len(enabled)} 个: {enabled}")
    print(f"订阅拓扑: {bus_stats()['subscriptions']}")
    organ_tick_all()
    print(f"分发后日志: {bus_stats()['log_len']}")
