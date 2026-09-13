# -*- coding: utf-8 -*-
"""
阶段五元认知验证（严格对照文档三个表现）
表现① ORG-SIMULATE: 推演"如果我改变我的某个目标，我会发生什么"（反事实推演）
表现② ORG-F: 对自身过去的假设、自身预测误差建立新假设（对思维过程做统计）
表现③ ORG-SELFMODEL: 迭代更新——不仅记录外部成败，还记录"我之前预测错了"的思维历史
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

import src.agent.bionic_organs as bo

# ---------- 重置环境 ----------
bo.organ_registry.clear()
bo._event_queue.clear()
bo._event_log.clear()
bo._replay_buffer.clear()
bo._subscriptions.clear()
bo._inboxes.clear()
bo.init_all_organs()
bo.sim_scenario_pool.clear()
bo._self_limitations_sim = []
# 重置元认知统计（fresh process 理论上是干净的，双保险）
bo.meta_cognition_stats["hypo_accepted"] = 0
bo.meta_cognition_stats["hypo_rejected"] = 0
bo.meta_cognition_stats["pe_samples"] = []
bo.meta_cognition_stats["meta_hypotheses"] = []
bo._meta_cognition_counter = 0
bo.self_model_data["meta"]["tick_counter"] = 0


class MockCtx:
    """带轨迹的上下文：scene/action 供推演与反事实使用"""
    def __init__(self):
        self.traces = [
            {"scene": "游戏菜单", "action": "点击", "result": "success"},
            {"scene": "游戏菜单", "action": "滑动", "result": "success"},
            {"scene": "商店", "action": "购买", "result": "fail"},
        ]
        self.knowledge = {}
    def add_knowledge(self, k, v, source=""):
        self.knowledge[k] = v


errors = []
def check(name, cond, detail=""):
    print(f"  {'✅' if cond else '❌'} {name}" + (f"  → {detail}" if detail else ""))
    if not cond:
        errors.append(name)

# ==================================================================
print("=" * 62)
print("【表现①】ORG-SIMULATE 反事实推演：如果我改变目标，会发生什么")
print("=" * 62)
ctx = MockCtx()

# 1. 工作记忆快照携带活跃目标 → SIMULATE
bo.emit_event("wm_snapshot", {"active_goals": ["游戏菜单:点击", "商店:购买"]},
              source="ORG-E", origin="internal")
bo._dispatch_events()

# 2. 跑一轮 SIMULATE
bo.organ_simulate_tick(ctx)
bo._dispatch_events()   # 让 counterfactual_result 进入回放缓冲（供 SELFMODEL 用）

sim_results = bo.poll_replay_events("simulation_result", 20)
cf_results = bo.poll_replay_events("counterfactual_result", 20)

check("内部沙盒推演已执行", len(sim_results) >= 2, f"simulation_result × {len(sim_results)}")
check("反事实推演已产出", len(cf_results) >= 2, f"counterfactual_result × {len(cf_results)}")

cf_payloads = [r.get("payload", {}) for r in cf_results]
print(f"  反事实推演明细：")
for p in cf_payloads:
    print(f"    原目标={p.get('original_goal')} → 替代={p.get('alternative_goal')} "
          f"orig_conf={p.get('original_conf')} alt_conf={p.get('alternative_conf')} delta={p.get('delta')}")

has_cf_structure = all(
    p.get("original_goal") and p.get("alternative_goal")
    and isinstance(p.get("delta"), (int, float))
    for p in cf_payloads
)
check("每条反事实都含 原目标/替代目标/对比delta（回答'改变目标会怎样'）",
      len(cf_payloads) > 0 and has_cf_structure)
alt_not_same = all(
    p.get("alternative_goal") != p.get("original_goal") for p in cf_payloads
)
check("替代目标确实不同于原目标（真的在推演'改变'）", alt_not_same)

# ==================================================================
print()
print("=" * 62)
print("【表现②】ORG-F 对自身思维过程做统计（自身假设 + 预测误差 → 新假设）")
print("=" * 62)

# 1. 注入"自身思维产物"：自己过去的假设接受/拒绝记录 + 自己的预测误差
bo.emit_event("hypothesis_update", {"key": "游戏菜单:点击", "status": "accepted"},
              source="ORG-F", origin="internal")
bo.emit_event("hypothesis_update", {"key": "商店:购买", "status": "accepted"},
              source="ORG-F", origin="internal")
bo.emit_event("hypothesis_update", {"key": "迷宫:探索", "status": "rejected"},
              source="ORG-F", origin="internal")
bo.emit_event("pe_update", {"pe": 0.4, "lp": 0.2}, source="ORG-B", origin="internal")
bo.emit_event("pe_update", {"pe": 0.2, "lp": 0.1}, source="ORG-B", origin="internal")
bo._dispatch_events()

# 2. 跑 module_f_tick 直到 META_COGNITION_INTERVAL(=20) 触发归纳
for _ in range(20):
    bo.module_f_tick(ctx)
bo._dispatch_events()

stats = bo.meta_cognition_stats
check("统计了自身假设接受数", stats["hypo_accepted"] == 2, f"hypo_accepted={stats['hypo_accepted']}")
check("统计了自身假设拒绝数", stats["hypo_rejected"] == 1, f"hypo_rejected={stats['hypo_rejected']}")
check("收集了自身预测误差样本", len(stats["pe_samples"]) == 2, f"pe_samples={stats['pe_samples']}")

meta_events = bo.poll_replay_events("meta_cognition_update", 10)
check("ORG-F 广播了 meta_cognition_update（对思维的统计结果）", len(meta_events) >= 1)
if meta_events:
    mp = meta_events[-1].get("payload", {})
    print(f"  meta_cognition_update 内容: accept_rate={mp.get('hypo_accept_rate')} "
          f"pe_mean={mp.get('pe_mean')} meta_hypotheses={mp.get('meta_hypotheses')}")
    check("统计含自身假设接受率", mp.get("hypo_accept_rate") == 0.6667,
          f"accept_rate={mp.get('hypo_accept_rate')}")
    check("统计含自身预测误差均值", mp.get("pe_mean") is not None, f"pe_mean={mp.get('pe_mean')}")
    mh = mp.get("meta_hypotheses", [])
    check("对自身思维建立了【新假设】(self_hypo_*)", len(mh) >= 1, f"meta_hypotheses={mh}")

# ==================================================================
print()
print("=" * 62)
print("【表现③】ORG-SELFMODEL 迭代更新：记录'我之前预测错了'的思维历史")
print("=" * 62)

# 1. 前置：subjective_tick（SELFMODEL 必需）+ 外部成败记忆 + 元认知/反事实已在上文产生
bo.emit_event("subjective_tick", {"subjective_clock": 10.0}, source="ORG-TIMESENSE", origin="internal")
bo.emit_event("mem_consolidated", {
    "thought_fragment": "经历:游戏菜单:点击", "focus": 0.8, "valence": 0.5,
    "origin": "external", "goal_tag": "游戏菜单:点击", "success": True,
    "subjective_time": 10.0,
}, source="ORG-CONSOLIDATE", origin="internal")
bo.emit_event("mem_consolidated", {
    "thought_fragment": "经历:商店:购买", "focus": 0.7, "valence": -0.5,
    "origin": "external", "goal_tag": "商店:购买", "success": False,
    "subjective_time": 10.0,
}, source="ORG-CONSOLIDATE", origin="internal")
bo._dispatch_events()

# 2. 第一轮归纳周期：60 tick
for _ in range(60):
    bo.organ_selfmodel_tick(ctx)
bo._dispatch_events()

smd1 = dict(bo.self_model_data)   # 第一周期快照
pe_hist1 = smd1.get("prediction_error_history", [])
meta_cog1 = smd1.get("meta_cognition", {})
cf_stats1 = smd1.get("counterfactual_stats", {})
hist1 = smd1.get("history_summary", {})

print(f"  第一周期（tick 60 归纳）：")
print(f"    history_summary(外部成败)        = {hist1}")
print(f"    prediction_error_history(思维史) = {pe_hist1}")
print(f"    meta_cognition(关于自身思维)     = {meta_cog1}")
print(f"    counterfactual_stats(反事实统计) = {cf_stats1}")

check("仍记录外部成败（'不仅…还…'的'不仅'部分）",
      hist1.get("total_goal", 0) >= 2 and hist1.get("total_fail", 0) >= 1)
check("记录了预测误差【历史明细】（非仅均值，'我之前预测错了'留痕）",
      len(pe_hist1) == 2 and pe_hist1[0] == {"pe": 0.4, "lp": 0.2},
      f"{pe_hist1}")
check("自我模型吸收了 ORG-F 的思维统计", meta_cog1.get("hypo_accept_rate") == 0.6667)
check("自我模型吸收了反事实推演统计", cf_stats1.get("total", 0) >= 2,
      f"total={cf_stats1.get('total')}, better_alt={cf_stats1.get('better_alternative')}")
check("自我模型含'关于思维的假设'", len(meta_cog1.get("meta_hypotheses", [])) >= 1)

# 3. 第二轮归纳周期：新预测误差（0.8，"我又预测错了"）→ 验证迭代更新
bo.emit_event("pe_update", {"pe": 0.8, "lp": 0.4}, source="ORG-B", origin="internal")
bo.emit_event("pe_update", {"pe": 0.6, "lp": 0.3}, source="ORG-B", origin="internal")
bo._dispatch_events()
for _ in range(60):
    bo.organ_selfmodel_tick(ctx)
bo._dispatch_events()

smd2 = dict(bo.self_model_data)
pe_hist2 = smd2.get("prediction_error_history", [])
print(f"  第二周期（tick 120 归纳，新增 pe=0.8/0.6）：")
print(f"    prediction_error_history = {pe_hist2}")
check("迭代更新：预测误差历史随新经历更新（非一次性快照）",
      len(pe_hist2) == 4 and {"pe": 0.8, "lp": 0.4} in pe_hist2,
      f"{len(pe_hist2)} 条记录")

# 4. selfmodel_update 事件确实广播了
sm_events = bo.poll_replay_events("selfmodel_update", 5)
check("selfmodel_update 已广播（自我表征参与思考闭环）", len(sm_events) >= 1,
      f"× {len(sm_events)}")

# ==================================================================
print()
print("=" * 62)
if errors:
    print(f"❌ 验证失败 {len(errors)} 项：")
    for e in errors:
        print(f"   - {e}")
    sys.exit(1)
else:
    print("✅ 阶段五三个表现全部验证通过（机制层 + 迭代更新）")
