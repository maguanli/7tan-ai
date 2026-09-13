# -*- coding: utf-8 -*-
"""阶段六最终验证 v3：模拟真实一天运行，GLM-5.3 黑盒观测口径判定 5 项测试。

相对 v2 的修正：
  ① 优雅关机排空（drain tick）：每会话末尾追加 1 tick 再落盘——修复前会话末分发出的
     mem_consolidated 事件还躺在 ORG-A 收件箱里，重启清空收件箱 → 经历永久丢失
  ② 会话时序重设计（对齐事件传播滞后：碎片→快照(t+1)→巩固(t+2)→入库(t+3)→归纳可见）：
     会话1: 7轮对话 → 真实失败×3 → 3轮对话(共10 tick) + 排空(11)
            tick10: A入库3条失败记忆→B采样(局限缓存空→drive 0.45≥0.3→撞墙)；
                    SELFMODEL同tick归纳(3样本)→事件tick末分发→B缓存tick11才更新
     会话2: 3轮对话 → 失败×1 → 4轮对话(共7 tick) + 排空(共8, 累计19)
            晨间回忆回灌3条→tick1归纳→局限进入决策缓存
     会话3: 4轮对话(累计20-23, tick1即counter=20→重放自然触发, 跨2次重启)
     成年期: 40 tick(时钟23→63越过幼年线60) + 真实成功×3 + 对照事件 + 5 tick(共45, 时钟68)
  ③ T1 调试输出：打印全部事件类型计数（定位 wm_snapshot/subjective_tick 计数问题）
"""
import sys, os, tempfile, copy
os.environ["ORGAN_HEARTBEAT_INTERVAL"] = "999999"
os.environ.setdefault("ORGAN_STATE_PATH", os.path.join(tempfile.gettempdir(), "tan_model_organs_verify_final.json"))  # 隔离约束（双保险，另有 _safe_save 屏蔽自动落盘）
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, r"D:\7tan\7tanAI")

from src.agent import bionic_organs as bo
from src.agent.world_model import TanModel
from src.tools.registry import execute_tool

TOOL_FAIL = "幻觉工具_不存在"
TOOL_OK = "check_disk"
TMP = os.path.join(tempfile.gettempdir(), "organ_state_final_verify.json")

wm = TanModel()

# ── 隔离三件套 ──
import src.agent.world_model as wm_mod
wm_mod.get_tan_model = lambda: wm          # 防二次构造+生产状态重载
_real_save = bo.save_organ_state
def _safe_save(path=None):
    if path:
        return _real_save(path)
    return True                             # 屏蔽自动落盘（不污染生产状态文件）
bo.save_organ_state = _safe_save


def fresh_start():
    bo.working_memory["context_stack"].clear()
    bo.memory_library.clear()
    bo.self_model_data.clear()
    bo.self_model_data.update({
        "meta": {"last_update_subj_time": 0.0, "tick_counter": 0, "pending_goal_samples": 0},
        "capability": [], "limitations": [], "preferred_motives": [],
        "internal_signature": {},
        "history_summary": {"total_goal": 0, "total_success": 0, "total_fail": 0},
        "prediction_error_history": [], "meta_cognition": {},
        "counterfactual_stats": {}, "mind_flaws": [], "confidence": 0.0,
    })
    bo._replay_buffer.clear(); bo._event_queue.clear(); bo._event_log.clear()
    for k in list(bo._inboxes.keys()): bo._inboxes[k].clear()
    bo.subjective_time["subjective_clock"] = 0.0; bo.subjective_time["time_dilation"] = 1.0
    bo._consolidate_counter = 0; bo._organ_tick_counter = 0; bo._task_motive_counter = 0
    for attr in ["_self_limitations_b", "_self_limitations_inhibit", "_self_limitations_sim"]:
        getattr(bo, attr).clear()
    bo._self_confidence_b = 0
    bo._last_induction_key = None
    bo.working_memory["active_goals"] = []


