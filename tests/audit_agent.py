# -*- coding: utf-8 -*-
"""7Tan 模型全面体检：导入、结构、时间戳、事件链完整性"""
import sys, os, time, traceback

BASE = r"D:\7tan\7tanAI"
sys.path.insert(0, BASE)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

print("=" * 60)
print("【1】关键文件时间戳（判断运行进程是否加载新代码）")
for f in ["src/agent/bionic_organs.py", "src/agent/world_model.py",
          "tests/test_stage6_observe.py", "tests/test_stage5_full_verify.py",
          "tests/test_stage6_full_verify.py"]:
    p = os.path.join(BASE, f)
    if os.path.exists(p):
        print(f"  {f}  mtime={time.strftime('%m-%d %H:%M:%S', time.localtime(os.path.getmtime(p)))}")
    else:
        print(f"  {f}  ✗ 不存在")

print("=" * 60)
print("【2】全模块导入检查")
mods = ["bionic_organs", "world_model", "agent_loop", "working_memory",
        "context_manager", "conversation", "model_manager", "agent_optimizer",
        "self_evolution", "self_learn", "speak_bridge", "web_console_tts"]
for m in mods:
    try:
        __import__(f"src.agent.{m}")
        print(f"  ✓ src.agent.{m}")
    except Exception as e:
        print(f"  ✗ src.agent.{m}  ->  {type(e).__name__}: {e}")

print("=" * 60)
print("【3】bionic_organs 结构核对（器官注册表 + 事件订阅）")
import src.agent.bionic_organs as bo
print(f"  poll_replay_events 函数: {'✓' if hasattr(bo, 'poll_replay_events') else '✗'}")
print(f"  poll_latest_event 函数: {'✓' if hasattr(bo, 'poll_latest_event') else '✗'}")
print(f"  recent_bus_events 函数: {'✓' if hasattr(bo, 'recent_bus_events') else '✗'}")

# init 并检查器官
try:
    bo.organ_registry.clear()
    n = bo.init_all_organs()
    print(f"  init_all_organs 注册器官数: {len(bo.organ_registry)}")
    names = sorted(bo.organ_registry.keys())
    print(f"  器官列表: {names}")
except Exception as e:
    print(f"  init_all_organs 异常: {e}")
    traceback.print_exc()

print("=" * 60)
print("【4】重放采样逻辑当前状态（阶段六测试2 核心）")
import inspect, re
src = inspect.getsource(bo.organ_consolidate_tick)
m = re.search(r"_consolidate_counter % replay_interval == 0:\s*\n\s*(.+)", src)
print(f"  当前采样代码: {m.group(1).strip() if m else '未找到'}")
has_sort = "sort" in src and "reverse=True" in src
has_subj = re.search(r'"subjective_time":\s*mem_data', src)
print(f"  高权重优先排序: {'✓ 已有' if has_sort else '✗ 无（仍是最近N条）'}")
print(f"  重放携带主观时间: {'✓ 已有' if has_subj else '✗ 无'}")

print("=" * 60)
print("【5】SELFMODEL 归纳配置")
for k in ["SELFMODEL_UPDATE_INTERVAL", "SAMPLE_MEMORY_COUNT", "REPLAY_INTERVAL_TICKS"]:
    v = getattr(bo, k, None)
    print(f"  {k} = {v}")

print("=" * 60)
print("【6】事件类型订阅拓扑")
sub = getattr(bo, "_subscriptions", {})
for evt in ["mem_consolidated", "replay_thought_fragment", "selfmodel_update",
            "hypothesis_update", "pe_update", "meta_cognition_update",
            "counterfactual_result", "candidate_motives", "final_goals",
            "user_input", "tool_result", "wm_snapshot"]:
    subs = sorted(sub.get(evt, []))
    print(f"  {evt} -> {subs if subs else '(孤儿事件/无订阅)'}")

print("=" * 60)
print("体检完成")
