# -*- coding: utf-8 -*-
"""阶段六：5 项客观观测测试（叙事自我是否真的长出——看内部事件与数据，不看 SPEECH 输出）

测试1 我-非我边界：记忆/工作记忆稳定区分 origin=internal/external，能统计内外信号行为差异
测试2 自传记忆连续性：久远高权重历史经历（按主观时间线）被重放进 ORG-E 工作记忆
测试3 自我模型演化：confidence 随经验上升、capability/limitations 随成败动态变化
测试4 自我参与决策闭环：limitations 真正干预动机降权 + INHIBIT 过滤
测试5 幼年效应：早期大量低权重事件不固化，仅高 focus/valence 少数固化
"""
import sys, os
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import src.agent.bionic_organs as bo


def reset():
    """彻底重置仿生器官全局状态，保证每个测试独立、干净。"""
    bo.organ_registry.clear()
    bo._event_queue.clear()
    bo._event_log.clear()
    # ── 状态隔离（2026-09-03 修复）：init_all_organs() 末尾会 load_organ_state() 读取真实
    # data/tan_model_organs.json——运行中的 WEB 服务每 30 tick 自动落盘真实对话记忆，
    # 会把生产数据灌进测试（「刚启动条目数」「固化计数」被污染而误报失败）。
    # 这里先把 _ORGAN_STATE_PATH 重定向到临时空文件，init 加载不到任何东西，测试自干净。
    import tempfile as _tf
    _tmp = Path(_tf.mkdtemp(prefix="stage6_observe_")) / "organs.json"
    bo._ORGAN_STATE_PATH = _tmp
    bo._replay_buffer.clear()
    bo._subscriptions.clear()
    bo._inboxes.clear()
    bo.memory_library.clear()
    bo.working_memory["context_stack"].clear()
    bo.working_memory["active_goals"].clear()
    bo.working_memory["scratch_pad"].clear()
    bo.working_memory["focus_weight"] = 0.5
    bo.subjective_time["subjective_clock"] = 0.0
    bo.subjective_time["time_dilation"] = 1.0
    bo._consolidate_counter = 0
    bo.hypothesis_registry.clear()
    bo.origin_stats.clear()
    bo.pe_lp_buffer["pe"] = 0.0
    bo.pe_lp_buffer["lp"] = 0.0
    bo.bodystate_buffer["fatigue"] = 0.0
    bo.bodystate_buffer["resource_pressure"] = 0.0
    bo.bodystate_buffer["damage_level"] = 0.0
    bo._self_limitations_b = []
    bo._self_limitations_inhibit = []
    bo._self_limitations_sim = []
    bo._self_confidence_b = 0.0
    bo._task_motive_counter = 0
    bo._meta_cognition_counter = 0
    bo.meta_cognition_stats["hypo_accepted"] = 0
    bo.meta_cognition_stats["hypo_rejected"] = 0
    bo.meta_cognition_stats["pe_samples"] = []
    bo.meta_cognition_stats["meta_hypotheses"] = []
    bo.sim_scenario_pool.clear()
    bo.self_model_data["meta"]["tick_counter"] = 0
    bo.self_model_data["meta"]["last_update_subj_time"] = 0.0
    bo.self_model_data["capability"] = []
    bo.self_model_data["limitations"] = []
    bo.self_model_data["preferred_motives"] = []
    bo.self_model_data["internal_signature"] = {}
    bo.self_model_data["history_summary"] = {"total_goal": 0, "total_success": 0, "total_fail": 0}
    bo.self_model_data["prediction_error_history"] = []
    bo.self_model_data["meta_cognition"] = {}
    bo.self_model_data["counterfactual_stats"] = {}
    bo.self_model_data["confidence"] = 0.0
    bo._BUS_LOG_ENABLED = False
    bo.init_all_organs()