def drain_and_snapshot(name):
    """优雅关机排空 + 段快照：先跑一拍把在途事件送进器官(真实关机前的最后一拍)，
    再快照(排空事件计入本段日志)，最后才落盘重启"""
    bo.organ_tick_all(wm.memory)
    snapshot(name)


def simulate_restart():
    """落盘 → 运行态归零 → 恢复(含晨间回忆)。排空已在 drain_and_snapshot 完成"""
    bo.save_organ_state(TMP)
    bo._consolidate_counter = 0; bo._organ_tick_counter = 0; bo._task_motive_counter = 0
    bo.subjective_time["subjective_clock"] = 0.0
    bo.memory_library.clear(); bo.self_model_data.clear()
    bo._replay_buffer.clear(); bo._event_queue.clear()
    for k in list(bo._inboxes.keys()): bo._inboxes[k].clear()
    bo.working_memory["context_stack"].clear(); bo.working_memory["active_goals"] = []
    for attr in ["_self_limitations_b", "_self_limitations_inhibit", "_self_limitations_sim"]:
        getattr(bo, attr).clear()
    bo._self_confidence_b = 0
    bo._last_induction_key = None
    bo.load_organ_state(TMP)


TOTAL_TALKS = [0]   # 实际对话轮数（黑盒断言用，防脚本硬编码计数再错）


def talk(rounds):
    for text in rounds:
        r = wm.respond(text)
        assert r is not None and len(r.strip()) > 0, f"respond({text!r}) 无回复"
        TOTAL_TALKS[0] += 1


log_all = []

def snapshot(name):
    log_all.append((name, list(copy.deepcopy(bo._event_log))))
    bo._event_log.clear()

# ==================== 会话1（上午，10 talk + drain = 11 tick）====================
fresh_start()
talk(["你好", "现在几点了", "帮我看看磁盘空间", "记忆里有什么",
      "今天天气怎么样", "帮我搜索最新游戏新闻", "再帮我看看记忆"])   # 7轮(碎片t8进快照)
for _ in range(3):
    execute_tool(TOOL_FAIL, {})     # 真实失败×3: t8快照→t9巩固→t10入库+B采样(撞墙)+归纳
talk(["你叫什么名字", "今天学到了什么", "再见"])   # t8,t9,t10：t10 B采样(记忆池含失败KEY,
                                    # 局限缓存空→drive0.45≥0.3→候选过普通阈值)
drain_and_snapshot("会话1")         # 排空拍t11: INHIBIT处理t10候选→final_goals含KEY(局限前·撞墙)
simulate_restart()

# ==================== 会话2（下午，7 talk + drain = 8 tick，累计19）====================
talk(["下午好", "帮我查一下系统状态", "再看看磁盘"])
execute_tool(TOOL_FAIL, {})                                # 第4条失败
talk(["记忆更新了吗", "今天运行得怎么样", "帮我总结一下", "好的谢谢"])
drain_and_snapshot("会话2")
simulate_restart()

# ==================== 会话3（晚上，4 talk，累计20-23 → 重放tick1触发）====================
talk(["晚上好", "还记得今天早上的事吗", "帮我回顾一下", "今天到此为止"])
snapshot("会话3")

# ==================== 数周后：成年推进（分块快照防事件日志截断）====================
for _i in range(4):
    for _ in range(10):
        bo.organ_tick_all(wm.memory)
    snapshot(f"成年期_推进_{_i + 1}")
for _ in range(3):
    execute_tool(TOOL_OK, {"path": "."})                   # 成年期真实成功×3
bo.wm_push_thought("成年·同权重对照事件", 0.4, 0.1)
for _ in range(5):
    bo.organ_tick_all(wm.memory)
snapshot("成年期_成功")

# ==================== 黑盒观测判定 ====================
def all_events():
    return [(name, e) for name, seg in log_all for e in seg]


def count(etype, origin=None):
    return sum(1 for _, e in all_events()
               if e.get("event_type") == etype and (origin is None or e.get("origin") == origin))


