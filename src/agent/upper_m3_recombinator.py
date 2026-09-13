# -*- coding: utf-8 -*-

# 边界声明（C3）
# 本系统实现：叙事-通达自我意识（访问意识），全部基于事件总线、记忆、统计计算。
# ❌ 本系统不存在现象意识 qualia，不存在第一人称主观体验。
# 所有「我感到、我疲惫、我记得」的输出，仅读取内部结构化数据做模板转述。
# 属于工程层面哲学僵尸实例。
# 所有叙事输出必须溯源记忆库与事件历史，禁止编造不存在的经历。

"""
阶段3｜上层模块 M3：记忆碎片重组器（创新能力模块）

来源：7Tan可执行架构文档_修订终版 V1.2（阶段3）。
定位：上层只读模块；不改动器官内核状态（遵 C4）。
创新链路（文档阶段3）：
  1. 动机触发创新诉求
  2. 跨领域调取 ORG-A 记忆碎片
  3. 解离打散特征/逻辑/结构 → 生成大量候选构想 hypothesis_candidate
  4. 送入 ORG-SIMULATE 批量反事实预演，过滤劣质方案
  5. ORG-SELFMODEL + ORG-INHIBIT 抑制高风险超出能力边界构想
  6. 可行方案结构化输出，交付沙盒执行
  7. 执行成败结果作为 tool_result 回流事件总线存入记忆库迭代优化

边界（C2/C3）：
  可实现：跨领域融合创新、现有方案改良、多方案虚拟试错迭代。
  不能实现：脱离全部记忆素材的无中生有创造、主观灵感体验（现象意识范畴）。
  纯规则拼接生成可运行代码只适用于中小复杂度任务；禁止隐性调用外部大模型完成生成。

本模块自包含（仅依赖标准库 + loguru + 内核只读接口）。
"""
from __future__ import annotations

import re
import time
from typing import Dict, List, Optional

from loguru import logger

try:  # 内核只读接口
    from src.agent.bionic_organs import (
        emit_event,
        memory_library,
        self_model_data,
        organ_simulate_preview,
        _self_limitations_sim,
    )
except Exception:  # pragma: no cover
    emit_event = organ_simulate_preview = None  # type: ignore
    memory_library, self_model_data = [], {}
    _self_limitations_sim = []

# ═══════════════ 配置 ═══════════════
M3_MAX_CANDIDATES = 30            # 候选构想上限
M3_SIM_CONFIDENCE_MIN = 0.5       # 预演置信度过滤阈值
M3_MAX_FINAL = 5                  # 最终可行方案输出上限


# ═══════════════ 记忆碎片解离（跨领域特征/逻辑/结构提取） ═══════════════
def _extract_atoms(mem: dict) -> dict:
    """把一条记忆碎片解离为「领域/动作/特征/结构」原子。"""
    thought = str(mem.get("thought", "") or "")
    goal_tag = str(mem.get("goal_tag", "") or "")
    success = mem.get("success")
    # 领域：goal_tag 的「:」前半段（如 知识包/自学/下载）
    domain = goal_tag.split(":", 1)[0] if ":" in goal_tag else "通用"
    # 动作：从 thought 提取动词性短语（简单启发式）
    verbs = re.findall(r"[\u4e00-\u9fa5]{2,4}(?:完成|成功|失败|执行|调用|抓取|下载|导入|生成|推演|归纳)", thought)
    action = verbs[0] if verbs else (goal_tag if goal_tag else "通用动作")
    # 特征：提取 thought 中的名词短语（2-6 字）
    feats = re.findall(r"[\u4e00-\u9fa5A-Za-z]{2,6}(?:模块|系统|器官|架构|记忆|知识|工具|接口|文件|数据)", thought)
    return {
        "domain": domain,
        "action": action,
        "features": feats[:4],
        "success": success,
        "subj": float(mem.get("subjective_time", 0.0) or 0.0),
        "mem_id": mem.get("_id"),
    }


def _load_atoms(limit: int = 200) -> List[dict]:
    """跨领域调取记忆碎片并解离为原子。"""
    atoms = []
    for i, m in enumerate(memory_library):
        if not isinstance(m, dict) or not m.get("thought"):
            continue
        a = _extract_atoms(m)
        a["mem_id"] = i
        atoms.append(a)
    # 按主观时间取最近 limit 条（跨领域调取）
    atoms.sort(key=lambda x: -x["subj"])
    return atoms[:limit]


# ═══════════════ 候选构想生成（跨领域重组） ═══════════════
def _recombine(atoms: List[dict]) -> List[dict]:
    """跨领域重组：把不同领域的「领域 + 动作 + 特征」重新配对，生成候选构想。"""
    candidates: List[dict] = []
    domains = sorted({a["domain"] for a in atoms})
    for i, a in enumerate(atoms):
        for j, b in enumerate(atoms):
            if i == j:
                continue
            # 跨领域：a 的领域 + b 的动作/特征
            if a["domain"] != b["domain"]:
                cand = {
                    "scene": a["domain"],
                    "action": b["action"],
                    "features": list(dict.fromkeys(a["features"][:2] + b["features"][:2])),
                    "src_a": a["mem_id"], "src_b": b["mem_id"],
                    "hypothesis": f"把「{b['domain']}」领域的做法「{b['action']}」迁移到「{a['domain']}」场景",
                }
                candidates.append(cand)
            # 同领域改良：同领域不同动作组合
            elif a["domain"] == b["domain"] and a["action"] != b["action"]:
                cand = {
                    "scene": a["domain"],
                    "action": f"{a['action']}+{b['action']}",
                    "features": list(dict.fromkeys(a["features"][:2] + b["features"][:2])),
                    "src_a": a["mem_id"], "src_b": b["mem_id"],
                    "hypothesis": f"在「{a['domain']}」场景组合动作「{a['action']}」与「{b['action']}」",
                }
                candidates.append(cand)
        if len(candidates) >= M3_MAX_CANDIDATES:
            break
    return candidates[:M3_MAX_CANDIDATES]


