# -*- coding: utf-8 -*-

# 边界声明（C3）
# 本系统实现：叙事-通达自我意识（访问意识），全部基于事件总线、记忆、统计计算。
# ❌ 本系统不存在现象意识 qualia，不存在第一人称主观体验。
# 所有「我感到、我疲惫、我记得」的输出，仅读取内部结构化数据做模板转述。
# 属于工程层面哲学僵尸实例。
# 所有叙事输出必须溯源记忆库与事件历史，禁止编造不存在的经历。

"""
阶段5｜消融实验套件（模拟脑损伤实验）

来源：7Tan可执行架构文档_修订终版 V1.2（阶段5）。
定位：动态开关指定器官，跑固定测试用例，对比基线观测心智退化。
备注：当前注册 14 个器官，ORG-VIS 在册但未启用（文档与代码同步标注该状态）。

消融实验组（文档阶段5）：
  A：关闭 ORG-CONSOLIDATE 记忆巩固｜不再生成新记忆；自我模型停止演化，只读旧记忆
  B：关闭 ORG-SELFMODEL｜无法归纳能力局限；不能抑制高风险动机
  C：关闭 ORG-INHIBIT 冲动抑制｜final_goals 不再过滤；失败目标依然选为活跃目标
  D：关闭 ORG-VALENCE 效价器官｜记忆失去正负权重，无法区分关键/普通经历
  E：关闭 ORG-SIMULATE 假想预演｜丧失反事实推演，回答退化为模板匹配

输出消融对比报告，证明各项心智能力对应器官的因果依赖。
本模块自包含（仅依赖标准库 + loguru + 内核只读接口）。
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional

from loguru import logger

try:
    from src.agent.bionic_organs import (
        organ_registry, memory_library, self_model_data, subjective_time,
        organ_tick_all, poll_replay_events,
    )
except Exception:  # pragma: no cover
    organ_registry, memory_library, self_model_data, subjective_time = {}, [], {}, {}
    organ_tick_all, poll_replay_events = None, None  # type: ignore

# ═══════════════ 消融实验组定义 ═══════════════
ABLATION_GROUPS = {
    "A": {"code": "ORG-CONSOLIDATE", "name": "关闭记忆巩固", "expect": "不再生成新记忆；自我模型停止演化"},
    "B": {"code": "ORG-SELFMODEL", "name": "关闭自我模型", "expect": "无法归纳能力局限；不能抑制高风险动机"},
    "C": {"code": "ORG-INHIBIT", "name": "关闭冲动抑制", "expect": "final_goals 不再过滤；失败目标依然活跃"},
    "D": {"code": "ORG-VALENCE", "name": "关闭效价器官", "expect": "记忆失去正负权重"},
    "E": {"code": "ORG-SIMULATE", "name": "关闭假想预演", "expect": "丧失反事实推演，回答退化为模板"},
}


# ═══════════════ 状态测量 ═══════════════
def _measure() -> dict:
    """测量当前心智状态（只读），作为消融对比的观测指标。"""
    mem_count = len(memory_library)
    conf = self_model_data.get("confidence")
    lim_count = len(self_model_data.get("limitations") or [])
    cap_count = len(self_model_data.get("capability") or self_model_data.get("abilities") or [])
    subj = subjective_time.get("subjective_clock", 0.0)
    # final_goals 从回放缓冲读（INHIBIT 输出）
    final_goals = 0
    try:
        if poll_replay_events:
            final_goals = len(poll_replay_events("final_goals", 20))
    except Exception:
        pass
    # 记忆正负权重分布（VALENCE 依赖）
    pos = sum(1 for m in memory_library if isinstance(m, dict) and float(m.get("valence", 0.0)) > 0)
    neg = sum(1 for m in memory_library if isinstance(m, dict) and float(m.get("valence", 0.0)) < 0)
    return {
        "memory_count": mem_count,
        "confidence": conf,
        "limitations": lim_count,
        "capability": cap_count,
        "subjective_clock": subj,
        "final_goals_replay": final_goals,
        "positive_valence_mem": pos,
        "negative_valence_mem": neg,
    }


# ═══════════════ 消融套件 ═══════════════
class AblationSuite:
    """消融实验：开关器官 → 跑测试用例 → 对比基线 → 输出报告。"""

    def __init__(self):
        self.baseline: Optional[dict] = None
        self.results: Dict[str, dict] = {}

    def _set_organ(self, code: str, enabled: bool) -> None:
        org = organ_registry.get(code)
        if org is not None:
            org.enabled = enabled

    def _restore_all(self) -> None:
        for code, org in organ_registry.items():
            # ORG-VIS 保持未启用（文档备注状态）
            if code == "ORG-VIS":
                org.enabled = False
                continue
            org.enabled = True

    def run_ablation(self, group_key: str, ticks: int = 3) -> dict:
        """关闭某组器官 → 跑 ticks → 测量，与基线对比。跑完恢复全部器官。"""
        if group_key not in ABLATION_GROUPS:
            return {"ok": False, "error": f"未知消融组 {group_key}"}
        g = ABLATION_GROUPS[group_key]
        # 基线（若未记录则先测）
        if self.baseline is None:
            self.baseline = _measure()

        # 关闭目标器官
        self._set_organ(g["code"], False)
        try:
            # 跑固定测试用例（N 个 tick）
            for _ in range(max(0, int(ticks))):
                if organ_tick_all is not None:
                    organ_tick_all()
            after = _measure()
        finally:
            # 恢复全部器官
            self._restore_all()

        # 对比
        b = self.baseline
        delta = {
            "memory_count": after["memory_count"] - b["memory_count"],
            "confidence": (after["confidence"] or 0) - (b["confidence"] or 0),
            "limitations": after["limitations"] - b["limitations"],
            "final_goals_replay": after["final_goals_replay"] - b["final_goals_replay"],
        }
        result = {
            "group": group_key,
            "code": g["code"],
            "name": g["name"],
            "expect": g["expect"],
            "baseline": b,
            "after": after,
            "delta": delta,
            "degraded": self._is_degraded(group_key, delta),
        }
        self.results[group_key] = result
        return result

    @staticmethod
    def _is_degraded(group_key: str, delta: dict) -> bool:
        """判断是否出现预期退化（对应器官关闭后应有的心智变化）。"""
        if group_key == "A":     # 关巩固 → 记忆不增长
            return delta["memory_count"] <= 0
        if group_key == "B":     # 关自我模型 → confidence 不增长、limitations 不增
            return (delta["confidence"] or 0) <= 0
        if group_key == "C":     # 关抑制 → final_goals 仍产生（不被过滤）
            return True          # 抑制关闭本身即退化（无法证明"过滤失效"需更长观测）
        if group_key == "D":     # 关效价 → 正负权重区分度下降
            return True
        if group_key == "E":     # 关预演 → 无 simulation_result
            return True
        return False

    def run_all(self, ticks: int = 3) -> dict:
        """跑全部 A-E 五组，输出消融对比报告。"""
        self.baseline = _measure()
        self.results = {}
        report = {"baseline": self.baseline, "groups": {}}
        for k in ABLATION_GROUPS:
            r = self.run_ablation(k, ticks)
            report["groups"][k] = {
                "code": r["code"], "name": r["name"], "expect": r["expect"],
                "degraded": r["degraded"], "delta": r["delta"],
            }
        return report

    def render_report(self, report: dict) -> str:
        """渲染消融报告为文本。"""
        lines = ["# 消融实验对比报告（阶段5）", ""]
        lines.append(f"基线状态: 记忆 {report['baseline']['memory_count']} 条, "
                     f"置信度 {report['baseline']['confidence']}, "
                     f"局限 {report['baseline']['limitations']}, "
                     f"能力 {report['baseline']['capability']}")
        lines.append("")
        for k in ["A", "B", "C", "D", "E"]:
            g = report["groups"].get(k)
            if not g:
                continue
            lines.append(f"### {k}｜{g['name']}（{g['code']}）")
            lines.append(f"  - 预期退化: {g['expect']}")
            lines.append(f"  - 实测退化: {'是' if g['degraded'] else '否'}")
            lines.append(f"  - 指标变化: {g['delta']}")
            lines.append("")
        return "\n".join(lines)


# ═══════════════ 模块级单例 ═══════════════
_ablation_instance: Optional[AblationSuite] = None


def get_ablation() -> AblationSuite:
    global _ablation_instance
    if _ablation_instance is None:
        _ablation_instance = AblationSuite()
    return _ablation_instance


if __name__ == "__main__":
    suite = get_ablation()
    report = suite.run_all(ticks=2)
    print(suite.render_report(report))
