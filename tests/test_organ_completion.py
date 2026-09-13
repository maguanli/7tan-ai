# -*- coding: utf-8 -*-
"""器官业务逻辑补全验证：VALENCE 细化 / CONSOLIDATE 重放反哺 / SIMULATE 完善 / SELFMODEL mind_flaws / SPEECH 自述层。"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"D:\7tan\7tanAI")

from src.agent import bionic_organs as bo

# 测试卫生：器官状态自动落盘重定向到临时文件，避免污染真实 data/tan_model_organs.json
# （本测试跑大量 organ_tick_all，会周期触发 save_organ_state()）
import tempfile as _tf
from pathlib import Path as _P
bo._ORGAN_STATE_PATH = _P(_tf.mkdtemp(prefix="organ_state_test_")) / "state.json"

PASS = []
FAIL = []

def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"{'✅ PASS' if cond else '❌ FAIL'}: {name} {detail}")


# ================= 测试1：VALENCE 躯体/认知效价区分 =================
bo.init_all_organs()
bo._event_log.clear(); bo._replay_buffer.clear()
bo.emit_event("bodystate_update", {"fatigue": 0.8, "resource_pressure": 0.2, "damage_level": 0.0},
              source="ORG-BODYSTATES", origin="internal")
bo.emit_event("hypothesis_update", {"key": "场景A:动作X", "status": "rejected"}, source="ORG-F", origin="internal")
bo.organ_tick_all(None)
val_events = [e for e in bo._event_log if e["event_type"] == "valence_tag"]
som = [e for e in val_events if e["payload"].get("source_type") == "somatic"]
cog = [e for e in val_events if e["payload"].get("source_type") == "cognitive"]
check("1a 躯体效价(fatigue_high)", any(e["payload"].get("reason") == "fatigue_high" for e in som),
      f"somatic_tags={len(som)}")
check("1b 认知效价(hypo_rejected)", any(e["payload"].get("reason") == "hypo_rejected" for e in cog),
      f"cognitive_tags={len(cog)}")
# mood_state 周期广播（VALENCE_MOOD_INTERVAL=30）
for _ in range(35):
    bo.organ_tick_all(None)
mood = [e for e in bo._event_log if e["event_type"] == "mood_state"]
check("1c mood_state 心境综合广播", len(mood) >= 1,
      f"payload={mood[-1]['payload'] if mood else None}")

# ================= 测试2：CONSOLIDATE 重放反哺（rehearsal 复述强化） =================
bo.emit_event("mem_consolidated", {"thought_fragment": "重放反哺测试记忆", "focus": 0.9, "valence": 0.5,
                                   "origin": "internal", "subjective_time": 1.0, "weight_eff": 1.0},
              source="ORG-CONSOLIDATE", origin="internal")
bo.organ_tick_all(None)
mem = [m for m in bo.memory_library if m.get("thought") == "重放反哺测试记忆"]
check("2a 记忆入库", len(mem) == 1)
if mem:
    w_before = float(mem[0]["weight_eff"])
    bo.emit_event("replay_thought_fragment", {"thought": "重放反哺测试记忆", "focus": 0.54, "valence": 0.5,
                                              "origin": "internal", "rehearsal": True},
                  source="ORG-CONSOLIDATE", origin="internal")
    bo.organ_tick_all(None)
    w_after = float(mem[0]["weight_eff"])
    check("2b 重放反哺权重提升(+0.1)", w_after > w_before + 0.05, f"{w_before:.4f} → {w_after:.4f}")

# ================= 测试3：SIMULATE 动作级置信度 =================
class FakeCtx:
    def __init__(self):
        self.traces = [
            {"scene": "商店", "action": "购买", "action_finished": False, "weight_eff": 1.0},
            {"scene": "商店", "action": "购买", "action_finished": False, "weight_eff": 1.0},
            {"scene": "商店", "action": "浏览", "action_finished": True, "weight_eff": 1.0},
        ]
ctx = FakeCtx()
c_buy = bo._simulate_confidence(ctx, "商店", "购买", set())
c_browse = bo._simulate_confidence(ctx, "商店", "浏览", set())
c_new = bo._simulate_confidence(ctx, "新场景", "探索", set())
c_other = bo._simulate_confidence(ctx, "商店", "砍价", set())
check("3a 同场景同动作主证据(购买0/2)", c_buy == 0.0, f"conf={c_buy}")
check("3b 同场景同动作主证据(浏览1/1)", c_browse == 1.0, f"conf={c_browse}")
check("3c 无经验中性0.5(非0.0)", c_new == 0.5, f"conf={c_new}")
check("3d 同场景其他动作弱参考×0.3", abs(c_other - 0.1) < 0.02, f"conf={c_other}")

# ================= 测试4：反事实推演选最优替代（非字母序第一） =================
bo.sim_scenario_pool.clear()
bo._event_log.clear(); bo._replay_buffer.clear()
bo.working_memory["active_goals"] = ["商店:购买"]
bo.emit_event("wm_snapshot", {"active_goals": ["商店:购买"], "context_stack": []},
              source="ORG-E", origin="internal")
bo.organ_tick_all(ctx)
cf_events = [e for e in bo._event_log if e["event_type"] == "counterfactual_result"]
check("4a 反事实事件产出", len(cf_events) >= 1, f"count={len(cf_events)}")
# 注意：organ_tick_all 全器官联跑时，ORG-E 上一轮广播的 wm_snapshot（含稳态动机 reduce_load 等）
# 也会进入 SIMULATE 推演池，因此必须按 original_goal 过滤出本测试注入的「商店:购买」目标。
cf_shop = [e for e in cf_events if e["payload"].get("original_goal") == "商店:购买"]
if cf_shop:
    p = cf_shop[0]["payload"]
    check("4b 选最优替代(浏览conf1.0)而非字母序", p.get("alternative_goal") == "商店:浏览" and p.get("delta", 0) > 0.9,
          f"alt={p.get('alternative_goal')} delta={p.get('delta')} best_alt={p.get('best_alt')}")
else:
    check("4b 选最优替代(浏览conf1.0)而非字母序", False, "未找到 original_goal=商店:购买 的反事实事件")
sim_events = [e for e in bo._event_log if e["event_type"] == "simulation_result"]
if sim_events:
    check("4c simulation_result 多维化(expected_valence/limit_hit)",
          "expected_valence" in sim_events[0]["payload"] and "limit_hit" in sim_events[0]["payload"],
          f"payload_keys={sorted(sim_events[0]['payload'].keys())}")

# ================= 测试5：SELFMODEL mind_flaws 思维缺陷归纳 =================
bo.SELFMODEL_UPDATE_INTERVAL = 2   # 加速测试：2 tick 归纳一次
bo.self_model_data["meta"]["tick_counter"] = 0   # 重置归纳周期计数（前序测试已累加，对齐 %2==0 触发）
bo._replay_buffer.clear()
# 实际成功率 0.2（1成功4失败）+ 推演置信度 0.9 → calibration_gap=0.7 → self_overconfident
for i, ok in enumerate([True, False, False, False, False]):
    bo.emit_event("mem_consolidated", {"thought_fragment": f"战场经历{i}", "focus": 0.8, "valence": 0.3,
                                       "origin": "internal", "subjective_time": 5.0, "weight_eff": 1.0,
                                       "goal_tag": "战场:冲锋", "success": ok},
                  source="ORG-CONSOLIDATE", origin="internal")
for _ in range(3):
    bo.emit_event("simulation_result", {"scene": "战场", "action": "冲锋", "sim_confidence": 0.9},
                  source="ORG-SIMULATE", origin="internal")
for _ in range(2):
    bo.emit_event("hypothesis_update", {"key": "战场:冲锋", "status": "rejected"}, source="ORG-F", origin="internal")
bo.organ_tick_all(None)
bo.organ_tick_all(None)
flaws = bo.self_model_data.get("mind_flaws") or []
mc = bo.self_model_data.get("meta_cognition") or {}
check("5a self_overconfident 归纳", any(f.get("type") == "self_overconfident" for f in flaws),
      f"flaws={[f.get('type') for f in flaws]}")
check("5b calibration_gap 计算", mc.get("calibration_gap") is not None and mc.get("calibration_gap") > 0.2,
      f"gap={mc.get('calibration_gap')} sim_conf={mc.get('sim_conf_mean')} actual={mc.get('actual_success_rate')}")
check("5c repeated_falsified_hypothesis 归纳", any(f.get("type") == "repeated_falsified_hypothesis" for f in flaws),
      f"keys={[f.get('keys') for f in flaws if f.get('type')=='repeated_falsified_hypothesis']}")
sm_events = [e for e in bo._event_log if e["event_type"] == "selfmodel_update"]
check("5d selfmodel_update 广播携带 mind_flaws", sm_events and "mind_flaws" in sm_events[-1]["payload"])

# ================= 测试6：SPEECH 自述层（忠实读数转述） =================
bo.speech_state.update({
    "fatigue": 0.8, "confidence": 0.15,
    "history_summary": {"total_goal": 5, "total_success": 1},
    "mind_flaws": [{"type": "self_overconfident", "gap": 0.7}],
    "mood": {"somatic_valence": -0.4, "cognitive_valence": -0.35, "overall_valence": -0.375},
})
report = bo.generate_self_report()
check("6a 疲劳自述(我感觉很累)", "我感觉很累" in report, f"report={report[:80]}")
check("6b 自我模型模糊自述", "自我形象还模糊" in report)
check("6c 思维缺陷自述(过度自信)", "过度自信" in report)
check("6d 躯体/认知效价自述", "躯体效价" in report and "认知效价" in report)
# SPEECH 状态缓存由订阅事件刷新（验证 tick 刷新链路）
bo._replay_buffer.clear(); bo._event_log.clear()
bo.emit_event("bodystate_update", {"fatigue": 0.55, "resource_pressure": 0.1, "damage_level": 0.0},
              source="ORG-BODYSTATES", origin="internal")
bo.organ_tick_all(None)
check("6e SPEECH 订阅刷新状态缓存", abs(float(bo.speech_state.get("fatigue", 0.0)) - 0.55) < 1e-6 or bo.speech_state.get("fatigue") == 0.55,
      f"speech_state.fatigue={bo.speech_state.get('fatigue')}")

# ================= 测试7：memory_library 权重淘汰（非FIFO） =================
bo.memory_library.clear()
for i in range(205):
    bo.memory_library.append({"thought": f"m{i}", "focus": 0.5, "valence": 0.0,
                              "origin": "internal", "subjective_time": float(i),
                              "weight_eff": 0.05 if i < 100 else 1.5})
bo.emit_event("mem_consolidated", {"thought_fragment": "新记忆触发淘汰", "focus": 0.9, "valence": 0.5,
                                   "origin": "internal", "subjective_time": 999.0, "weight_eff": 1.0},
              source="ORG-CONSOLIDATE", origin="internal")
bo.organ_tick_all(None)
check("7a 容量控制在200内", len(bo.memory_library) <= 200, f"len={len(bo.memory_library)}")
low_left = sum(1 for m in bo.memory_library if m.get("weight_eff") is not None and float(m["weight_eff"]) < 0.1
               and str(m.get("thought", "")).startswith("m"))
high_left = sum(1 for m in bo.memory_library if m.get("weight_eff") is not None and float(m["weight_eff"]) > 1.0
                and str(m.get("thought", "")).startswith("m"))
check("7b 低权重被淘汰、高权重保留(非FIFO)", low_left < 100 and high_left >= 100,
      f"low_left={low_left} high_left={high_left}")

# ================= 测试8：CONSOLIDATE 调参确认 =================
cfg = bo.get_organ("ORG-CONSOLIDATE").config
# b03baf7（阶段六修复6）将重放间隔从 50 调至 20（重放更快触达，采样数不变），此处同步断言
check("8a 重放间隔20/采样6", cfg.get("REPLAY_INTERVAL_TICKS") == 20 and cfg.get("REPLAY_SAMPLE_COUNT") == 6,
      f"config={cfg}")

# ================= 测试9：world_model 兼容（关键接口未被破坏） =================
try:
    from src.agent import world_model as wm
    check("9a world_model 模块导入", True, "")
except Exception as ex:
    check("9a world_model 模块导入", False, f"{ex}")
try:
    bo.module_speech_push("接口兼容测试")
    bo.wm_push_thought("碎片", 0.5)
    bo.module_a_bump(None, "s", "a")
    check("9b speech/wm/bump 接口存在", True, "")
except Exception as ex:
    check("9b speech/wm/bump 接口存在", False, f"{ex}")

# ================= 汇总 =================
print("\n" + "=" * 60)
print(f"总计: {len(PASS)} 通过 / {len(FAIL)} 失败")
if FAIL:
    print("失败项:", FAIL)
    sys.exit(1)
print("✅ 全部验证通过")
sys.exit(0)
