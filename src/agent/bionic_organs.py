# =============================================================================
# 7Tan 仿生器官框架 —— 原生心智生长闭环（事件总线版）
# 依据：7Tan_All_Organs.txt（器官蓝图）+ code_20260903.txt（落地开发指南）
#
# 架构约束（必须遵守）：
#   1. 器官间禁止直接 import/读写对方全局变量，全部通信走内部消息事件总线。
#   2. 所有内部信号使用结构化字典（event_type + payload），不用自然语言字符串。
#   3. ORG-LLM.enabled=False，结构体仅历史兼容，任何器官逻辑不许调用 ORG-LLM。
#   4. ORG-SELFMODEL 禁止硬编码自我描述，数据只来源于记忆库/假设库/动机历史。
#   5. 实现顺序自底向上：本体信号 → 效价 → 工作记忆E → 记忆时序 → 动机+抑制
#      → 学习F → 自我模型+假想预演 → 安全输出。
#
# 事件在本 tick 内先入队，tick 结束后统一分发（organ_tick_all 末尾 dispatch），
# 避免同一 tick 内器官循环调用造成递归。
# =============================================================================

import os
import random
import time
from dataclasses import dataclass
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
_REPLAY_MAX_PER_TYPE: int = 200   # 每类事件最多保留条数（供 poll_replay_events 回放）
_subscriptions: Dict[str, List[str]] = {}         # event_type -> [organ_code, ...]
_inboxes: Dict[str, List[Dict[str, Any]]] = {}    # organ_code -> 待处理事件收件箱

# 事件总线观测日志开关：True=每次分发打印一行日志（肉眼可见信号流入），False=静默。
_BUS_LOG_ENABLED = True


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
        if len(_replay_buffer[etype]) > _REPLAY_MAX_PER_TYPE:
            _replay_buffer[etype] = _replay_buffer[etype][-_REPLAY_MAX_PER_TYPE:]
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


def organ_tick_all(ctx=None):
    """系统主循环：先分发已入队事件 → 顺序驱动所有已开启器官执行 tick → 末尾再分发本 tick 新事件。

    ctx 可选：传 world_model 的 memory 实例，使器官作用于真实状态。

    关键：开头先 dispatch 一次，把 respond() 开头 emit 的 external 事件（user_input/tool_result）
    在本轮器官 tick 前就送进收件箱，消除「本轮投递、下一轮才生效」的一轮延迟。"""
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


# ====================== 阶段3：ORG-A 海马体·长期记忆器官 ======================
# 职责：唯一记忆写入口（接收 mem_consolidated 新记忆）+ 权重衰减（冷热闭环冷端）

memory_library: List[Dict[str, Any]] = []


