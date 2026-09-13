# -*- coding: utf-8 -*-
"""语用层（PragmaticLayer）测试 — 2026-09-03 修复「程序化回复」

背景：用户寒暄「晚上好」/ 情绪「牛逼」/ 挫败「答非所问」此前全部掉进
联网搜索兜底（搜出「都会」百科）或一字不差的固定模板。语用层在言语层之后、
知识库之前接住这类「说人话」的输入。

覆盖：
  ① 寒暄接住 + 真实时钟 + 多模板轮换不复读
  ② 时间语境（已经很晚了）
  ③ 情绪表达（正/负/中性）
  ④ 挫败信号 → 认领 + 负反馈表述
  ⑤ 名字确认（对，我就是老马）→ 工作记忆 + 后续带称呼
  ⑥ 短语释义（你不知道晚上好是什么意思吗）
  ⑦ 能力问法（你都会些啥呀）不再搜出百科
  ⑧ 搜索防误伤单元（is_smalltalk）
  ⑨ 安全边界：不劫持携带真实任务的长句
  ⑩ 语用意图入库（语用:xx 同步言语层 → _observe_round）
  ⑪ 诚实兜底多模板轮换
  ⑫ 回归：既有言语意图不被劫持
"""
import os
import re
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.abspath("."))

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + f"| {name}  {detail}")


# 兜底模板 / 搜索兜底 的特征串（命中即判定「没接住」）
HONEST_MARKS = ("我诚实说", "诚实说：这句话我不认识", "超出了我现在的能力",
                "我接不住这句话", "我不会硬答")
SEARCH_MARKS = ("联网搜索", "百度百科", "必应", "🔧")
KB_MARK = "📌"   # 知识库命中回复的特征


def is_honest(r):
    return any(m in r for m in HONEST_MARKS)


def is_search(r):
    return any(m in r for m in SEARCH_MARKS)