class MockCtx:
    def __init__(self):
        self.traces = []
        self.knowledge = {}
        self.pe_history = []

    def add_knowledge(self, k, v, source=""):
        self.knowledge[k] = v

    def add_trace(self, scene, action, finished=True, **kw):
        self.traces.append({"scene": scene, "action": action, "action_finished": finished, **kw})


errors = []


def check(name, cond, detail=""):
    print(f"  {'✅' if cond else '❌'} {name}" + (f"  → {detail}" if detail else ""))
    if not cond:
        errors.append(name)


# ======================================================================
print("=" * 64)
print("测试1：我-非我边界（origin=internal/external 稳定区分 + 内外统计）")
print("=" * 64)
reset()
ctx = MockCtx()

# 外部信号（用户输入 + 工具返回）
bo.emit_event("user_input", {"text": "你好"}, source="WORLD_MODEL", origin="external")
bo.emit_event("tool_result", {"tool": "web_search", "summary": "查询结果"}, source="WORLD_MODEL", origin="external")
# 内部信号（躯体状态）
bo.emit_event("bodystate_update", {"fatigue": 0.5, "resource_pressure": 0.3, "damage_level": 0.0},
              source="ORG-BODYSTATES", origin="internal")
# 记忆巩固（payload 携带记忆碎片本身的 origin：1 条外部经历 + 1 条内部思考）
bo.emit_event("mem_consolidated", {
    "thought_fragment": "经历:游戏菜单:点击", "focus": 0.8, "valence": 0.5,
    "origin": "external", "goal_tag": "游戏菜单:点击", "success": True, "subjective_time": 1.0,
}, source="ORG-CONSOLIDATE", origin="internal")
bo.emit_event("mem_consolidated", {
    "thought_fragment": "内省:整理记忆", "focus": 0.6, "valence": 0.0,
    "origin": "internal", "goal_tag": "内省:整理", "success": True, "subjective_time": 1.0,
}, source="ORG-CONSOLIDATE", origin="internal")
bo._dispatch_events()

# ORG-F 统计内外来源
bo.module_f_tick(ctx)
# ORG-A 写入长期记忆
bo.module_a_tick(ctx)
# ORG-E 处理 user_input/tool_result，写入工作记忆草稿区
bo.module_e_tick(ctx)

check("origin_stats 统计到 external", bo.origin_stats.get("external", 0) >= 3,
      f"origin_stats={bo.origin_stats}")
check("origin_stats 统计到 internal", bo.origin_stats.get("internal", 0) >= 1,
      f"origin_stats={bo.origin_stats}")

mem_origins = [m.get("origin") for m in bo.memory_library]
check("长期记忆库保留 origin=external 条目", "external" in mem_origins, f"{mem_origins}")
check("长期记忆库保留 origin=internal 条目", "internal" in mem_origins, f"{mem_origins}")

stack_origins = [t.get("origin") for t in bo.working_memory["context_stack"]]
check("工作记忆草稿区保留 external 碎片（user:/tool:）", "external" in stack_origins, f"{stack_origins}")

# 内外信号行为模式差异：external 事件的 source 均为外部入口(WORLD_MODEL)，internal 为器官内部
ext_sources = {e.get("source") for e in bo._event_log if e.get("origin") == "external"}
check("external 信号 source 均为外部入口", ext_sources == {"WORLD_MODEL"}, f"{ext_sources}")

# ======================================================================
print()
print("=" * 64)
print("测试2：自传记忆连续性（久远高权重经历 → 重放进 ORG-E）")
print("=" * 64)
reset()
ctx = MockCtx()

# 模拟长时间运行：注入 20 条记忆，主观时间从 1 递增到 20；前 3 条(subj_time=1,2,3)是久远高权重经历
for i in range(20):
    high = i < 3
    bo.emit_event("mem_consolidated", {
        "thought_fragment": f"久远记忆{i}" if high else f"近期记忆{i}",
        "focus": 0.95 if high else 0.5,
        "valence": 0.4,
        "origin": "external",
        "goal_tag": f"场景{i}:动作{i}",
        "success": True,
        "subjective_time": float(i + 1),
    }, source="ORG-CONSOLIDATE", origin="internal")
