# -*- coding: utf-8 -*-
"""阶段五元认知 A/B/C 三处修复的真机验证脚本"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

import importlib
import src.agent.bionic_organs as bo
importlib.reload(bo)

# 重置状态
bo.organ_registry.clear()
bo._event_queue.clear()
bo._event_log.clear()
bo._replay_buffer.clear()
bo._subscriptions.clear()
bo._inboxes.clear()
bo.init_all_organs()


class MockCtx:
    def __init__(self):
        self.traces = []
        self.knowledge = {}
    def add_knowledge(self, k, v, source=""):
        self.knowledge[k] = v


errors = []

# ========== A/B 前置：订阅表验证 ==========
print("=== 订阅表验证 ===")
def has_sub(etype, code):
    return code in bo._subscriptions.get(etype, [])

checks = [
    ("hypothesis_update → ORG-F", has_sub("hypothesis_update", "ORG-F")),
    ("pe_update → ORG-F", has_sub("pe_update", "ORG-F")),
    ("meta_cognition_update → ORG-SELFMODEL", has_sub("meta_cognition_update", "ORG-SELFMODEL")),
    ("counterfactual_result → ORG-SELFMODEL", has_sub("counterfactual_result", "ORG-SELFMODEL")),
    ("counterfactual_result → ORG-E", has_sub("counterfactual_result", "ORG-E")),
]
for name, ok in checks:
    print(f"  {'✅' if ok else '❌'} {name}")
    if not ok:
        errors.append(f"订阅缺失：{name}")

# ========== B：ORG-F 对自身思维做统计（元认知） ==========
print("\n=== B：ORG-F 元认知统计 ===")
ctx = MockCtx()
# 注入自身假设更新（接受/拒绝）+ 预测误差
bo.emit_event("hypothesis_update", {"key": "a:b", "status": "accepted"}, source="ORG-F", origin="internal")
bo.emit_event("hypothesis_update", {"key": "c:d", "status": "accepted"}, source="ORG-F", origin="internal")
bo.emit_event("hypothesis_update", {"key": "e:f", "status": "rejected"}, source="ORG-F", origin="internal")
bo.emit_event("pe_update", {"pe": 0.4, "lp": 0.2}, source="ORG-B", origin="internal")
bo.emit_event("pe_update", {"pe": 0.2, "lp": 0.1}, source="ORG-B", origin="internal")
bo._dispatch_events()

meta_event_seen = None
for i in range(1, 21):
    bo.module_f_tick(ctx)
    # 第 20 次触发后，事件进 queue，dispatch 一下让 SELFMODEL 能回放，同时检查
    if i == 20:
        bo._dispatch_events()
        evs = bo.poll_replay_events("meta_cognition_update", 5)
        if evs:
            meta_event_seen = evs[-1]

print(f"  meta_cognition_stats = {bo.meta_cognition_stats}")
print(f"  meta_cognition_update 事件 = {meta_event_seen}")

if bo.meta_cognition_stats["hypo_accepted"] != 2:
    errors.append(f"B失败：hypo_accepted 应为 2，实际 {bo.meta_cognition_stats['hypo_accepted']}")
if bo.meta_cognition_stats["hypo_rejected"] != 1:
    errors.append(f"B失败：hypo_rejected 应为 1，实际 {bo.meta_cognition_stats['hypo_rejected']}")
if len(bo.meta_cognition_stats["pe_samples"]) != 2:
    errors.append(f"B失败：pe_samples 应为 2，实际 {len(bo.meta_cognition_stats['pe_samples'])}")
if meta_event_seen is None:
    errors.append("B失败：第20 tick 未产出 meta_cognition_update 事件")
else:
    p = meta_event_seen.get("payload", {})
    if p.get("hypo_accept_rate") is None or p.get("pe_mean") is None:
        errors.append(f"B失败：meta_cognition_update payload 缺 accept_rate/pe_mean，实际 {p}")
    print(f"  hypo_accept_rate = {p.get('hypo_accept_rate')}, pe_mean = {p.get('pe_mean')}")

# ========== C：ORG-SIMULATE 反事实推演 ==========
print("\n=== C：ORG-SIMULATE 反事实推演 ===")
ctx.traces = [
    {"scene": "游戏菜单", "action": "点击", "action_finished": True, "weight_eff": 1.0},
    {"scene": "游戏菜单", "action": "滑动", "action_finished": False, "weight_eff": 1.0},
]
# 注入 wm_snapshot，携带任务型活跃目标
bo.emit_event("wm_snapshot", {"active_goals": ["游戏菜单:点击"], "context_stack": []},
              source="ORG-E", origin="internal")
bo._dispatch_events()
bo.organ_simulate_tick(ctx)
bo._dispatch_events()
counter_evs = bo.poll_replay_events("counterfactual_result", 10)
print(f"  counterfactual_result 事件数 = {len(counter_evs)}")
for ev in counter_evs:
    print(f"    {ev.get('payload')}")

if len(counter_evs) == 0:
    errors.append("C失败：未产出 counterfactual_result 反事实推演事件")
else:
    p = counter_evs[0].get("payload", {})
    # 原目标 游戏菜单:点击（成功1次，conf=1.0），替代动作应为 滑动（失败，conf=0.0）
    if p.get("original_goal") != "游戏菜单:点击":
        errors.append(f"C失败：original_goal 应为 游戏菜单:点击，实际 {p.get('original_goal')}")
    if p.get("alternative_goal") != "游戏菜单:滑动":
        errors.append(f"C失败：alternative_goal 应为 游戏菜单:滑动，实际 {p.get('alternative_goal')}")
    print(f"  原目标={p.get('original_goal')} conf={p.get('original_conf')}, "
          f"替代={p.get('alternative_goal')} conf={p.get('alternative_conf')}, delta={p.get('delta')}")

# ========== A：SELFMODEL 留痕 + 归纳元认知/反事实 ==========
print("\n=== A：SELFMODEL 留痕与元认知归纳 ===")
# 补充注入记忆/动机/目标/本体/主观时间，让 SELFMODEL 归纳有完整素材
bo.emit_event("mem_consolidated",
              {"thought_fragment": "游戏菜单:点击", "focus": 0.9, "valence": 0.5, "origin": "internal",
               "goal_tag": "game_menu:click", "success": True}, source="ORG-CONSOLIDATE", origin="internal")
bo.emit_event("candidate_motives", {"motives": [{"goal": "reduce_load", "drive": 0.8}]},
              source="ORG-B", origin="internal")
bo.emit_event("final_goals", {"goals": ["reduce_load"]}, source="ORG-INHIBIT", origin="internal")
bo.emit_event("bodystate_update", {"fatigue": 0.6, "resource_pressure": 0.8}, source="ORG-BODYSTATES", origin="internal")
bo.emit_event("subjective_tick", {"subjective_clock": 10.0}, source="ORG-TIMESENSE", origin="internal")
bo._dispatch_events()

for i in range(1, 61):
    bo.organ_selfmodel_tick()

smd = bo.self_model_data
print(f"  prediction_error_history = {smd.get('prediction_error_history')}")
print(f"  meta_cognition = {smd.get('meta_cognition')}")
print(f"  counterfactual_stats = {smd.get('counterfactual_stats')}")

if "prediction_error_history" not in smd:
    errors.append("A失败：self_model_data 缺少 prediction_error_history 字段")
elif len(smd["prediction_error_history"]) == 0:
    errors.append("A失败：prediction_error_history 为空（PE 留痕未生效）")

if "meta_cognition" not in smd:
    errors.append("A失败：self_model_data 缺少 meta_cognition 字段")

if "counterfactual_stats" not in smd:
    errors.append("A失败：self_model_data 缺少 counterfactual_stats 字段")
else:
    cs = smd["counterfactual_stats"]
    if cs.get("total", 0) <= 0:
        errors.append(f"A失败：counterfactual_stats.total 应为 >0，实际 {cs}")

print("\n=== 断言结果 ===")
if errors:
    print("❌ 失败项：")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("✅ A/B/C 三处修复全部验证通过")
