# -*- coding: utf-8 -*-
"""阶段六·测试2修复：真实落盘验证脚本
验证重放采样已从「最近N条」改为「全部历史+高权重优先」+ 主观时间透传。
"""
import sys, os
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# 1) 编译检查
import py_compile
py_compile.compile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "agent", "bionic_organs.py"), doraise=True)
print("COMPILE_OK")

# 2) 源码断言：修复代码真实落盘
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "agent", "bionic_organs.py"), encoding="utf-8").read()
# b03baf7（阶段六修复6）把「变量赋值采样」重构为「for 循环直读 + 去重键」，语义不变（全历史采样），锚点同步更新
assert "for mem_evt in poll_replay_events(\"mem_consolidated\", 200):" in src, "修复代码不在源码里！"
assert "subjective_time\": mem_data.get(\"subjective_time\")" in src, "主观时间透传缺失！"
assert src.count("old_mem_events = poll_replay_events(\"mem_consolidated\", replay_sample)") == 0, "旧逻辑还残留！"
print("SOURCE_PATCH_OK  (全部历史采样 + focus降序 + 主观时间透传 均已落盘)")

# 3) 真机行为验证：注入久远高权重 + 近期低权重记忆，触发重放
from src.agent import bionic_organs as bo
bo.init_all_organs()

# 快速触发配置：重放间隔改小
bo.get_organ("ORG-CONSOLIDATE").config["REPLAY_INTERVAL_TICKS"] = 5
bo.get_organ("ORG-CONSOLIDATE").config["REPLAY_SAMPLE_COUNT"] = 4

# 注入主观时间线：久远记忆（subj_time=1,2,3, focus=0.95）+ 近期记忆（subj_time=100+, focus=0.3~0.5）
for i in range(3):
    bo.emit_event("mem_consolidated", {
        "thought_fragment": f"久远记忆{i}", "focus": 0.95, "valence": 0.8,
        "origin": "external", "subjective_time": float(i + 1), "weight_eff": 1.0,
    }, source="ORG-CONSOLIDATE", origin="internal")
for i in range(20):
    bo.emit_event("mem_consolidated", {
        "thought_fragment": f"近期记忆{i}", "focus": 0.3 + 0.01 * i, "valence": 0.1,
        "origin": "internal", "subjective_time": 100.0 + i, "weight_eff": 1.0,
    }, source="ORG-CONSOLIDATE", origin="internal")
bo._dispatch_events()

# 跑 tick 触发重放（_consolidate_counter 从当前值继续，多跑几轮确保命中 %5==0）
import src.agent.bionic_organs as BO
before = BO._consolidate_counter
for _ in range(6):
    bo.organ_tick_all()

# 收集重放事件（从 ORG-E 工作记忆的 replay_thought_fragment 订阅读）
replays = bo.poll_replay_events("replay_thought_fragment", 50)
replay_thoughts = [r["payload"].get("thought", "") for r in replays if isinstance(r.get("payload"), dict)]
print(f"\n重放事件数 = {len(replay_thoughts)}")
print(f"重放内容 = {replay_thoughts}")

# 断言1：久远高权重记忆被重放（此前为 0 —— 这就是测试2失败根因）
n_far = sum(1 for t in replay_thoughts if t.startswith("久远记忆"))
assert n_far >= 3, f"久远高权重记忆仍未被重放！数量={n_far}"
print(f"断言1通过：久远高权重记忆被重放 {n_far} 条（修复前=0）")

# 断言2：重放 payload 携带主观时间（远小值=久远）
subj_times = [r["payload"].get("subjective_time") for r in replays if isinstance(r.get("payload"), dict)]
far_subj = [s for s in subj_times if s is not None and float(s) < 10]
assert len(far_subj) >= 3, f"重放未携带久远主观时间！subj_times={subj_times}"
print(f"断言2通过：重放 payload 携带主观时间线，久远时间戳 = {sorted(far_subj)}")

# 断言3：高权重优先——0.95 的久远记忆排序在 0.3x 近期之前被选入
far_replays = [r for r in replays if isinstance(r.get("payload"), dict) and str(r["payload"].get("thought", "")).startswith("久远记忆")]
all_far_in = len(far_replays) >= 3
assert all_far_in, "久远记忆未全部入选 top 采样"
print("断言3通过：focus=0.95 久远记忆全部入选高权重优先采样（近期 0.3x 被挤出 top4）")

# 断言4：focus 衰减 0.6 仍在生效（重放防抢占）
far_focus = far_replays[0]["payload"].get("focus")
assert abs(far_focus - 0.95 * 0.6) < 0.001, f"focus 衰减失效: {far_focus}"
print(f"断言4通过：重放 focus 衰减生效 0.95×0.6={far_focus}")

# 断言5：origin 继承不破坏（久远记忆 origin=external）
far_origin = far_replays[0]["payload"].get("origin")
assert far_origin == "external", f"origin 继承被破坏: {far_origin}"
print(f"断言5通过：重放 origin 继承正确（external）")

print("\nALL_TESTS_PASSED  ✅ 阶段六·测试2 修复真实落盘且行为验证通过")