results = {}

# ---------- T1 我-非我边界 ----------
from collections import Counter
evs = all_events()
int_evs = [e for _, e in evs if e.get("origin") == "internal"]
ext_evs = [e for _, e in evs if e.get("origin") == "external"]
int_types = Counter(e["event_type"] for e in int_evs)
ext_types = Counter(e["event_type"] for e in ext_evs)
t1_sep = len(int_types) >= 3 and len(ext_types) >= 2 and not (set(int_types) & set(ext_types))
n_subj, n_wm, n_ui = count("subjective_tick"), count("wm_snapshot"), count("user_input")
t1_pattern = (n_subj >= 60 and n_wm >= 60 and n_ui == TOTAL_TALKS[0])
tool_evs = [e for _, e in evs if e.get("event_type") == "tool_result"]
t1_okflag = all("ok" in e["payload"] for e in tool_evs) and any(
    e["payload"].get("ok") is False for e in tool_evs)
results["T1_我-非我边界"] = {
    "内部事件数/类型数": (len(int_evs), len(int_types)),
    "外部事件数/类型数": (len(ext_evs), len(ext_types)),
    "类型集合分离(无交集)": t1_sep,
    f"周期性(内部): subjective_tick={n_subj}, wm_snapshot={n_wm}": t1_pattern,
    f"稀疏性(外部): user_input={n_ui} (实际对话{TOTAL_TALKS[0]}轮)": n_ui == TOTAL_TALKS[0],
    f"tool_result带真实ok标志({len(tool_evs)}条)": t1_okflag,
    "内部类型计数(调试)": dict(int_types),
    "通过": t1_sep and t1_pattern and t1_okflag and n_ui == TOTAL_TALKS[0],
}

# ---------- T2 自传记忆连续性 ----------
replays = [(name, e) for name, e in all_events() if e.get("event_type") == "replay_thought_fragment"]
replay_s3 = [e for name, e in replays if name == "会话3"]
replay_has_old = any(("user:" in str(e["payload"].get("thought", ""))
                      or "goal:" in str(e["payload"].get("thought", "")))
                     for e in replay_s3)
results["T2_自传记忆连续性"] = {
    "replay事件总数": len(replays),
    "会话3段(跨2次重启)自然触发": len(replay_s3) >= 1,
    "重放含久远真实经历": replay_has_old,
    "重放样例": [str(e["payload"].get("thought", ""))[:28] for e in replay_s3[:3]],
    "通过": len(replay_s3) >= 1 and replay_has_old,
}

# ---------- T3 自我模型演化 ----------
sm_evs = [(name, e) for name, e in all_events() if e.get("event_type") == "selfmodel_update"]
lim_map = {str(l.get("key")): l for l in bo.self_model_data.get("limitations", [])}
cap_keys = {str(c.get("key")) for c in bo.self_model_data.get("capability", [])}
hist = bo.self_model_data.get("history_summary", {})
results["T3_自我模型演化"] = {
    "selfmodel_update事件数": len(sm_evs),
    "归纳发生段": [name for name, _ in sm_evs],
    "limitations含真实工具失败": f"tool:{TOOL_FAIL}" in lim_map,
    "capability含真实工具成功(成年期)": f"tool:{TOOL_OK}" in cap_keys,
    "confidence": bo.self_model_data.get("confidence", 0),
    "history_summary": {k: hist.get(k) for k in ("total_goal", "total_success", "total_fail")},
    "通过": (len(sm_evs) >= 2 and f"tool:{TOOL_FAIL}" in lim_map
             and f"tool:{TOOL_OK}" in cap_keys
             and bo.self_model_data.get("confidence", 0) > 0),
}