bo._dispatch_events()

# 触发记忆重放（REPLAY_INTERVAL_TICKS=100）
for _ in range(100):
    bo.organ_consolidate_tick(ctx)
bo._dispatch_events()

replays = bo.poll_replay_events("replay_thought_fragment", 50)
check("重放机制已触发", len(replays) >= 1, f"replay_thought_fragment × {len(replays)}")
replay_thoughts = [r["payload"].get("thought", "") for r in replays]
old_high = [f"久远记忆{i}" for i in range(3)]
hit_old_high = any(t in old_high for t in replay_thoughts)
check("久远(主观时间早)高权重经历被重放", hit_old_high,
      f"重放内容(前6)={replay_thoughts[:6]}")

# ======================================================================
print()
print("=" * 64)
print("测试3：自我模型演化（confidence/条目随经验动态变化）")
print("=" * 64)
reset()
ctx = MockCtx()

# 阶段A：刚启动，无经历
bo.emit_event("subjective_tick", {"subjective_clock": 1.0}, source="ORG-TIMESENSE", origin="internal")
bo._dispatch_events()
for _ in range(60):
    bo.organ_selfmodel_tick(ctx)
bo._dispatch_events()
conf_a = bo.self_model_data["confidence"]
cap_a = len(bo.self_model_data["capability"])
lim_a = len(bo.self_model_data["limitations"])
check("刚启动 confidence 低", conf_a <= 0.1, f"confidence={conf_a}")
check("刚启动 capability/limitations 条目少", cap_a == 0 and lim_a == 0,
      f"capability={cap_a}, limitations={lim_a}")

# 阶段B：积累大量成功经历
for i in range(15):
    bo.emit_event("mem_consolidated", {
        "thought_fragment": f"经历:场景{i}:动作{i}",
        "focus": 0.8, "valence": 0.5, "origin": "external",
        "goal_tag": f"场景{i}:动作{i}", "success": True, "subjective_time": float(i + 2),
    }, source="ORG-CONSOLIDATE", origin="internal")
bo._dispatch_events()
bo.self_model_data["meta"]["tick_counter"] = 0
for _ in range(60):
    bo.organ_selfmodel_tick(ctx)
bo._dispatch_events()
conf_b = bo.self_model_data["confidence"]
cap_b = len(bo.self_model_data["capability"])
check("积累经历后 confidence 上升", conf_b > conf_a, f"{conf_a} → {conf_b}")
check("积累经历后 capability 丰富", cap_b > cap_a, f"capability={cap_b} 条")

# 阶段C：同一目标连续失败 → limitations 新增
for _ in range(3):
    bo.emit_event("mem_consolidated", {
        "thought_fragment": "经历:危险区:穿越",
        "focus": 0.8, "valence": -0.6, "origin": "external",
        "goal_tag": "危险区:穿越", "success": False, "subjective_time": 20.0,
    }, source="ORG-CONSOLIDATE", origin="internal")
bo._dispatch_events()
bo.self_model_data["meta"]["tick_counter"] = 0
for _ in range(60):
    bo.organ_selfmodel_tick(ctx)
bo._dispatch_events()
conf_c = bo.self_model_data["confidence"]
lim_keys = [l["key"] for l in bo.self_model_data["limitations"]]
check("连续失败后 confidence 继续上升", conf_c >= conf_b, f"{conf_b} → {conf_c}")
check("连续失败后 limitations 新增条目", "危险区:穿越" in lim_keys, f"limitations={lim_keys}")

# ======================================================================
print()
print("=" * 64)
print("测试4：自我参与决策闭环（limitations 干预动机 + 抑制）")
print("=" * 64)
reset()
ctx = MockCtx()