def module_a_tick(ctx=None):
    """海马体：监听 mem_consolidated 接收新记忆 + 全量记忆权重衰减。"""
    try:
        # 1. 接收新记忆条目（来自 CONSOLIDATE 的 mem_consolidated 事件）
        for ev in poll_events("ORG-A"):
            if ev["event_type"] == "mem_consolidated":
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
                    # 控制思想记忆库规模（防止无限增长）
                    while len(memory_library) > 200:
                        memory_library.pop(0)
        # 2. 权重衰减（冷端）
        target = getattr(ctx, "traces", None) if ctx is not None else None
        if target is None:
            target = memory_library
        for mem in target:
            if isinstance(mem, dict):
                mem["weight_eff"] = max(0.0, float(mem.get("weight_eff", 1.0)) - 0.001)
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
    """
    candidates = {}   # goal -> 累计评分
    # 1. 从记忆库采样（含 goal_tag + focus + weight_eff）
    for mem in memory_library:
        if not isinstance(mem, dict):
            continue
        gt = mem.get("goal_tag")
        if not gt or ":" not in str(gt):
            continue
        focus = float(mem.get("focus", 0.0) or 0.0)
        w = float(mem.get("weight_eff", 1.0) or 1.0)
        candidates[str(gt)] = candidates.get(str(gt), 0.0) + focus * w
    # 2. 从轨迹采样（scene + action）
    traces = getattr(ctx, "traces", None) or []
    for t in traces:
        if not isinstance(t, dict):
            continue
        scene = str(t.get("scene", "")).strip()
        action = str(t.get("action", "")).strip()
        if scene and action:
            key = f"{scene}:{action}"
            candidates[key] = candidates.get(key, 0.0) + float(t.get("weight_eff", 1.0) or 1.0)
    # 3. 生成任务型候选动机（含 limitations 降权）
    lim_keys = {str(l.get("key", "")) for l in limitations}
    motives = []
    for goal, score in sorted(candidates.items(), key=lambda x: -x[1])[:5]:
        drive = round(min(1.0, score / 5.0), 4)
        if drive < 0.1:
            continue
        if goal in lim_keys:
            drive = round(drive * 0.5, 4)   # 阶段四：落在能力局限内 → 降权
        motives.append({"goal": goal, "drive": drive, "source": "task_memory"})
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
        config={"ENABLE_7TAN_SELF_CODE_EVOLVE": False}
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
                # 阶段一：工具返回结果作为 external 信号进入工作记忆
                wm_push_thought(f"tool:{str(p.get('tool', ''))}:{str(p.get('summary', ''))[:40]}", 0.5, origin="external")
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


# ====================== ORG-LLM 基底神经·基座内核（历史兼容，强制关闭） ======================
# 约束：ORG-LLM.enabled=False，任何器官逻辑不许调用。

llm_model_path: str = "./qwen2.5-1.5b-instruct-q4_K_M.gguf"


def module_llm_tick(ctx=None):
    """基座内核：结构体占位，enabled=False，不执行任何推理。"""
    pass


def register_organ_llm():
    register_organ(BionicOrgan(
        organ_code="ORG-LLM",
        organ_name="基底神经·基座内核",
        module_name="LLM_GGUF",
        bio_analogy="大脑基底核，语言推理生成内核（已禁用）",
        enabled=False,
        tick_func=module_llm_tick,
        config={"model_path": llm_model_path}
    ))


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


# ====================== 阶段7：ORG-SPEECH 言语输出器官 ======================
# 职责：唯一把结构化内部事件翻译为人类文本输出的器官。

output_log: List[str] = []


def module_speech_tick(ctx=None):
    """言语输出：订阅 broadcast 事件翻译成文本，维护输出日志。"""
    global output_log
    try:
        for ev in poll_events("ORG-SPEECH"):
            if ev["event_type"] == "broadcast":
                text = ev.get("payload", {}).get("text", "")
                if text:
                    output_log.append(str(text)[:200])
        if len(output_log) > 200:
            output_log = output_log[-100:]
    except Exception:
        pass


def module_speech_push(text):
    """把最新一轮输出写入言语日志（保持 world_model 接口兼容）。"""
    global output_log
    try:
        if text:
            output_log.append(str(text)[:200])
            if len(output_log) > 200:
                output_log = output_log[-100:]
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


# ====================== 阶段1：ORG-VALENCE 情绪效价标签器官 ======================

valence_cache: Dict[str, float] = {}  # item_id -> valence [-1.0 厌恶 .. 0 中性 .. +1.0 愉悦]


def organ_valence_tick(ctx=None):
    """效价：给本体/记忆条目打 valence 标签，产出 valence_tag 事件。"""
    try:
        # 1. 处理本体信号 → 疲劳高产生负效价
        for ev in poll_events("ORG-VALENCE"):
            if ev["event_type"] == "bodystate_update":
                fatigue = float(ev.get("payload", {}).get("fatigue", 0.0))
                if fatigue > 0.7:
                    emit_event("valence_tag", {
                        "item": "bodystate",
                        "valence": -0.3,
                        "reason": "fatigue_high",
                    }, source="ORG-VALENCE", origin="internal")
        # 2. 给最近记忆打效价标签（携带 origin，供巩固层区分内外来源）
        traces = getattr(ctx, "traces", None) if ctx is not None else None
        if traces:
            for t in traces[-10:]:
                if not isinstance(t, dict):
                    continue
                key = f"{t.get('scene')}:{t.get('action')}"
                v = 0.5 if t.get("action_finished") else -0.5
                valence_cache[key] = v
                origin = str(t.get("origin", "internal"))
                emit_event("valence_tag", {
                    "item": key,
                    "valence": v,
                    "origin": origin,
                }, source="ORG-VALENCE", origin=origin)
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
        for ev in poll_events("ORG-INHIBIT"):
            et = ev["event_type"]
            p = ev.get("payload", {})
            if et == "selfmodel_update":
                _self_limitations_inhibit = list(p.get("limitations", []))
            elif et == "candidate_motives":
                candidates.extend(p.get("motives", []))
        lim_keys = {str(l.get("key", "")) for l in _self_limitations_inhibit}
        seen = set()
        final = []
        for m in candidates:
            if not isinstance(m, dict):
                continue
            g = str(m.get("goal", "")).strip()
            drive = float(m.get("drive", 0.0))
            # 阶段四：落在能力局限内的目标加强抑制（阈值 0.3 → 0.6）
            threshold = 0.6 if g in lim_keys else 0.3
            if g and g not in seen and len(g) <= 100 and drive >= threshold:
                seen.add(g)
                final.append(m)
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
        replay_interval = int(cfg.get("REPLAY_INTERVAL_TICKS", 100))
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

            # 遍历工作记忆碎片，筛选满足条件的写入长期记忆
            for thought_item in context_stack:
                if not isinstance(thought_item, dict):
                    continue
                if thought_item.get("consolidated"):
                    continue
                focus = float(thought_item.get("focus", 0.0))
                valence = float(thought_item.get("valence", 0.0))
                origin = thought_item.get("origin", "internal")
                # 筛选：focus 与效价都低于阈值才跳过（模拟遗忘/幼年失忆）
                if focus < focus_thr and abs(valence) < valence_thr:
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

        # 2. 记忆后台重放：周期触发
        _consolidate_counter += 1
        if _consolidate_counter % replay_interval == 0:
            # 【阶段六·测试2修复】自传记忆连续性：重放采样从「最近N条」改为「全部历史+高权重优先」
            # 旧逻辑 poll_replay_events(..., replay_sample) 内部取队列尾部（最近N条），
            # 久远高权重记忆永远被近期低权重记忆挤出重放队列 → 久远记忆彻底沉默，
            # 系统只剩近期记忆，无法形成连续的"我"（违背阶段二设计目标）。
            all_mem_events = poll_replay_events("mem_consolidated", 200)  # 全部历史（回放缓冲上限200条）
            all_mem_events.sort(
                key=lambda e: float(e.get("payload", {}).get("focus", 0.0)) if isinstance(e.get("payload"), dict) else 0.0,
                reverse=True,
            )
            old_mem_events = all_mem_events[:replay_sample]  # 高权重优先重放（久远高权重不再被挤出）
            for mem_evt in old_mem_events:
                mem_data = mem_evt.get("payload", {})
                if not isinstance(mem_data, dict):
                    continue
                replay_thought = {
                    "thought": mem_data.get("thought_fragment", ""),
                    "focus": float(mem_data.get("focus", 0.5)) * 0.6,  # 重放 focus 衰减，防抢占工作记忆
                    "valence": float(mem_data.get("valence", 0.0)),
                    "origin": mem_data.get("origin", "internal"),  # 必须继承原始 origin，禁止硬编码
                    "goal_tag": mem_data.get("goal_tag"),
                    "pe": mem_data.get("pe"),
                    "subjective_time": mem_data.get("subjective_time"),  # 透传主观时间线（基于主观时间，非系统时间）
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
    "confidence": 0.0,       # 0.0~1.0 证据越少置信度越低
}

# SELFMODEL 归纳配置（伪代码配置项：低频周期增量归纳，禁止每 tick 全量重算）
SELFMODEL_UPDATE_INTERVAL: int = 60    # 每 60 tick 执行一次归纳
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
        # ========== tick 计数，只有到达周期才归纳，其余 tick 直接返回 ==========
        self_model_data["meta"]["tick_counter"] += 1
        tick_cnt = int(self_model_data["meta"]["tick_counter"])
        if tick_cnt % SELFMODEL_UPDATE_INTERVAL != 0:
            return

        # ========== 步骤1：回放读取历史事件（禁止直读全局变量） ==========
        mem_events = poll_replay_events("mem_consolidated", SAMPLE_MEMORY_COUNT)
        hypo_events = poll_replay_events("hypothesis_update", SAMPLE_HYPOTHESIS_COUNT)
        motive_events = poll_replay_events("candidate_motives", 80)
        final_goal_events = poll_replay_events("final_goals", 80)
        pe_events = poll_replay_events("pe_update", 60)
        body_events = poll_replay_events("bodystate_update", 60)
        meta_events = poll_replay_events("meta_cognition_update", 40)
        counter_events = poll_replay_events("counterfactual_result", 40)
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
            "confidence": round(conf, 4),
            "meta": self_model_data["meta"],
        }, source="ORG-SELFMODEL", origin="internal")
    except Exception:
        pass


# ====================== 阶段6：ORG-SIMULATE 假想预演器官 ======================

sim_scenario_pool: List[Dict[str, Any]] = []
_self_limitations_sim: List[Dict[str, Any]] = []   # 自我模型能力边界缓存（阶段四）


def _simulate_confidence(ctx, scene, action, lim_keys):
    """内部沙盒推演：返回某「场景:动作」的预期成功率。

    阶段四闭环：把「自身能力边界」作为推演条件，落在已知局限内则压低置信度。
    阶段五元认知：反事实推演复用本函数，对「替代目标」做沙盒预演。"""
    if ctx is None:
        return 0.0
    similar = [t for t in (getattr(ctx, "traces", []) or [])
               if isinstance(t, dict) and t.get("scene") == scene]
    if similar:
        total_w = sum(float(t.get("weight_eff", 1.0)) for t in similar)
        succ_w = sum(float(t.get("weight_eff", 1.0)) for t in similar if t.get("action_finished"))
        conf = round(succ_w / total_w, 4) if total_w > 0 else 0.0
    else:
        conf = 0.0  # 无历史经验 → 知识缺口
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
            emit_event("simulation_result", {
                "scene": scene, "action": action, "sim_confidence": conf,
            }, source="ORG-SIMULATE", origin="internal")
            simulated_this_round.append({"scene": scene, "action": action, "conf": conf})
            sc["simulated"] = True
            sim_scenario_pool.remove(sc)
        # 3. 阶段五元认知：反事实推演——"如果我改变我的某个目标，我会发生什么"
        #    对每个已推演目标，找一个不同的替代动作，推演对比并产出 counterfactual_result。
        if ctx is not None:
            alt_actions = set()
            for t in (getattr(ctx, "traces", []) or []):
                if isinstance(t, dict) and t.get("action"):
                    alt_actions.add(str(t.get("action")))
            for r in simulated_this_round:
                scene = r["scene"]
                action = r["action"]
                orig_conf = r["conf"]
                alt_found = False
                for alt in sorted(alt_actions):
                    if alt == action or not alt:
                        continue
                    alt_conf = _simulate_confidence(ctx, scene, alt, lim_keys)
                    emit_event("counterfactual_result", {
                        "original_goal": f"{scene}:{action}",
                        "alternative_goal": f"{scene}:{alt}",
                        "original_conf": orig_conf,
                        "alternative_conf": alt_conf,
                        "delta": round(alt_conf - orig_conf, 4),
                    }, source="ORG-SIMULATE", origin="internal")
                    alt_found = True
                    break   # 每个目标只取第一个替代动作，避免组合爆炸
                if not alt_found:
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
            "REPLAY_INTERVAL_TICKS": 100,   # 每 100 tick 执行一次记忆重放
            "REPLAY_SAMPLE_COUNT": 8,       # 每次重放采样几条高权重记忆
            "FOCUS_THRESHOLD": 0.3,         # focus 低于该值且效价低才不写入长期记忆
            "VALENCE_ABS_THRESHOLD": 0.2,   # 效价绝对值过低且 focus 低才不写入长期记忆
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


# ====================== 一次性初始化全部器官 ======================

def init_all_organs():
    register_organ_a()
    register_organ_b()
    register_organ_d()
    register_organ_e()
    register_organ_f()
    register_organ_llm()
    register_organ_vis()
    register_organ_speech()
    register_extra_core_organs()
    _setup_subscriptions()


# ====================== 自检入口 ======================

if __name__ == "__main__":
    init_all_organs()
    print(f"已注册 {len(organ_registry)} 个器官")
    enabled = [c for c, o in organ_registry.items() if o.enabled]
    print(f"已启用 {len(enabled)} 个: {enabled}")
    print(f"订阅拓扑: {bus_stats()['subscriptions']}")
    organ_tick_all()
    print(f"分发后日志: {bus_stats()['log_len']}")