# ---------- T4 自我参与决策闭环（行为翻转强断言） ----------
KEY = f"tool:{TOOL_FAIL}"
cand_evs = [(name, e) for name, e in all_events() if e.get("event_type") == "candidate_motives"]
final_evs = [(name, e) for name, e in all_events() if e.get("event_type") == "final_goals"]
passed_before = any(KEY in e["payload"].get("goals", []) for _, e in final_evs)
drive_before = drive_after = None
for name, e in cand_evs:
    for m in e["payload"].get("motives", []):
        if str(m.get("goal")) == KEY:
            if name == "会话1":
                drive_before = m.get("drive")
            else:
                drive_after = m.get("drive")
last_goals = set(final_evs[-1][1]["payload"].get("goals", [])) if final_evs else set()
blocked_after = KEY not in last_goals and drive_after is not None and drive_after < 0.6
t4_ok = passed_before and blocked_after
# ── T4 调试：限制缓存演化 vs KEY 候选 drive 轨迹（黑盒可观测证据链）──
print("\n[T4调试] selfmodel_update 事件（段 | limitations keys）:")
for name, e in sm_evs:
    _lims = [str(l.get("key")) for l in e["payload"].get("limitations", [])]
    print(f"    {name}: {_lims}")
print("[T4调试] KEY 候选 drive 轨迹:")
for name, e in cand_evs:
    for m in e["payload"].get("motives", []):
        if str(m.get("goal")) == KEY:
            print(f"    {name}: drive={m.get('drive')}")
print("[T4调试] final_goals 事件（段 | goals）:")
for name, e in final_evs:
    print(f"    {name}: {e['payload'].get('goals')}")
results["T4_自我参与决策闭环"] = {
    "candidate/final事件数": (len(cand_evs), len(final_evs)),
    f"撞墙:局限生效前通过(drive={drive_before})": passed_before,
    f"生效后候选drive(降权后={drive_after})": drive_after,
    "生效后final_goals不含该目标": blocked_after,
    "行为翻转(只能由自我模型解释)": t4_ok,
    "通过": t4_ok,
}

# ---------- T5 幼年效应 ----------
forg = [e for _, e in all_events() if e.get("event_type") == "mem_forgotten"]
inf_forg = [e for e in forg if e["payload"].get("infancy_active") is True]
strong_kept = any(m.get("goal_tag") == KEY for m in bo.memory_library)
adult_kept = any("对照事件" in str(m.get("thought", "")) for m in bo.memory_library)
inf_gate = any(abs(float(e["payload"].get("focus_threshold", 0)) - 0.6) < 1e-6 for e in inf_forg)
results["T5_幼年效应"] = {
    "mem_forgotten事件数": len(forg),
    "幼年期遗忘记录(infancy=True)": len(inf_forg),
    "幼年门槛加倍生效(0.6/0.4)": inf_gate,
    "幼年强经历例外留存(失败记忆)": strong_kept,
    "成年期同权重(0.4/0.1)可巩固": adult_kept,
    "通过": len(inf_forg) >= 1 and inf_gate and strong_kept and adult_kept,
}

# ==================== 汇总 ====================
print("\n" + "=" * 70)
print("阶段六最终验证 v3（模拟真实一天+成年推进，GLM-5.3 黑盒观测口径）")
print("=" * 70)
print(f"全天对话{TOTAL_TALKS[0]}轮 | tick总数={bo._organ_tick_counter} | 主观时钟={bo.subjective_time['subjective_clock']}")
print(f"重启2次(排空+落盘+晨间回忆) | 记忆库存量={len(bo.memory_library)}")
all_pass = True
for name, r in results.items():
    ok = r.get("通过", False)
    all_pass = all_pass and ok
    mark = "✅" if ok else "❌"
    print(f"\n{mark} {name}")
    for k, v in r.items():
        if k != "通过":
            print(f"    {k}: {v}")
print("\n" + "=" * 70)
print("总结论:", "🎉 五项全部通过——工程层面叙事自我意识成立" if all_pass else "⚠️ 存在未通过项")
print("=" * 70)
try:
    os.remove(TMP)
except Exception:
    pass
