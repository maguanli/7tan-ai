# -*- coding: utf-8 -*-
"""阶段三 SELFMODEL 5 处修复的真机验证脚本"""
import sys, os
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import importlib
import src.agent.bionic_organs as bo
importlib.reload(bo)

# 重置状态（直接重新 init）
bo.organ_registry.clear()
bo._event_queue.clear()
bo._event_log.clear()
bo._replay_buffer.clear()
bo._subscriptions.clear()
bo._inboxes.clear()
bo.init_all_organs()

print("=== 注册器官 ===")
print(f"注册: {len(bo.organ_registry)} 个, 启用: {len([c for c,o in bo.organ_registry.items() if o.enabled])} 个")

# ========== 注入事件（模拟外部数据源，全部通过 emit + dispatch 进 replay buffer）==========
# 1. 记忆样本（新结构：单条 thought_fragment，CONSOLIDATE 当前产出格式）
mem_samples = [
    {"thought_fragment": "游戏菜单:点击", "focus": 0.9, "valence": 0.5, "origin": "internal",
     "subjective_time": 1.0, "weight_eff": 1.0, "goal_tag": "game_menu:click", "pe": 0.1, "success": True},
    {"thought_fragment": "游戏菜单:点击", "focus": 0.8, "valence": -0.4, "origin": "internal",
     "subjective_time": 2.0, "weight_eff": 1.0, "goal_tag": "game_menu:click", "pe": 0.2, "success": False},
    {"thought_fragment": "游戏菜单:点击", "focus": 0.7, "valence": 0.3, "origin": "external",
     "subjective_time": 3.0, "weight_eff": 1.0, "goal_tag": "game_menu:click", "pe": 0.15, "success": False},
    {"thought_fragment": "商店:购买", "focus": 0.6, "valence": 0.4, "origin": "internal",
     "subjective_time": 4.0, "weight_eff": 1.0, "goal_tag": "shop:buy", "pe": 0.3, "success": True},
    {"thought_fragment": "商店:购买", "focus": 0.5, "valence": 0.2, "origin": "external",
     "subjective_time": 5.0, "weight_eff": 1.0, "goal_tag": "shop:buy", "pe": 0.35, "success": True},
]
for m in mem_samples:
    bo.emit_event("mem_consolidated", m, source="ORG-CONSOLIDATE", origin="internal")

# 2. 假设样本（accepted）
bo.emit_event("hypothesis_update", {"key": "game_menu:click", "status": "accepted", "score": 1.0},
              source="ORG-F", origin="internal")
bo.emit_event("hypothesis_update", {"key": "shop:buy", "status": "accepted", "score": 0.8},
              source="ORG-F", origin="internal")

# 3. 候选动机
bo.emit_event("candidate_motives", {"motives": [{"goal": "reduce_load", "drive": 0.8}]},
              source="ORG-B", origin="internal")
bo.emit_event("candidate_motives", {"motives": [{"goal": "consolidate_memory", "drive": 0.9}]},
              source="ORG-B", origin="internal")

# 4. 最终执行目标（ORG-INHIBIT 产出）
bo.emit_event("final_goals", {"goals": ["reduce_load", "explore"]}, source="ORG-INHIBIT", origin="internal")

# 5. PE/LP 预测误差（ORG-B 现在会 emit，这里直接注入等价事件）
bo.emit_event("pe_update", {"pe": 0.4, "lp": 0.2}, source="ORG-B", origin="internal")
bo.emit_event("pe_update", {"pe": 0.3, "lp": 0.1}, source="ORG-B", origin="internal")

# 6. 本体信号
bo.emit_event("bodystate_update", {"fatigue": 0.6, "resource_pressure": 0.8, "damage_level": 0.0},
              source="ORG-BODYSTATES", origin="internal")

# 7. 主观时间（SELFMODEL 需要）
bo.emit_event("subjective_tick", {"subjective_clock": 10.0, "time_dilation": 1.0},
              source="ORG-TIMESENSE", origin="internal")

# 手动分发，让所有事件进 replay buffer
bo._dispatch_events()

print(f"\n=== 分发后 replay buffer 键 ===")
print(sorted(bo._replay_buffer.keys()))

# ========== 跑 60 次 SELFMODEL tick 触发归纳 ==========
for i in range(1, 61):
    bo.organ_selfmodel_tick()

smd = bo.self_model_data
print(f"\n=== self_model_data（第60次归纳）===")
print(f"history_summary   = {smd['history_summary']}")
print(f"origin_distribution = {smd.get('origin_distribution')}")
print(f"capability        = {smd['capability']}")
print(f"limitations       = {smd['limitations']}")
print(f"preferred_motives = {smd['preferred_motives']}")
print(f"internal_signature = {smd['internal_signature']}")
print(f"confidence        = {smd['confidence']}")

# ========== 断言验证 5 处修复 ==========
errors = []

# 缺陷1：记忆样本不再空转（history_summary 应有数据）
if smd['history_summary']['total_goal'] == 0:
    errors.append("缺陷1未修复：history_summary 仍为空（记忆样本空转）")

# 缺陷5：success 字段判断（capability 里 game_menu:click 应该有数据）
keys = [c.get('key') for c in smd['capability']]
if 'game_menu:click' not in keys:
    errors.append(f"缺陷5未修复：capability 缺少 game_menu:click，实际 keys={keys}")

# 缺陷2：origin 区分
od = smd.get('origin_distribution', {})
if od.get('internal', 0) <= 0 or od.get('external', 0) <= 0:
    errors.append(f"缺陷2未修复：origin_distribution 未区分内外，实际={od}")

# 缺陷3：final_goals 读入（preferred_motives 应含 explore）
pm_tags = [p.get('motive_tag') for p in smd['preferred_motives']]
if 'explore' not in pm_tags:
    errors.append(f"缺陷3未修复：final_goals 的 explore 未并入 preferred_motives，实际={pm_tags}")

# 缺陷4：PE 进总线（internal_signature 应含 pe_avg/lp_avg）
if 'pe_avg' not in smd['internal_signature'] or 'lp_avg' not in smd['internal_signature']:
    errors.append(f"缺陷4未修复：internal_signature 缺少 pe_avg/lp_avg，实际={smd['internal_signature']}")

print(f"\n=== 断言结果 ===")
if errors:
    print("❌ 失败项：")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("✅ 5 处修复全部验证通过")