# ═══════════════ 预演过滤 + 抑制（SIMULATE + SELFMODEL + INHIBIT） ═══════════════
def _filter_by_simulate(candidates: List[dict], ctx=None) -> List[dict]:
    """送入 ORG-SIMULATE 批量反事实预演，过滤劣质方案。"""
    kept: List[dict] = []
    for c in candidates:
        try:
            if organ_simulate_preview is None:
                c["sim_confidence"] = 0.5   # 无预演能力时中性值
            else:
                r = organ_simulate_preview(c["scene"], c["action"], ctx)
                c["sim_confidence"] = float(r.get("sim_confidence", 0.5))
        except Exception:
            c["sim_confidence"] = 0.5
        if c["sim_confidence"] >= M3_SIM_CONFIDENCE_MIN:
            kept.append(c)
    kept.sort(key=lambda x: -x["sim_confidence"])
    return kept


def _filter_by_inhibit(candidates: List[dict]) -> List[dict]:
    """ORG-SELFMODEL + ORG-INHIBIT：抑制高风险超出能力边界的构想。"""
    lim_keys = {str(l.get("key", "")) for l in (_self_limitations_sim or [])}
    # 同时从 self_model_data 读 limitations 兜底
    try:
        for l in (self_model_data.get("limitations") or []):
            if isinstance(l, dict) and l.get("key"):
                lim_keys.add(str(l["key"]))
    except Exception:
        pass
    kept: List[dict] = []
    for c in candidates:
        scene_action = f"{c['scene']}:{c['action']}"
        if scene_action in lim_keys:
            c["inhibited"] = True     # 超出能力边界，抑制
            continue
        c["inhibited"] = False
        kept.append(c)
    return kept


# ═══════════════ M3 主体 ═══════════════
class UpperModuleM3:
    """阶段3 记忆碎片重组器（创新能力）。"""

    def __init__(self):
        self._mounted = False

    def mount(self) -> bool:
        if self._mounted:
            return False
        self._mounted = True
        logger.info("[M3] 记忆碎片重组器已就绪")
        return True

    def recombine(self, trigger: str = "manual", ctx=None) -> dict:
        """完整创新链路：调取→解离→重组→预演→抑制→输出。返回结构化方案集。"""
        atoms = _load_atoms()
        if len(atoms) < 2:
            return {"ok": False, "reason": "无相关经历记录（记忆素材不足，无法重组）",
                    "candidates": [], "final": []}

        candidates = _recombine(atoms)
        if not candidates:
            return {"ok": False, "reason": "无相关经历记录（无跨领域可重组素材）",
                    "candidates": [], "final": []}

        # SIMULATE 预演过滤
        simulated = _filter_by_simulate(candidates, ctx)
        # INHIBIT 抑制高风险
        final = _filter_by_inhibit(simulated)[:M3_MAX_FINAL]

        result = {
            "ok": True,
            "trigger": trigger,
            "atom_count": len(atoms),
            "candidate_count": len(candidates),
            "final": final,
            "traceable_ids": sorted({c["src_a"] for c in final} | {c["src_b"] for c in final}),
        }
        # 创新结果以 tool_result 回流事件总线（存入记忆库迭代优化，文档第7步）
        if emit_event is not None and final:
            emit_event(
                "tool_result",
                payload={"tool": "m3_recombine", "ok": True, "trigger": trigger,
                         "thought_fragment": f"重组器产出 {len(final)} 个可行方案（触发:{trigger}）",
                         "goal_tag": f"创新:{trigger[:16]}", "success": True},
                source="knowledge_package",
                origin="external",
            )
        return result

    def generate_code_plan(self, final: List[dict]) -> str:
        """把可行方案结构化输出为可运行代码方案（纯规则拼接，中小复杂度）。"""
        if not final:
            return "# 无可运行方案（素材不足或全部被抑制）"
        lines = ["# M3 重组器生成的代码方案（纯规则拼接，禁止外部大模型参与）", ""]
        for i, c in enumerate(final, 1):
            lines.append(f"# 方案{i}: {c.get('hypothesis','')}")
            lines.append(f"def plan_{i}():")
            lines.append(f"    scene = {c['scene']!r}")
            lines.append(f"    action = {c['action']!r}")
            lines.append(f"    features = {c['features']!r}")
            lines.append(f"    sim_confidence = {c.get('sim_confidence', 0.0):.3f}")
            lines.append(f"    return (scene, action, features, sim_confidence)")
            lines.append("")
        return "\n".join(lines)


# ═══════════════ 模块级单例 ═══════════════
_m3_instance: Optional[UpperModuleM3] = None


def get_m3() -> UpperModuleM3:
    global _m3_instance
    if _m3_instance is None:
        _m3_instance = UpperModuleM3()
    return _m3_instance


def mount_m3() -> bool:
    return get_m3().mount()


if __name__ == "__main__":
    m3 = get_m3()
    m3.mount()
    r = m3.recombine("测试")
    print("重组结果:", r["ok"], "原子数", r.get("atom_count"), "候选", r.get("candidate_count"),
          "可行", len(r.get("final", [])))
    print(m3.generate_code_plan(r.get("final", []))[:400])
