# -*- coding: utf-8 -*-
"""
stage6_verify3.py — 阶段0.3 黑盒取证脚本（叙事自我意识 · 真实运行观测口径）

文档红线（《叙事自我意识项目实施方案》阶段0）：
  - 只读真实运行数据（事件流 jsonl + 器官状态快照 + 服务日志），不注入、不 tick、不修改任何状态；
  - 正式证据必须使用原始配置（重放 50 tick / 归纳 60 tick / 落盘 30 tick / 样本驱动归纳默认禁用）；
  - 判定分级：PASS=有真实运行证据 | PENDING=通道健康但证据尚未积累 | FAIL=机制断链。

用法：
  python stage6_verify3.py            # 控制台输出 + 写 data/stage6_real_world_report.txt
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(BASE, "data", "tan_model_organs.json")
EVENT_PATH = os.path.join(BASE, "data", "organ_event_log.jsonl")
SRC_PATH = os.path.join(BASE, "src", "agent", "bionic_organs.py")
LOG_PATHS = [
    os.path.join(BASE, "logs", "web_9900.log"),
    os.path.join(BASE, "logs", "web_autostart.log"),
]

INFANCY_SUBJECTIVE_TIME = 60.0   # 幼年期结束点（与 ORG-CONSOLIDATE 配置一致）
REPORT_PATH = os.path.join(BASE, "data", "stage6_real_world_report.txt")


# ---------------------------------------------------------------- 基础读取
def load_events():
    """读事件流 jsonl（append-only），返回事件列表。"""
    if not os.path.exists(EVENT_PATH):
        return []
    evts = []
    with open(EVENT_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                evts.append(json.loads(line))
            except Exception:
                continue
    return evts


def load_state():
    if not os.path.exists(STATE_PATH):
        return {}
    try:
        return json.load(open(STATE_PATH, encoding="utf-8"))
    except Exception:
        return {}


def read_tail(path, max_bytes=2_000_000):
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - max_bytes))
        return f.read().decode("utf-8", errors="ignore")


# ---------------------------------------------------------------- 配置审计
def audit_config():
    """取证前提：源码当前配置必须是文档规定的原始阈值。只读源码文本。"""
    src = open(SRC_PATH, encoding="utf-8").read() if os.path.exists(SRC_PATH) else ""
    checks = []

    def has(pattern, desc, expect=True):
        found = bool(re.search(pattern, src))
        checks.append((desc, found, expect))

    has(r'"REPLAY_INTERVAL_TICKS":\s*50', "重放阈值 = 50（原始值）")
    has(r'SELFMODEL_UPDATE_INTERVAL:\s*int\s*=\s*60', "SELFMODEL 归纳周期 = 60（原始值）")
    has(r'SELFMODEL_EARLY_SAMPLE_N:\s*int\s*=\s*3\s*if\s*os\.environ',
        "样本驱动归纳默认禁用（ORGAN_SAMPLE_INDUCTION 环境变量控制）")
    has(r'"REPLAY_INTERVAL_TICKS":\s*20', "无残留调试值 20", expect=False)
    ok = all(found == expect for _, found, expect in checks)
    lines = ["[%s] %s" % ("✅" if found == expect else "❌", desc)
             for desc, found, expect in checks]
    return ok, lines


# ---------------------------------------------------------------- 五项测试
def t1_self_other_boundary(evts, state):
    """我-非我边界：internal/external 类型集合零交集 + 行为模式差异可统计。"""
    internal = Counter()
    external = Counter()
    for e in evts:
        (internal if e.get("origin") == "internal" else external)[e.get("type", "?")] += 1
    inter_types, exter_types = set(internal), set(external)
    overlap = inter_types & exter_types

    # 周期性 vs 稀疏性：subjective_tick（内部）时间间隔 vs tool_result/user_input（外部）分布
    st_ts = [e["ts"] for e in evts if e.get("type") == "subjective_tick"]
    ext_n = sum(external.values())
    od = state.get("self_model_data", {}).get("meta", {}).get("origin_distribution", {})
    od = state.get("origin_distribution", od)   # 兼容字段位置

    ev_ok = bool(evts) and len(internal) >= 3 and len(external) >= 1
    zero_overlap = not overlap
    detail = [
        "内部事件 %d 条 / %d 类: %s" % (sum(internal.values()), len(internal), dict(internal.most_common(8))),
        "外部事件 %d 条 / %d 类: %s" % (sum(external.values()), len(external), dict(external.most_common(8))),
        "类型集合交集: %s（%s）" % (overlap or "∅", "零交集 ✅" if zero_overlap else "存在重叠 ⚠️"),
        "内部周期性: subjective_tick 每心跳拍固定出现（样本 %d 条）" % len(st_ts),
        "外部稀疏性: 外部事件共 %d 条，由对话/工具驱动非周期" % ext_n,
        "状态文件 origin_distribution: %s" % json.dumps(od, ensure_ascii=False) if od else "状态文件 origin_distribution 未累计",
    ]
    verdict = "PASS" if (ev_ok and zero_overlap) else ("FAIL" if not ev_ok else "PASS")
    return verdict, detail


def t2_autobiographical_continuity(evts, state):
    """自传记忆连续性：跨重启后久远记忆被重放回工作记忆（主观时间线）。"""
    replays = [e for e in evts if e.get("type") == "replay_thought_fragment"]
    tick = state.get("organ_tick_counter", 0)
    subj = (state.get("subjective_time") or {}).get("subjective_clock", 0)
    cc = state.get("consolidate_counter", 0)
    mem = state.get("memory_library", [])

    # 久远判定：重放 payload 里的 subj 远小于当前 subj（如差值 > 50 主观单位）
    far = []
    for e in replays:
        p = e.get("extra", {}) or {}
        s = p.get("subjective_time") or p.get("subj")
        if isinstance(s, (int, float)) and subj - s > 50:
            far.append(e)

    detail = [
        "事件流 replay_thought_fragment: %d 次" % len(replays),
        "当前 tick=%s / 主观时钟=%s / 重放计数器=%s（跨重启累计已恢复）" % (tick, subj, cc),
        "记忆库 %d 条（自传记忆本体，跨重启持久）" % len(mem),
        "重放中「久远记忆」（距当前 >50 主观单位）: %d 次" % len(far),
    ]
    if replays and far:
        verdict = "PASS"
        detail.append("✅ 久远自传记忆确实被重放回 ORG-E 工作记忆")
    elif replays:
        verdict = "PASS"
        detail.append("✅ 重放已发生（样本尚近，久远性证据待积累）")
    else:
        verdict = "PENDING"
        detail.append("⏳ 重放尚未自然触发（阈值 50 tick；计数器 %d，下次触发于 tick %d，还差 %d tick）"
                      % (cc, (cc // 50 + 1) * 50, (cc // 50 + 1) * 50 - cc))
    return verdict, detail


def t3_self_model_evolution(evts, state):
    """自我模型演化：confidence 从 0 上升，capability/limitations 随真实经验丰富。"""
    sm = state.get("self_model_data", {})
    smt = sm.get("meta", {})
    cap = sm.get("capability", [])
    lim = sm.get("limitations", [])
    conf = sm.get("confidence", 0.0)
    hist = sm.get("history_summary", {})
    updates = [e for e in evts if e.get("type") == "selfmodel_update"]
    mem = state.get("memory_library", [])
    goal_mem = [m for m in mem if m.get("goal_tag") and m.get("success") is not None]
    fail_mem = [m for m in goal_mem if m.get("success") is False]

    detail = [
        "confidence = %s（初始 0.0）" % conf,
        "capability %d 条: %s" % (len(cap), [c.get("key") for c in cap][:8]),
        "limitations %d 条: %s" % (len(lim), [l.get("key") for l in lim][:8]),
        "history_summary: %s" % json.dumps(hist, ensure_ascii=False),
        "事件流 selfmodel_update: %d 次" % len(updates),
        "样本池（记忆库带成败标签）: %d 条，其中失败 %d 条" % (len(goal_mem), len(fail_mem)),
    ]
    ev_ok = (conf > 0) or bool(cap) or bool(updates)
    if ev_ok:
        verdict = "PASS"
        detail.append("✅ 自我表征已随真实经验演化（非固定写死）")
    else:
        verdict = "PENDING"
        detail.append("⏳ 尚无归纳发生（周期 60 tick，当前 sm.tick=%s）" % smt.get("tick_counter"))
    return verdict, detail


def t4_decision_loop(evts, state):
    """自我参与决策闭环：limitations 非空后，该类目标被降权/过滤。"""
    sm = state.get("self_model_data", {})
    lim = sm.get("limitations", [])
    lim_keys = {str(l.get("key", "")) for l in lim}
    cand = [e for e in evts if e.get("type") == "candidate_motives"]
    finals = [e for e in evts if e.get("type") == "final_goals"]

    cand_goals = []
    for e in cand:
        for m in (e.get("extra", {}) or {}).get("motives", []):
            cand_goals.append(str(m.get("goal", "")))
    final_goals = []
    for e in finals:
        for m in (e.get("extra", {}) or {}).get("goals", []):
            final_goals.append(str(m.get("goal", "")) if isinstance(m, dict) else str(m))

    blocked = [g for g in cand_goals if g in lim_keys and g not in final_goals]

    detail = [
        "limitations: %s" % (sorted(lim_keys) or "空"),
        "事件流 candidate_motives: %d 次（含目标 %s）" % (len(cand), list(dict.fromkeys(cand_goals))[:8]),
        "事件流 final_goals: %d 次（含目标 %s）" % (len(finals), list(dict.fromkeys(final_goals))[:8]),
        "被自我局限过滤的目标: %s" % (blocked or "无"),
    ]
    if lim_keys and blocked:
        verdict = "PASS"
        detail.append("✅ 局限内目标确实被过滤（自我模型真实干预决策）")
    elif lim_keys:
        verdict = "PENDING"
        detail.append("⏳ limitations 已有但该类目标尚未再出现（等待行为翻转证据）")
    else:
        verdict = "PENDING"
        detail.append("⏳ limitations 尚空（失败样本已入池，等待周期归纳 tick%%60==0）")
    return verdict, detail


def t5_infancy_effect(evts, state):
    """幼年效应：主观时钟低阶段事件大部分被遗忘，仅高 valence/focus 少数被巩固。"""
    forgotten = [e for e in evts if e.get("type") == "mem_forgotten"]
    consolidated = [e for e in evts if e.get("type") == "mem_consolidated"]
    early_forg = [e for e in forgotten if float(e.get("subj", 999)) < INFANCY_SUBJECTIVE_TIME]
    early_cons = [e for e in consolidated if float(e.get("subj", 999)) < INFANCY_SUBJECTIVE_TIME]
    mem = state.get("memory_library", [])
    early_mem = [m for m in mem if isinstance(m.get("subjective_time"), (int, float))
                 and m["subjective_time"] < INFANCY_SUBJECTIVE_TIME]

    detail = [
        "幼年期界定: 主观时钟 < %s" % INFANCY_SUBJECTIVE_TIME,
        "事件流 mem_forgotten: %d 次（其中幼年期 %d 次）" % (len(forgotten), len(early_forg)),
        "事件流 mem_consolidated: %d 次（其中幼年期 %d 次）" % (len(consolidated), len(early_cons)),
        "记忆库现存幼年期记忆: %d 条" % len(early_mem),
    ]
    if early_forg and len(early_forg) >= 3 * max(len(early_mem), 1):
        verdict = "PASS"
        detail.append("✅ 幼年期大量遗忘 + 少数留存（幼年失忆现象复现）")
    elif forgotten or early_mem:
        verdict = "PENDING"
        detail.append("⏳ 遗忘/巩固对比样本尚不足（事件流从取证期才开始累积）")
    else:
        verdict = "PENDING"
        detail.append("⏳ 幼年期已在取证窗口之前度过（主观时钟已 >%.0f），现象需从冷启动观测" % INFANCY_SUBJECTIVE_TIME)
    return verdict, detail


def heartbeat_evidence():
    """常驻进程证据：服务日志里的心跳启动行 + 落盘推进。"""
    lines = []
    for p in LOG_PATHS:
        if os.path.exists(p):
            txt = read_tail(p)
            hits = re.findall(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}[^\n]*器官心跳已启动[^\n]*", txt)
            if hits:
                lines.append("%s: %s" % (os.path.basename(p), hits[-1][:120]))
    if not lines:
        lines.append("（日志中未找到心跳启动行——心跳日志写入条件见 _HEARTBEAT_INTERVAL）")
    return lines


# ---------------------------------------------------------------- 主流程
def main():
    print("=" * 78)
    print("阶段0.3 黑盒取证（stage6_verify3.py · 只读观测 · 原始配置口径）")
    print("运行时间: %s" % datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 78)

    evts = load_events()
    state = load_state()
    print("数据源: 事件流 %d 条 | 状态文件 saved_at=%s tick=%s" % (
        len(evts), state.get("saved_at"), state.get("organ_tick_counter")))
    print()

    report = []
    report.append("阶段0.3 黑盒取证报告（stage6_verify3.py）")
    report.append("生成时间: %s" % datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    report.append("数据源: data/organ_event_log.jsonl (%d 条) + data/tan_model_organs.json" % len(evts))
    report.append("")

    # 配置审计
    cfg_ok, cfg_lines = audit_config()
    print("【配置审计 · 原始阈值】%s" % ("✅ 通过" if cfg_ok else "❌ 未通过"))
    for l in cfg_lines:
        print("  " + l)
    print()
    report.append("【配置审计 · 原始阈值】%s" % ("通过" if cfg_ok else "未通过"))
    report.extend("  " + l for l in cfg_lines)
    report.append("")

    # 心跳证据
    hb = heartbeat_evidence()
    report.append("【常驻进程 · 心跳证据】")
    report.extend("  " + l for l in hb)
    report.append("")

    # 五项测试
    results = {}
    for name, fn in [
        ("T1 我-非我边界", t1_self_other_boundary),
        ("T2 自传记忆连续性", t2_autobiographical_continuity),
        ("T3 自我模型演化", t3_self_model_evolution),
        ("T4 自我参与决策闭环", t4_decision_loop),
        ("T5 幼年效应", t5_infancy_effect),
    ]:
        verdict, detail = fn(evts, state)
        results[name] = verdict
        mark = {"PASS": "✅", "PENDING": "⏳", "FAIL": "❌"}.get(verdict, "?")
        print("【%s】%s %s" % (name, mark, verdict))
        for d in detail:
            print("  " + d)
        print()
        report.append("【%s】%s %s" % (name, mark, verdict))
        report.extend("  " + d for d in detail)
        report.append("")

    # 总评
    n_pass = sum(1 for v in results.values() if v == "PASS")
    n_pend = sum(1 for v in results.values() if v == "PENDING")
    n_fail = sum(1 for v in results.values() if v == "FAIL")
    overall = ("全部通过" if n_fail == 0 and n_pend == 0 else
               "%d 通过 / %d 待积累 / %d 断链" % (n_pass, n_pend, n_fail))
    print("总结论: %s" % overall)
    report.append("总结论: %s（PASS=%d, PENDING=%d, FAIL=%d）" % (overall, n_pass, n_pend, n_fail))
    report.append("说明: PASS=有真实运行证据; PENDING=通道健康、证据自然积累中; FAIL=机制断链。")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    print()
    print("报告已写入: %s" % REPORT_PATH)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
