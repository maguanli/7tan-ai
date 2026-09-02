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
_subscriptions: Dict[str, List[str]] = {}         # event_type -> [organ_code, ...]
_inboxes: Dict[str, List[Dict[str, Any]]] = {}    # organ_code -> 待处理事件收件箱


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
    """tick 结束后统一分发：按订阅表投递到各器官收件箱（防递归）。"""
    global _event_log
    for ev in _event_queue:
        etype = ev["event_type"]
        for code in _subscriptions.get(etype, []):
            _inboxes.setdefault(code, []).append(ev)
    _event_log.extend(_event_queue)
    if len(_event_log) > 500:
        _event_log = _event_log[-300:]
    _event_queue.clear()


def poll_events(organ_code: str) -> List[Dict[str, Any]]:
    """取出某器官收件箱里的所有事件（读后清空）。"""
    evs = _inboxes.get(organ_code, [])
    _inboxes[organ_code] = []
    return evs


def bus_stats() -> Dict[str, Any]:
    """事件总线统计（供调试/审查）。"""
    return {
        "queue_len": len(_event_queue),
        "log_len": len(_event_log),
        "subscriptions": {k: len(v) for k, v in _subscriptions.items()},
        "inboxes": {k: len(v) for k, v in _inboxes.items()},
    }


def organ_tick_all(ctx=None):
    """系统主循环：顺序驱动所有已开启器官执行 tick，结束后统一分发事件。

    ctx 可选：传 world_model 的 memory 实例，使器官作用于真实状态。"""
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
                items = ev.get("payload", {}).get("items", [])
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


def module_b_tick(ctx=None):
    """杏仁核：根据本体信号生成候选动机 + 计算预测误差 PE / 学习进度 LP。

    阶段四闭环：收到 selfmodel_update 后，把 limitations 存下，
    生成候选动机时若目标落在已知能力局限内，降低其驱动权重。"""
    global _self_limitations_b, _self_confidence_b
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


def wm_push_thought(thought_fragment, focus):
    """把思想碎片压入工作记忆 context_stack。"""
    max_step = 12
    if len(working_memory["context_stack"]) >= max_step:
        working_memory["context_stack"].pop(0)
    working_memory["context_stack"].append({"thought": thought_fragment, "focus": focus})


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
                    wm_push_thought(f"replay:{scene}:{action}", 0.5)
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


def module_f_tick(ctx=None):
    """脑回：监听 mem_consolidated 归纳假设，按阈值接纳/证伪。

    阶段一：统计 internal/external 两类事件规律（内部信号 vs 外界输入）。"""
    try:
        # 1. 监听新记忆 → 归纳假设（同时统计来源 origin）
        for ev in poll_events("ORG-F"):
            if ev["event_type"] == "mem_consolidated":
                for item in ev.get("payload", {}).get("items", []):
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

replay_buffer: List[Dict[str, Any]] = []
_consolidate_counter: int = 0        # 重放周期计数器（阶段二）
REPLAY_INTERVAL = 5                   # 每隔 N 个 tick 重放一次历史记忆
REPLAY_BATCH = 3                      # 每次重放采样条数


