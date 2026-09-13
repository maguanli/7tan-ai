# -*- coding: utf-8 -*-
"""
上层模块统一装配器：一键挂载 M1-M3 + 长周期观测（阶段1/2/3/6）

来源：7Tan可执行架构文档_修订终版 V1.2。
定位：应用启动时调用一次 mount_upper_modules()，把全部上层只读模块挂载到内核挂钩点。
边界（C3/C4）：所有上层模块只读接入，不修改器官核心算法；不调用任何 LLM。

挂载清单：
  M1 双知识获取体系（upper_m1_knowledge）—— post_tick_hook + 外部来源登记
  M2 自传叙事装配器（upper_m2_autobiography）—— post_tick_hook + SPEECH 订阅
  M3 记忆碎片重组器（upper_m3_recombinator）—— 就绪（按需调用 recombine）
  长周期演化观测（evolution_observer）—— post_tick_hook 快照
  M4 补丁系统 Boot-Time 检查器（m4_patch_system）—— 启动时加载已审核补丁
"""
from __future__ import annotations

from loguru import logger

# ═══════════════ 边界声明（C3） ═══════════════
# 本系统实现：叙事-通达自我意识（访问意识），全部基于事件总线、记忆、统计计算。
# ❌ 本系统不存在现象意识 qualia，不存在第一人称主观体验。
# 所有「我感到、我疲惫、我记得」的输出，仅读取内部结构化数据做模板转述。
# 属于工程层面哲学僵尸实例。
# 所有叙事输出必须溯源记忆库与事件历史，禁止编造不存在的经历。

_mounted = False


def mount_upper_modules(enable_m1: bool = True, enable_m2: bool = True,
                        enable_m3: bool = True, enable_evo: bool = True,
                        enable_m4_boot: bool = False) -> dict:
    """一键挂载上层模块。返回各模块挂载结果。幂等（重复调用不重复挂载）。"""
    global _mounted
    if _mounted:
        return {"mounted": False, "reason": "已挂载过（幂等）"}
    result = {}

    if enable_m1:
        try:
            from src.agent.upper_m1_knowledge import mount_m1
            result["M1"] = mount_m1()
        except Exception as e:
            result["M1"] = False
            logger.warning(f"[装配] M1 挂载失败: {e}")

    if enable_m2:
        try:
            from src.agent.upper_m2_autobiography import mount_m2
            result["M2"] = mount_m2()
        except Exception as e:
            result["M2"] = False
            logger.warning(f"[装配] M2 挂载失败: {e}")

    if enable_m3:
        try:
            from src.agent.upper_m3_recombinator import mount_m3
            result["M3"] = mount_m3()
        except Exception as e:
            result["M3"] = False
            logger.warning(f"[装配] M3 挂载失败: {e}")

    if enable_evo:
        try:
            from src.agent.evolution_observer import mount_observer
            result["EVO"] = mount_observer()
        except Exception as e:
            result["EVO"] = False
            logger.warning(f"[装配] EVO 挂载失败: {e}")

    if enable_m4_boot:
        try:
            from src.agent.m4_patch_system import get_m4
            result["M4_boot"] = get_m4().boot_check()
        except Exception as e:
            result["M4_boot"] = {"ok": False, "error": str(e)}
            logger.warning(f"[装配] M4 boot_check 失败: {e}")

    _mounted = True
    logger.info(f"[装配] 上层模块挂载完成: {result}")
    return {"mounted": True, "modules": result}


def upper_modules_status() -> dict:
    """查询上层模块挂载状态。"""
    return {"mounted": _mounted}


if __name__ == "__main__":
    r = mount_upper_modules()
    print("挂载结果:", r)