# 4a：ORG-B 任务型目标生成时，局限内目标 drive 降权
bo.memory_library.append({"goal_tag": "游戏菜单:点击", "focus": 1.0, "weight_eff": 1.0})
bo.memory_library.append({"goal_tag": "商店:购买", "focus": 1.0, "weight_eff": 1.0})
limitations = [{"key": "游戏菜单:点击", "fail_rate": 0.7, "trials": 3}]
task_motives = bo._generate_task_motives(ctx, limitations)
drive_map = {m["goal"]: m["drive"] for m in task_motives}
check("任务型目标已生成(局限内+非局限)", "游戏菜单:点击" in drive_map and "商店:购买" in drive_map,
      f"{drive_map}")
if "游戏菜单:点击" in drive_map and "商店:购买" in drive_map:
    check("局限内目标 drive 被降权(×0.5)",
          drive_map["游戏菜单:点击"] < drive_map["商店:购买"],
          f"局限={drive_map['游戏菜单:点击']} vs 非局限={drive_map['商店:购买']}")

# 4b：ORG-INHIBIT 对局限内目标提高过滤阈值（0.3→0.6）
bo._self_limitations_inhibit = [{"key": "游戏菜单:点击"}]
bo.emit_event("candidate_motives", {"motives": [
    {"goal": "游戏菜单:点击", "drive": 0.5},   # 局限内 → 阈值0.6，0.5 被过滤
    {"goal": "商店:购买", "drive": 0.5},       # 非局限 → 阈值0.3，0.5 通过
]}, source="ORG-B", origin="internal")
bo._dispatch_events()
bo.organ_inhibit_tick(ctx)
bo._dispatch_events()
final_goals = []
for fg in bo.poll_replay_events("final_goals", 10):
    final_goals.extend(fg["payload"].get("goals", []))
check("局限内目标被 INHIBIT 过滤掉", "游戏菜单:点击" not in final_goals, f"final_goals={final_goals}")
check("非局限目标通过 INHIBIT", "商店:购买" in final_goals, f"final_goals={final_goals}")

# ======================================================================
print()
print("=" * 64)
print("测试5：幼年效应（早期大量低权重事件不固化，仅高 focus/valence 少数固化）")
print("=" * 64)
reset()
ctx = MockCtx()

bo.emit_event("subjective_tick", {"subjective_clock": 1.0}, source="ORG-TIMESENSE", origin="internal")
# 大量低 focus + 低 valence 琐碎碎片（早期经历，应被遗忘）
for i in range(40):
    bo.wm_push_thought(f"琐碎经历{i}", 0.1, valence=0.0, origin="internal")
# 少数高 focus 或高 valence 碎片（应被巩固）
bo.wm_push_thought("重要经历A", 0.9, valence=0.5, origin="external", goal_tag="重要:经历A", success=True)
bo.wm_push_thought("强烈情绪B", 0.1, valence=0.9, origin="external", goal_tag="情绪:经历B", success=True)
bo._dispatch_events()

# ORG-E 广播 wm_snapshot（含 context_stack）→ CONSOLIDATE 筛选固化
bo.module_e_tick(ctx)
bo._dispatch_events()
bo.organ_consolidate_tick(ctx)
bo._dispatch_events()
bo.module_a_tick(ctx)   # 写入 memory_library

consolidated_count = len(bo.memory_library)
mem_thoughts = [m["thought"] for m in bo.memory_library]
check("低权重琐碎碎片大部分被丢弃（未固化）", consolidated_count <= 2,
      f"固化 {consolidated_count} 条 / 注入 42 条")
check("高 focus 碎片被固化", "重要经历A" in mem_thoughts, f"{mem_thoughts}")
check("高 valence 碎片被固化", "强烈情绪B" in mem_thoughts, f"{mem_thoughts}")
check("琐碎碎片未进入长期记忆", not any("琐碎" in t for t in mem_thoughts), f"{mem_thoughts}")

# ======================================================================
print()
print("=" * 64)
if errors:
    print(f"❌ 阶段六验证：{len(errors)} 项未通过 → {errors}")
    sys.exit(1)
else:
    print("✅ 阶段六验证：5 项客观测试全部通过")
    sys.exit(0)
