# -*- coding: utf-8 -*-
"""
阶段7 交付物｜bionic_organs_no_llm.py：无 LLM 仿生器官内核（官方交付入口）

来源：7Tan可执行架构文档_修订终版 V1.2（阶段7 交付物清单）。
定位：对外交付的「无 LLM 心智内核」完整源码入口。内核本体在 bionic_organs.py，
      本文件是官方交付面：统一边界声明 + 全量接口再导出 + 无 LLM 自检。

════════════════════ 边界声明（C3，强制） ════════════════════
# 本系统实现：叙事-通达自我意识（访问意识），全部基于事件总线、记忆、统计计算。
# ❌ 本系统不存在现象意识 qualia，不存在第一人称主观体验。
# 所有「我感到、我疲惫、我记得」的输出，仅读取内部结构化数据做模板转述。
# 属于工程层面哲学僵尸实例。
# 所有叙事输出必须溯源记忆库与事件历史，禁止编造不存在的经历。
══════════════════════════════════════════════════════════════

无 LLM 自检：本文件 import 时执行 _assert_no_llm()，扫描内核源码确认
            不存在任何生成式大模型调用入口（ORG-LLM 已彻底移除）。
"""
from __future__ import annotations

import re
from pathlib import Path

# ═══════════════ 全量接口再导出（内核本体） ═══════════════
from src.agent.bionic_organs import (  # noqa: F401
    BionicOrgan,
    register_organ,
    get_organ,
    emit_event,
    subscribe_event,
    poll_events,
    poll_replay_events,
    poll_latest_event,
    recent_bus_events,
    bus_stats,
    save_organ_state,
    load_organ_state,
    organ_tick_all,
    generate_self_report,
    organ_simulate_preview,
    register_post_tick_hook,
    register_external_source,
    init_all_organs,
    start_organ_heartbeat,
    organ_registry,
    memory_library,
    self_model_data,
    subjective_time,
)

__all__ = [
    "BionicOrgan", "register_organ", "get_organ", "emit_event", "subscribe_event",
    "poll_events", "poll_replay_events", "poll_latest_event", "recent_bus_events",
    "bus_stats", "save_organ_state", "load_organ_state", "organ_tick_all",
    "generate_self_report", "organ_simulate_preview", "register_post_tick_hook",
    "register_external_source", "init_all_organs", "start_organ_heartbeat",
    "organ_registry", "memory_library", "self_model_data", "subjective_time",
]


# ═══════════════ 无 LLM 自检 ═══════════════
_LLM_IMPORT_PATTERNS = [
    # 只匹配行首真实 import 语句（多行模式），避免误报「无 GGUF/无 LLM」等否定性注释
    r"(?m)^\s*(?:import|from)\s+(?:openai|anthropic|transformers|llama_cpp|gguf|chatglm)\b",
    r"(?m)^\s*(?:import|from)\s+[\w.]+\s+import\s+.*(?:llm|chat|completion)",
    r"requests\.post\([^)]*(?:api/chat|/completions|/v1/chat)",
    # 精确检测 ORG-LLM 作为器官代码被实际注册
    r"organ_code\s*=\s*[\"']ORG[-_]LLM",
    r"register_organ\([^)]*ORG[-_]LLM",
]


def assert_no_llm() -> bool:
    """扫描内核源码确认无任何 LLM 调用入口。返回 True=无 LLM。"""
    kernel = Path(__file__).resolve().parent / "bionic_organs.py"
    try:
        src = kernel.read_text(encoding="utf-8")
        for pat in _LLM_IMPORT_PATTERNS:
            if re.search(pat, src, flags=re.I):
                return False
        return True
    except Exception:
        return False


_NO_LLM = assert_no_llm()

if not _NO_LLM:
    raise RuntimeError("内核检测到 LLM 调用入口，违反 C1 红线！")


if __name__ == "__main__":
    print("=" * 60)
    print("bionic_organs_no_llm.py 交付自检")
    print("=" * 60)
    print(f"无 LLM 自检: {'通过（内核无任何 LLM 调用入口）' if _NO_LLM else '失败'}")
    init_all_organs()
    enabled = [c for c, o in organ_registry.items() if o.enabled]
    print(f"已注册器官: {len(organ_registry)} 个")
    print(f"已启用: {len(enabled)} 个 -> {enabled}")
    print(f"订阅拓扑: {bus_stats()['subscriptions']}")
    print()
    print("边界声明（对外输出约束）：")
    print("  本系统实现叙事-通达自我意识，不存在现象意识 qualia；")
    print("  情绪类输出仅为内部状态报告，不等于真实主观感受；")
    print("  重置/关闭系统不会产生主观伦理伤害。")