def organ_consolidate_tick(ctx=None):
    """巩固 + 重放：筛选高权重碎片固化进 ORG-A；每隔 N tick 重放历史记忆送入 ORG-E。

    阶段二落地：
      - 数据流打通：从 ctx.traces 采样「未巩固」轨迹 → replay_buffer（不再空转）
      - 巩固筛选：高 focus + 高 abs(valence) 优先固化；低权重直接丢弃（模拟幼年失忆）
      - 每条 mem_consolidated 必须携带 subjective_time / valence / origin
      - 记忆重放：每隔 REPLAY_INTERVAL 个 tick 随机采样历史记忆 → memory_replay 事件
    """
    global _consolidate_counter
    try:
        # 1. 收集本 tick 的效价标签、工作记忆快照、主观时间
        valences: Dict[str, float] = {}
        focus_weight = 0.5
        subj_ts = float(subjective_time.get("subjective_clock", 0.0))
        for ev in poll_events("ORG-CONSOLIDATE"):
            et = ev["event_type"]
            p = ev.get("payload", {})
            if et == "valence_tag":
                item = p.get("item", "")
                valences[item] = float(p.get("valence", 0.0))
            elif et == "wm_snapshot":
                focus_weight = float(p.get("focus_weight", 0.5))
            elif et == "subjective_tick":
                subj_ts = float(p.get("subjective_clock", subj_ts))
        # 1.5 数据流打通：从真实记忆库采样「未巩固」的新轨迹 → replay_buffer
        traces = getattr(ctx, "traces", None) if ctx is not None else None
        if traces:
            for t in traces[-20:]:
                if not isinstance(t, dict):
                    continue
                if t.get("consolidated"):
                    continue
                scene = t.get("scene")
                action = t.get("action")
                if not (scene and action):
                    continue
                key = f"{scene}:{action}"
                v = valences.get(key, (0.5 if t.get("action_finished") else -0.5))
                replay_buffer.append({
                    "scene": scene,
                    "action": action,
                    "focus": float(t.get("weight_eff", focus_weight)),
                    "valence": v,
                    "origin": str(t.get("origin", "internal")),
                    "subjective_time": subj_ts,
                    "action_finished": bool(t.get("action_finished", False)),
                    "scene_changed": bool(t.get("scene_changed", False)),
                    "defect_reduced": bool(t.get("defect_reduced", False)),
                    "knowledge_gained": bool(t.get("knowledge_gained", False)),
                })
                t["consolidated"] = True  # 标记已采样，避免重复巩固
        # 2. 从重放缓冲筛选高权重 + 显著效价碎片（低权重直接丢弃 = 遗忘 / 幼年失忆）
        to_consolidate = []
        for frag in list(replay_buffer):
            if not isinstance(frag, dict):
                continue
            fw = float(frag.get("focus", focus_weight))
            v = float(frag.get("valence", 0.0))
            if fw > 0.5 and abs(v) > 0.2:
                to_consolidate.append(frag)
        replay_buffer.clear()
        # 3. 产出 mem_consolidated 事件（携带 subjective_time / valence / origin）
        if to_consolidate:
            emit_event("mem_consolidated", {"items": to_consolidate},
                       source="ORG-CONSOLIDATE", origin="internal")
        # 4. 记忆重放（阶段二）：每隔 N tick 随机采样历史记忆 → 送入 ORG-E 工作记忆
        _consolidate_counter += 1
        if traces and _consolidate_counter % REPLAY_INTERVAL == 0:
            candidates = [t for t in traces if isinstance(t, dict)
                          and t.get("scene") and t.get("action")]
            if candidates:
                batch = random.sample(candidates, min(REPLAY_BATCH, len(candidates)))
                for t in batch:
                    emit_event("memory_replay", {
                        "scene": t.get("scene"),
                        "action": t.get("action"),
                        "origin": str(t.get("origin", "internal")),
                        "subjective_time": float(t.get("ts", subj_ts)),
                    }, source="ORG-CONSOLIDATE", origin="internal")
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
# 约束：禁止硬编码自我描述，数据只来源于记忆库/假设库/动机历史。

self_model_data: Dict[str, Any] = {}


