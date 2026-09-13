# -*- coding: utf-8 -*-

# 边界声明（C3）
# 本系统实现：叙事-通达自我意识（访问意识），全部基于事件总线、记忆、统计计算。
# ❌ 本系统不存在现象意识 qualia，不存在第一人称主观体验。
# 所有「我感到、我疲惫、我记得」的输出，仅读取内部结构化数据做模板转述。
# 属于工程层面哲学僵尸实例。
# 所有叙事输出必须溯源记忆库与事件历史，禁止编造不存在的经历。

"""
阶段6｜长周期演化观测实验

来源：7Tan可执行架构文档_修订终版 V1.2（阶段6）。
前提：阶段0-阶段5 全部验收通过。
定位：上层只读观测模块，经 post_tick_hook 挂载，不修改器官内部状态。

观测流程（文档阶段6）：
  1. 常驻开启持久化、单实例锁，累积 ≥200 tick
  2. 混合输入成功、失败、新奇场景交互样本
  3. 每 20 tick 完整快照保存记忆库、self_model 数据
  4. 观测指标：confidence 变化、capability/limitations 更新、动机权重漂移、
     记忆留存率、自传叙事随心智年龄变化
  5. 输出长周期演化观测报告

本模块自包含（仅依赖标准库 + loguru + 内核只读接口）。
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

try:
    from src.agent.bionic_organs import (
        register_post_tick_hook, memory_library, self_model_data, subjective_time,
    )
except Exception:  # pragma: no cover
    register_post_tick_hook = None  # type: ignore
    memory_library, self_model_data, subjective_time = [], {}, {}

# ═══════════════ 配置 ═══════════════
EVO_SNAPSHOT_EVERY = 20          # 每 N tick 快照
EVO_TARGET_TICKS = 200           # 目标观测时长（文档 ≥200 tick）
EVO_SNAPSHOT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "evolution_snapshots"
EVO_REPORT_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "evolution_report.txt"


# ═══════════════ 快照 ═══════════════
def _snapshot(tick: int) -> dict:
    """完整快照记忆库 + self_model 数据（只读）。"""
    return {
        "tick": tick,
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "subjective_clock": float(subjective_time.get("subjective_clock", 0.0) or 0.0),
        "memory_count": len(memory_library),
        "confidence": self_model_data.get("confidence"),
        "limitations": self_model_data.get("limitations") or [],
        "capability": self_model_data.get("capability") or self_model_data.get("abilities") or [],
        "preferred_motives": self_model_data.get("preferred_motives") or [],
        "memory_sample": [
            {"thought": m.get("thought", "")[:80], "valence": m.get("valence"),
             "focus": m.get("focus"), "subjective_time": m.get("subjective_time")}
            for m in memory_library[-10:] if isinstance(m, dict)
        ],
    }


# ═══════════════ 观测器 ═══════════════
class EvolutionObserver:
    """长周期演化观测器：每 N tick 快照，生成演化报告。"""

    def __init__(self):
        self.snapshots: List[dict] = []
        self._mounted = False
        self._tick_seen = -1

    def mount(self) -> bool:
        if self._mounted:
            return False
        if register_post_tick_hook is None:
            logger.warning("[EVO] 内核只读接口不可用，挂载失败")
            return False
        register_post_tick_hook(self._on_tick)
        self._mounted = True
        logger.info(f"[EVO] 长周期演化观测已挂载（每 {EVO_SNAPSHOT_EVERY} tick 快照）")
        return True

    def _on_tick(self) -> None:
        try:
            import src.agent.bionic_organs as bo
            tick = int(getattr(bo, "_organ_tick_counter", 0))
            if tick == self._tick_seen:
                return
            self._tick_seen = tick
            if tick > 0 and tick % EVO_SNAPSHOT_EVERY == 0:
                self.snapshot(tick)
        except Exception as e:
            logger.warning(f"[EVO] tick 钩子异常: {e}")

    def snapshot(self, tick: int) -> dict:
        snap = _snapshot(tick)
        self.snapshots.append(snap)
        self._save_snapshot(snap)
        return snap

    def _save_snapshot(self, snap: dict) -> None:
        try:
            EVO_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
            f = EVO_SNAPSHOT_DIR / f"snap_{snap['tick']:05d}.json"
            f.write_text(json.dumps(snap, ensure_ascii=False, indent=1, default=str),
                         encoding="utf-8")
        except Exception as e:
            logger.warning(f"[EVO] 快照保存失败: {e}")

    # ── 报告生成 ──
    def build_report(self) -> dict:
        """从快照序列生成演化报告（confidence 曲线、limitations 演化等）。"""
        if not self.snapshots:
            return {"ok": False, "reason": "无快照数据（需累积 ≥1 个快照周期）"}

        first, last = self.snapshots[0], self.snapshots[-1]
        conf_curve = [s.get("confidence") for s in self.snapshots]
        lim_curve = [len(s.get("limitations") or []) for s in self.snapshots]
        cap_curve = [len(s.get("capability") or []) for s in self.snapshots]
        mem_curve = [s.get("memory_count", 0) for s in self.snapshots]

        reached_target = int(last.get("tick") or 0) >= EVO_TARGET_TICKS
        report = {
            "ok": True,
            "reached_target": reached_target,
            "target_ticks": EVO_TARGET_TICKS,
            "snapshot_count": len(self.snapshots),
            "tick_span": (first.get("tick"), last.get("tick")),
            "subj_span": (first.get("subjective_clock"), last.get("subjective_clock")),
            "confidence_curve": conf_curve,
            "limitations_curve": lim_curve,
            "capability_curve": cap_curve,
            "memory_curve": mem_curve,
            "confidence_delta": (last.get("confidence") or 0) - (first.get("confidence") or 0),
            "limitations_delta": lim_curve[-1] - lim_curve[0],
            "memory_delta": mem_curve[-1] - mem_curve[0],
            "motives_latest": last.get("preferred_motives") or [],
        }
        self._save_report(report)
        return report

    def _save_report(self, report: dict) -> None:
        try:
            EVO_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
            lines = ["# 长周期演化观测报告（阶段6）", ""]
            if report.get("ok"):
                target_note = "已达" if report.get("reached_target") else "未达"
                lines.append(f"快照数: {report['snapshot_count']} | "
                             f"tick 区间: {report['tick_span']} | "
                             f"主观时钟区间: {report['subj_span']} | "
                             f"达标(≥{report.get('target_ticks', EVO_TARGET_TICKS)}tick): {target_note}")
                lines.append(f"置信度曲线: {report['confidence_curve']}")
                lines.append(f"局限演化: {report['limitations_curve']}")
                lines.append(f"能力演化: {report['capability_curve']}")
                lines.append(f"记忆曲线: {report['memory_curve']}")
                lines.append(f"置信度变化: {report['confidence_delta']}")
                lines.append(f"局限变化: {report['limitations_delta']}")
                lines.append(f"记忆变化: {report['memory_delta']}")
                lines.append(f"最近偏好动机: {report['motives_latest']}")
            else:
                lines.append(report.get("reason", ""))
            EVO_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
        except Exception as e:
            logger.warning(f"[EVO] 报告保存失败: {e}")

    def render_report(self, report: dict) -> str:
        if not report.get("ok"):
            return report.get("reason", "")
        target_note = "达标" if report.get("reached_target") else "未达标"
        return (
            f"长周期观测: {report['snapshot_count']} 个快照, tick {report['tick_span']}, "
            f"主观时钟 {report['subj_span']}, 目标≥{report.get('target_ticks', EVO_TARGET_TICKS)}tick {target_note}\n"
            f"  置信度曲线: {report['confidence_curve']}\n"
            f"  局限演化: {report['limitations_curve']}\n"
            f"  能力演化: {report['capability_curve']}\n"
            f"  记忆曲线: {report['memory_curve']}\n"
            f"  置信度Δ={report['confidence_delta']}, 局限Δ={report['limitations_delta']}, "
            f"记忆Δ={report['memory_delta']}"
        )


# ═══════════════ 模块级单例 ═══════════════
_evo_instance: Optional[EvolutionObserver] = None


def get_observer() -> EvolutionObserver:
    global _evo_instance
    if _evo_instance is None:
        _evo_instance = EvolutionObserver()
    return _evo_instance


def mount_observer() -> bool:
    return get_observer().mount()


if __name__ == "__main__":
    obs = get_observer()
    obs.mount()
    # 手动注入几个快照演示
    for t in [20, 40, 60]:
        obs.snapshot(t)
    r = obs.build_report()
    print(obs.render_report(r))