def main():
    # ── 隔离：器官状态→临时文件 / 心跳停用 / 记忆库不落盘（防污染生产数据） ──
    tmpdir = Path(tempfile.mkdtemp(prefix="pragmatic_test_"))
    from src.agent import bionic_organs as bo
    bo._ORGAN_STATE_PATH = tmpdir / "tan_model_organs.json"
    bo.start_organ_heartbeat = lambda *a, **k: None

    from src.agent.world_model import TanModel, TanModelMemory
    TanModelMemory.save = lambda self: None   # 内存行为不变，只是不写生产库
    model = TanModel()
    P = model.pragmatic
    check("T0 模型构建（语用层已挂载）", P is not None, type(P).__name__)

    # ===== ① 寒暄 =====
    r = model.respond("晚上好")
    check("①a 晚上好 → 接住（非兜底/非搜索）", bool(r) and not is_honest(r) and not is_search(r), repr(r[:40]))
    check("①b 晚上好 → 语用意图=greeting", P._last_pragma == "greeting", str(P._last_pragma))
    check("①c 回复带真实时钟 HH:MM", bool(re.search(r"\d{1,2}:\d{2}", r)), repr(r[:60]))
    r2 = model.respond("hi")
    check("①d hi → 接住", not is_honest(r2) and not is_search(r2), repr(r2[:40]))
    greets = [model.respond("你好") for _ in range(4)]
    check("①e 寒暄 4 连发不复读（≥3 种不同回复）", len(set(greets)) >= 3, f"去重后 {len(set(greets))} 种")

    # ===== ② 时间语境 =====
    r = model.respond("已经很晚了")
    check("②a 已经很晚了 → 接住+带时钟", not is_honest(r) and bool(re.search(r"\d{1,2}:\d{2}", r)), repr(r[:50]))
    check("②b 语用意图=late_night", P._last_pragma == "late_night", str(P._last_pragma))

    # ===== ③ 情绪表达（正/负/中性）=====
    for txt in ("牛逼", "无语", "嗯", "还行吧", "晕哦"):
        r = model.respond(txt)
        check(f"③ 情绪「{txt}」→ 接住", not is_honest(r) and not is_search(r), repr(r[:36]))

    # ===== ④ 挫败信号（负反馈路径，最重要）=====
    for txt in ("你答非所问啊", "你越来越傻了", "操，搞什么鬼？？？"):
        r = model.respond(txt)
        ok = (not is_honest(r)) and (not is_search(r)) and any(k in r for k in ("语用层", "负反馈", "学习闭环"))
        check(f"④ 挫败「{txt}」→ 认领+负反馈", ok, repr(r[:60]))

    # ===== ⑤ 名字确认（对，我就是老马）=====
    name_before = model.wm.dialog_slots.get("user_name") if model.wm else None
    r = model.respond("对，我就是老马")
    name_after = model.wm.dialog_slots.get("user_name") if model.wm else None
    check("⑤a 名字确认 → 工作记忆记住老马", name_after == "老马", f"{name_before} → {name_after}")
    check("⑤b 回复含称呼确认", "老马" in r, repr(r[:60]))
    greets = [model.respond("晚上好") for _ in range(3)]
    check("⑤c 后续寒暄带称呼「老马」", any("老马" in g for g in greets), [g[:24] for g in greets])

    # ===== ⑥ 短语释义 =====
    r = model.respond("你不知道晚上好是什么意思吗")
    check("⑥ 短语释义 → 提到「晚上好」且非搜索/知识库误命中",
          ("晚上好" in r) and (not is_search(r)) and (KB_MARK not in r), repr(r[:60]))

    # ===== ⑦ 能力问法修复 =====
    r = model.respond("你都会些啥呀")
    check("⑦ 「你都会些啥呀」→ 能力自述（非搜索垃圾）", not is_search(r) and not is_honest(r), repr(r[:60]))
    check("⑦b 归属言语层 capability（语用未劫持）", model.speech._last_intent == "capability", str(model.speech._last_intent))

    # ===== ⑧ 搜索防误伤单元 =====
    check("⑧a is_smalltalk(晚上好)=True", P.is_smalltalk("晚上好"))
    check("⑧b is_smalltalk(牛逼)=True", P.is_smalltalk("牛逼"))
    check("⑧c is_smalltalk(量子力学是什么)=False", not P.is_smalltalk("量子力学是什么"))

    # ===== ⑨ 安全边界：不劫持携带真实任务的长句 =====
    for txt in ("你好意思吗这样", "嗯，帮我查一下最新游戏新闻", "早起的鸟儿有虫吃是什么道理"):
        check(f"⑨ 未劫持「{txt[:14]}…」", P.classify(txt) is None, str(P.classify(txt)))

    # ===== ⑩ 语用意图入库 =====
    model.respond("无语了")
    check("⑩ 语用意图同步言语层（语用:frustration）",
          model.speech._last_intent == "语用:frustration", str(model.speech._last_intent))

    # ===== ⑪ 诚实兜底轮换 =====
    h = [model._honest_unknown("xyz不认识的话") for _ in range(3)]
    check("⑪ 兜底 3 连发不重复", len(set(h)) == 3, f"{len(set(h))}/3 种")

    # ===== ⑫ 回归：既有意图不被语用层劫持 =====
    r = model.respond("你是谁")
    check("⑫a 你是谁 → 仍是言语自述", ("7Tan" in r or "模型" in r) and not is_honest(r), repr(r[:40]))
    model.respond("我叫王大力")
    r = model.respond("你认识王大力吗")
    check("⑫b 名字记忆链路完好", ("王大力" in r), repr(r[:60]))

    print(f"\n===== 结果: {len(PASS)} PASS / {len(FAIL)} FAIL =====")
    if FAIL:
        print("失败项:", FAIL)
        sys.exit(1)


if __name__ == "__main__":
    main()