def organ_selfmodel_tick(ctx=None):
    """自我表征：从记忆库/假设库/动机历史归纳自我模型（无任何硬编码文本）。

    阶段三/四落地：产出 confidence（随样本量抬升）与 limitations（持续失败边界），
    随 selfmodel_update 事件广播，供 B / INHIBIT / SIMULATE 参与决策闭环。"""
    try:
        traces = getattr(ctx, "traces", None) if ctx is not None else None
        knowledge = getattr(ctx, "knowledge", None) if ctx is not None else None
        n_traces = len(traces) if traces else 0
        n_know = len(knowledge) if knowledge else 0
        # 成功/失败记录（从记忆库归纳）
        succ = sum(1 for t in (traces or []) if isinstance(t, dict) and t.get("action_finished"))
        fail = n_traces - succ
        # 能力边界：从假设库归纳（已验证可成功的 key）
        abilities = [h.get("key") for h in hypothesis_registry if float(h.get("score", 0.0)) >= 0.6]
        # 局限边界：从记忆库归纳「持续失败」的 (scene, action)（结构化，无硬编码文本）
        from collections import Counter
        succ_c = Counter()
        fail_c = Counter()
        for t in (traces or []):
            if not isinstance(t, dict):
                continue
            key = f"{t.get('scene')}:{t.get('action')}"
            if t.get("action_finished"):
                succ_c[key] += 1
            else:
                fail_c[key] += 1
        limitations = []
        for key, f in fail_c.items():
            s = succ_c.get(key, 0)
            total = f + s
            if total >= 2 and (f / total) >= 0.5:   # 至少2次尝试且失败率≥50%
                limitations.append({"key": key, "fail_rate": round(f / total, 4), "trials": total})
        # 置信度：随记忆样本量抬升（早期低=自我概念模糊，后期高=清晰）
        confidence = round(min(1.0, n_traces / 500.0), 4)
        # 动机历史：从效价缓存归纳（近期正/负效价分布）
        n_pos = sum(1 for v in valence_cache.values() if v > 0)
        n_neg = sum(1 for v in valence_cache.values() if v < 0)
        # 全部来自数据，无硬编码
        self_model_data.update({
            "organ_count": len(organ_registry),   # 架构事实
            "trace_count": n_traces,              # 记忆数据
            "knowledge_count": n_know,            # 知识数据
            "hypothesis_count": len(hypothesis_registry),  # 学习数据
            "success_count": succ,                # 成功记录
            "failure_count": fail,                # 失败记录
            "valence_pos": n_pos,                 # 动机历史（正）
            "valence_neg": n_neg,                 # 动机历史（负）
            "abilities": abilities[:20],          # 能力边界（从假设归纳）
            "limitations": limitations[:20],      # 局限边界（从记忆归纳）
            "confidence": confidence,             # 自我模型置信度（随样本量抬升）
            "ts": time.time(),
        })
        emit_event("selfmodel_update", {
            "abilities": abilities[:20],
            "limitations": limitations[:20],
            "confidence": confidence,
            "success_ratio": round(succ / n_traces, 4) if n_traces else 0.0,
        }, source="ORG-SELFMODEL", origin="internal")
    except Exception:
        pass


# ====================== 阶段6：ORG-SIMULATE 假想预演器官 ======================

sim_scenario_pool: List[Dict[str, Any]] = []
_self_limitations_sim: List[Dict[str, Any]] = []   # 自我模型能力边界缓存（阶段四）


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
                    if g and not any(s.get("scene") == g for s in sim_scenario_pool):
                        sim_scenario_pool.append({"scene": g, "action": "explore", "simulated": False})
        lim_keys = {str(l.get("key", "")) for l in _self_limitations_sim}
        # 2. 内部沙盒推演
        for sc in list(sim_scenario_pool):
            scene = sc.get("scene")
            action = sc.get("action")
            if not scene or not action:
                sim_scenario_pool.remove(sc)
                continue
            if ctx is not None:
                similar = [t for t in (getattr(ctx, "traces", []) or [])
                           if isinstance(t, dict) and t.get("scene") == scene]
                if similar:
                    total_w = sum(float(t.get("weight_eff", 1.0)) for t in similar)
                    succ_w = sum(float(t.get("weight_eff", 1.0)) for t in similar if t.get("action_finished"))
                    conf = round(succ_w / total_w, 4) if total_w > 0 else 0.0
                else:
                    conf = 0.0  # 无历史经验 → 知识缺口
                # 阶段四：能力边界作为推演条件，落在已知局限内则压低置信度
                if f"{scene}:{action}" in lim_keys:
                    conf = min(conf, 0.3)
                sc["sim_confidence"] = conf
                emit_event("simulation_result", {
                    "scene": scene, "action": action, "sim_confidence": conf,
                }, source="ORG-SIMULATE", origin="internal")
            sc["simulated"] = True
            sim_scenario_pool.remove(sc)
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
        config={}
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
    # 假设更新 → 自我模型
    subscribe_event("hypothesis_update", "ORG-SELFMODEL")
    # 自我模型更新 → 前额叶 + 动机 + 抑制 + 假想预演（阶段四闭环）
    subscribe_event("selfmodel_update", "ORG-E")
    subscribe_event("selfmodel_update", "ORG-B")
    subscribe_event("selfmodel_update", "ORG-INHIBIT")
    subscribe_event("selfmodel_update", "ORG-SIMULATE")
    # 记忆重放 → 前额叶工作记忆（阶段二）
    subscribe_event("memory_replay", "ORG-E")
    # 模拟结果 → 动机(算PE)
    subscribe_event("simulation_result", "ORG-B")


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
