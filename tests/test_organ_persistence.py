# -*- coding: utf-8 -*-
"""ORG-A / ORG-SELFMODEL 器官状态持久化测试
覆盖：保存→清空→加载往返 / 原子写（无 .tmp 残留）/ 坏文件容错 /
meta 缺键合并（SELFMODEL tick 不 KeyError）/ organ_tick_all 自动落盘 / init_all_organs 启动加载
"""
import json
import os
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.abspath("."))

from src.agent import bionic_organs as bo

PASS = []
FAIL = []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS" if cond else "FAIL") + f": {name} {detail}")


def main():
    tmpdir = Path(tempfile.mkdtemp(prefix="organ_persist_"))
    state_file = tmpdir / "tan_model_organs.json"

    # ========== ① 保存 → 清空 → 加载 往返一致 ==========
    bo.memory_library.clear()
    bo.memory_library.append({
        "thought": "用户老马告诉我他的名字", "focus": 0.9, "valence": 0.3,
        "origin": "external", "weight_eff": 1.5, "goal_tag": "对话:记住名字",
        "pe": 0.2, "success": True, "subjective_time": 123.4,
    })
    bo.memory_library.append({
        "thought": "tool:run_command 第553次成功", "focus": 0.7, "valence": 0.1,
        "origin": "internal", "weight_eff": 1.2, "goal_tag": "tool:run_command",
        "pe": 0.05, "success": True, "subjective_time": 456.7,
    })
    bo.self_model_data["confidence"] = 0.42
    bo.self_model_data["history_summary"] = {"total_goal": 7, "total_success": 3, "total_fail": 4}
    bo.self_model_data["meta"]["tick_counter"] = 88
    bo._organ_tick_counter = 99

    ok = bo.save_organ_state(state_file)
    check("①保存成功", ok)

    # 清空内存（模拟重启）
    bo.memory_library.clear()
    bo.self_model_data["confidence"] = 0.0
    bo.self_model_data["history_summary"] = {"total_goal": 0, "total_success": 0, "total_fail": 0}
    bo._organ_tick_counter = 0

    ok = bo.load_organ_state(state_file)
    check("①加载成功", ok)
    check("①ORG-A记忆条数恢复", len(bo.memory_library) == 2, f"got {len(bo.memory_library)}")
    check("①记忆内容往返一致",
          bo.memory_library[0]["thought"] == "用户老马告诉我他的名字"
          and abs(float(bo.memory_library[0]["weight_eff"]) - 1.5) < 1e-9
          and bo.memory_library[1]["goal_tag"] == "tool:run_command")
    check("①SELFMODEL confidence 恢复", abs(float(bo.self_model_data["confidence"]) - 0.42) < 1e-9)
    check("①SELFMODEL history_summary 恢复",
          bo.self_model_data["history_summary"]["total_goal"] == 7)
    check("①tick计数恢复", bo._organ_tick_counter == 99, f"got {bo._organ_tick_counter}")

    # ========== ② 原子写：无 .tmp 残留，文件可解析 ==========
    check("②无 .tmp 残留", not (tmpdir / "tan_model_organs.json.tmp").exists())
    raw = json.loads(state_file.read_text(encoding="utf-8"))
    # b03baf7（阶段六修复6）将落盘格式升级为 version=2（新增重放/动机计数器+主观时钟），此处同步断言
    check("②落盘文件 JSON 可解析", isinstance(raw, dict) and raw.get("version") == 2)

    # ========== ③ 坏文件容错 ==========
    bad = tmpdir / "bad.json"
    bad.write_text("这不是JSON{{{", encoding="utf-8")
    bo.memory_library.clear()
    ok = bo.load_organ_state(bad)
    check("③坏文件加载返回False不抛异常", ok is False)

    # 坏条目容错：memory_library 里混入非 dict / 无 thought 条目
    bad2 = tmpdir / "bad2.json"
    bad2.write_text(json.dumps({
        "memory_library": ["字符串脏数据", {"no_thought": 1}, {"thought": "好条目"}],
        "self_model_data": {"confidence": 0.5},
    }, ensure_ascii=False), encoding="utf-8")
    bo.memory_library.clear()
    ok = bo.load_organ_state(bad2)
    check("③坏条目被跳过仅恢复好条目", ok is True and len(bo.memory_library) == 1
          and bo.memory_library[0]["thought"] == "好条目")

    # ========== ④ meta 缺键合并（旧版快照兼容） ==========
    old = tmpdir / "old.json"
    old.write_text(json.dumps({
        "memory_library": [],
        "self_model_data": {"meta": {"last_update_subj_time": 1.0}, "confidence": 0.3},
    }, ensure_ascii=False), encoding="utf-8")
    bo.self_model_data["meta"] = {}  # 清空 meta 模拟缺键
    bo.load_organ_state(old)
    check("④meta 缺键合并后含 tick_counter 默认键",
          "tick_counter" in bo.self_model_data["meta"])
    # SELFMODEL tick 第一行就 += tick_counter，缺键会 KeyError——此测试保证不炸
    bo.self_model_data["meta"]["tick_counter"] += 1
    check("④SELFMODEL tick 计数可安全自增", bo.self_model_data["meta"]["tick_counter"] == 1)

    # ========== ⑤ organ_tick_all 自动落盘（周期触发） ==========
    auto = tmpdir / "auto.json"
    real_path = bo._ORGAN_STATE_PATH
    real_counter = bo._organ_tick_counter
    bo._ORGAN_STATE_PATH = auto  # monkeypatch 到临时路径，不污染真实 data/
    try:
        bo._organ_tick_counter = bo.ORGAN_AUTOSAVE_EVERY - 1  # 差 1 tick 触发
        bo.organ_tick_all(None)   # 跑一次主循环 → counter 达到周期 → 自动落盘
        check("⑤organ_tick_all 周期自动落盘", auto.exists(),
              f"counter={bo._organ_tick_counter}")
        raw = json.loads(auto.read_text(encoding="utf-8"))
        check("⑤自动落盘内容合法", "memory_library" in raw and "self_model_data" in raw)
    finally:
        bo._ORGAN_STATE_PATH = real_path
        bo._organ_tick_counter = real_counter

    # ========== ⑥ init_all_organs() 启动加载链路 ==========
    boot = tmpdir / "boot.json"
    # ④的 old.json 已把内存记忆库清空——先重新填充，再走「保存→重启→init_all_organs」链路
    bo.memory_library.clear()
    bo.memory_library.append({"thought": "用户老马告诉我他的名字", "focus": 0.9,
                              "origin": "external", "weight_eff": 1.5,
                              "goal_tag": "对话:记住名字", "success": True})
    bo.memory_library.append({"thought": "tool:run_command 第553次成功", "focus": 0.7,
                              "origin": "internal", "weight_eff": 1.2,
                              "goal_tag": "tool:run_command", "success": True})
    bo.save_organ_state(boot)
    bo.memory_library.clear()
    bo._ORGAN_STATE_PATH = boot
    try:
        bo.init_all_organs()   # 注册全部器官 + 末尾 load_organ_state()
        check("⑥init_all_organs 后记忆自动恢复", len(bo.memory_library) == 2,
              f"got {len(bo.memory_library)}")
        check("⑥器官注册完整（14个）", len(bo.organ_registry) == 14,
              f"got {len(bo.organ_registry)}")
        check("⑥ORG-LLM 仍不存在", "ORG-LLM" not in bo.organ_registry)
    finally:
        bo._ORGAN_STATE_PATH = real_path

    # ========== 清理 ==========
    for f in tmpdir.iterdir():
        f.unlink()
    tmpdir.rmdir()

    print()
    print(f"RESULT: {len(PASS)} PASS / {len(FAIL)} FAIL")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
