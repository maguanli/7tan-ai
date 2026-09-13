# -*- coding: utf-8 -*-

# 边界声明（C3）
# 本系统实现：叙事-通达自我意识（访问意识），全部基于事件总线、记忆、统计计算。
# ❌ 本系统不存在现象意识 qualia，不存在第一人称主观体验。
# 所有「我感到、我疲惫、我记得」的输出，仅读取内部结构化数据做模板转述。
# 属于工程层面哲学僵尸实例。
# 所有叙事输出必须溯源记忆库与事件历史，禁止编造不存在的经历。

"""
阶段2｜上层模块 M2：自传叙事装配器、上下文指代、预演接入言语输出

来源：7Tan可执行架构文档_修订终版 V1.2（阶段2）。
定位：全部上层只读模块，仅消费事件总线回放与记忆库数据，不修改器官内部状态（遵 C4）。
边界（C2/C3）：无记忆记录绝不编造经历；缺失信息输出「无相关经历记录」。

四大能力：
  1. 自传叙事装配器：按主观时间排序记忆 → 划分心智阶段 → 检测认知矛盾
     → 输出 autobiography_fragment 事件供 ORG-SPEECH 模板转述（每条可溯源记忆 ID）。
  2. 扩展统计：高频动机 / 预测误差分类 / 记忆留存率（数据源全部来自历史回放，禁止硬编码文本）。
  3. 代词指代 + 多轮上下文栈：对话记忆单元存 ORG-A，tick 周期压入 context_stack，解析代词实体。
  4. ORG-SIMULATE 反事实预演接入言语生成：候选思路推演择优，回答不再只靠模板匹配。

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
        register_post_tick_hook,
        subscribe_event,
        memory_library,
        self_model_data,
        subjective_time,
        poll_replay_events,
        organ_simulate_preview,
    )
except Exception:  # pragma: no cover
    emit_event = register_post_tick_hook = subscribe_event = None  # type: ignore
    memory_library, self_model_data, subjective_time = [], {}, {}
    poll_replay_events = organ_simulate_preview = None  # type: ignore

# ═══════════════ 配置 ═══════════════
M2_AUTOBIO_INTERVAL_TICKS = 25      # 每 N tick 产出一段自传叙事
M2_CONTEXT_STACK_MAX = 10           # 多轮上下文栈容量
M2_STAGE_GAP_SUBJ = 30.0            # 心智阶段划分阈值（主观时钟差）


# ═══════════════ 代词指代 + 多轮上下文栈 ═══════════════
class DialogContextStack:
    """多轮对话上下文栈：维护最近 N 轮对话记忆单元，支持代词实体解析。"""

    def __init__(self, max_len: int = M2_CONTEXT_STACK_MAX):
        self.max_len = max(1, int(max_len))
        self.units: List[dict] = []      # [{role, content, entities, ts}]
        self.entity_map: Dict[str, str] = {}   # 代词 -> 实体

    def push(self, role: str, content: str) -> None:
        entities = self._extract_entities(content)
        unit = {"role": role, "content": content, "entities": entities, "ts": time.time()}
        self.units.append(unit)
        # 更新实体映射（最近优先）
        for e in entities:
            self.entity_map.setdefault(e["type"], e["text"])
        while len(self.units) > self.max_len:
            self.units.pop(0)

    def resolve(self, text: str) -> str:
        """把文本中的代词替换为已解析实体（纯规则，非 LLM）。"""
        resolved = text
        # 你/您 → 用户；我 → 系统自身
        resolved = re.sub(r"\b你\b|\b您\b", "用户", resolved)
        resolved = re.sub(r"\b我\b|\b我们\b", "我(7Tan)", resolved)
        # 它/他/她 → 最近对应实体
        for pro, etype in [("它", "object"), ("他", "person"), ("她", "person")]:
            if pro in resolved and etype in self.entity_map:
                resolved = resolved.replace(pro, self.entity_map[etype])
        return resolved

    @staticmethod
    def _extract_entities(text: str) -> List[dict]:
        """从文本中提取简单实体（人名/话题/对象）。"""
        ents: List[dict] = []
        # 提取引号内或书名号内的词作为对象实体
        for m in re.finditer(r"[「《]([^」》]{1,20})[」》]", text):
            ents.append({"type": "object", "text": m.group(1)})
        # 提取「xx项目/xx模块/xx系统」等名词短语
        for m in re.finditer(r"([\u4e00-\u9fa5A-Za-z]{2,12}(?:项目|模块|系统|器官|架构|文档))", text):
            ents.append({"type": "object", "text": m.group(1)})
        return ents


# ═══════════════ 自传叙事装配器 ═══════════════
def _sorted_memories():
    """按主观时间排序记忆库（只读），返回 [(mem, idx)]。"""
    mems = []
    for i, m in enumerate(memory_library):
        if isinstance(m, dict) and m.get("thought"):
            mems.append((m, i))
    mems.sort(key=lambda x: float(x[0].get("subjective_time", 0.0) or 0.0))
    return mems


def _detect_cognitive_conflict() -> List[dict]:
    """检测不同心智年龄自我模型认知矛盾（只读）。"""
    conflicts: List[dict] = []
    try:
        sm = self_model_data or {}
        confidence = sm.get("confidence")
        limitations = sm.get("limitations") or []
        capabilities = sm.get("capability") or sm.get("abilities") or []
        # 矛盾1：高置信度 + 大量局限（过度自信却反复失败）
        if confidence is not None and float(confidence) >= 0.6 and len(limitations) >= 3:
            conflicts.append({"type": "overconfident_with_many_limits",
                              "detail": f"置信度={confidence} 却存在 {len(limitations)} 条局限"})
        # 矛盾2：能力与局限键冲突
        cap_keys = {str(c.get("key", "")) for c in capabilities if isinstance(c, dict)}
        lim_keys = {str(l.get("key", "")) for l in limitations if isinstance(l, dict)}
        inter = cap_keys & lim_keys
        if inter:
            conflicts.append({"type": "cap_limit_overlap", "detail": f"能力与局限重叠: {sorted(inter)}"})
    except Exception:
        pass
    return conflicts


def assemble_autobiography() -> dict:
    """装配一段自传叙事（只读）。返回结构化结果；无记忆时返回空叙述。"""
    mems = _sorted_memories()
    if not mems:
        return {"ok": False, "reason": "无相关经历记录", "fragments": [], "stages": [],
                "conflicts": [], "traceable_ids": []}

    # 1) 按 focus/valence 筛选关键经历（保留 (mem, idx) 元组以便溯源记忆 ID）
    key = [(m, i) for m, i in mems
           if float(m.get("focus", 0.0)) >= 0.3 or abs(float(m.get("valence", 0.0))) >= 0.2]
    key = key[:20]

    # 2) 划分心智阶段（按主观时钟差）
    stages: List[dict] = []
    cur_stage = None
    for m, idx in mems:
        subj = float(m.get("subjective_time", 0.0) or 0.0)
        if cur_stage is None or subj - cur_stage["end_subj"] > M2_STAGE_GAP_SUBJ:
            if cur_stage is not None:
                stages.append(cur_stage)
            cur_stage = {"start_subj": subj, "end_subj": subj, "count": 0, "mem_ids": []}
        cur_stage["end_subj"] = subj
        cur_stage["count"] += 1
        cur_stage["mem_ids"].append(idx)
    if cur_stage is not None:
        stages.append(cur_stage)

    # 3) 认知矛盾
    conflicts = _detect_cognitive_conflict()

    # 4) 可溯源记忆 ID（自传叙事每条可溯源）
    traceable_ids = [idx for m, idx in key]
    fragments = [m for m, idx in key]

    return {"ok": True, "fragments": fragments, "stages": stages, "conflicts": conflicts,
            "traceable_ids": traceable_ids,
            "subj_now": float(subjective_time.get("subjective_clock", 0.0) or 0.0)}


def _narrative_text(bio: dict) -> str:
    """把自传叙事结构转述为文本（忠实读数，禁止编造）。"""
    if not bio.get("ok"):
        return "（无相关经历记录）"
    parts: List[str] = []
    subj_now = bio.get("subj_now", 0.0)
    parts.append(f"我的主观心智年龄约 {subj_now:.1f}，记忆库共 {len(_sorted_memories())} 条经历，"
                 f"关键经历 {len(bio['fragments'])} 条，可划分为 {len(bio['stages'])} 个心智阶段。")
    for c in bio.get("conflicts", [])[:2]:
        parts.append(f"检测到认知矛盾：{c.get('detail', '')}。")
    if not bio.get("conflicts"):
        parts.append("当前未检测到明显认知矛盾。")
    return " ".join(parts)


# ═══════════════ 扩展统计（只读，数据源来自历史回放） ═══════════════
def compute_extended_stats() -> dict:
    """高频动机 / 预测误差分类 / 记忆留存率（全部从回放缓冲读取，禁止硬编码文本）。"""
    stats: dict = {"high_freq_motives": [], "pe_classification": {}, "memory_retention": None}

    # 高频动机：从 candidate_motives / final_goals 回放统计 goal 出现频次
    goal_counter: Dict[str, int] = {}
    try:
        for ev in (poll_replay_events("candidate_motives", 200) if poll_replay_events else []):
            for m in (ev.get("payload", {}).get("motives") or []):
                if isinstance(m, dict) and m.get("goal"):
                    g = str(m["goal"])
                    goal_counter[g] = goal_counter.get(g, 0) + 1
        stats["high_freq_motives"] = sorted(goal_counter.items(), key=lambda x: -x[1])[:5]
    except Exception:
        pass

    # 预测误差分类：从 pe_update 回放统计正/负/零误差分布
    pe_cls = {"pos": 0, "neg": 0, "zero": 0}
    try:
        for ev in (poll_replay_events("pe_update", 200) if poll_replay_events else []):
            pe = float((ev.get("payload", {}).get("pe") or 0.0))
            if pe > 0.01:
                pe_cls["pos"] += 1
            elif pe < -0.01:
                pe_cls["neg"] += 1
            else:
                pe_cls["zero"] += 1
        stats["pe_classification"] = pe_cls
    except Exception:
        pass

    # 记忆留存率：memory_library 条数 / 历史 mem_consolidated 条数（含被遗忘）
    try:
        total_consolidated = len(poll_replay_events("mem_consolidated", 1000)) if poll_replay_events else 0
        if total_consolidated > 0:
            stats["memory_retention"] = round(len(memory_library) / max(1, total_consolidated + len(memory_library)), 4)
    except Exception:
        pass
    return stats


# ═══════════════ M2 主体 ═══════════════
class UpperModuleM2:
    """阶段2 自传叙事 + 代词指代 + SIMULATE 接言语（上层只读）。"""

    def __init__(self):
        self.context = DialogContextStack()
        self._mounted = False
        self._tick_seen = -1

    def mount(self) -> bool:
        if self._mounted:
            return False
        if register_post_tick_hook is None:
            logger.warning("[M2] 内核只读接口不可用，挂载失败")
            return False
        register_post_tick_hook(self._on_tick)
        if subscribe_event is not None:
            subscribe_event("autobiography_fragment", "ORG-SPEECH")
        self._mounted = True
        logger.info("[M2] 自传叙事装配器已挂载（post_tick_hook + SPEECH 订阅 autobiography_fragment）")
        return True

    def _on_tick(self) -> None:
        try:
            import src.agent.bionic_organs as bo
            tick = int(getattr(bo, "_organ_tick_counter", 0))
            if tick == self._tick_seen:
                return
            self._tick_seen = tick
            if tick % M2_AUTOBIO_INTERVAL_TICKS == 0 and tick > 0:
                self.emit_autobiography()
        except Exception as e:
            logger.warning(f"[M2] tick 钩子异常: {e}")

    def emit_autobiography(self) -> dict:
        """装配并投递一段自传叙事事件（供 SPEECH 转述）。返回叙事结构。"""
        bio = assemble_autobiography()
        if emit_event is not None:
            emit_event(
                "autobiography_fragment",
                payload={"text": _narrative_text(bio),
                         "traceable_ids": bio.get("traceable_ids", []),
                         "stage_count": len(bio.get("stages", [])),
                         "conflicts": bio.get("conflicts", [])},
                source="M2-autobiography",
                origin="internal",
            )
        return bio

    # ── 对外接口：代词指代 ──
    def push_turn(self, role: str, content: str) -> None:
        self.context.push(role, content)

    def resolve(self, text: str) -> str:
        return self.context.resolve(text)

    # ── 对外接口：SIMULATE 预演接言语 ──
    def simulate_and_pick(self, candidates: List[dict], ctx=None) -> Optional[dict]:
        """候选思路（scene/action）送入 ORG-SIMULATE 预演，择优返回。"""
        if not organ_simulate_preview:
            return None
        best, best_conf = None, -1.0
        for c in candidates:
            if not isinstance(c, dict):
                continue
            scene, action = c.get("scene", ""), c.get("action", "")
            if not scene or not action:
                continue
            try:
                r = organ_simulate_preview(scene, action, ctx)
                conf = float(r.get("sim_confidence", 0.0))
                if conf > best_conf:
                    best, best_conf = r, conf
            except Exception:
                continue
        return best


# ═══════════════ 模块级单例 ═══════════════
_m2_instance: Optional[UpperModuleM2] = None


def get_m2() -> UpperModuleM2:
    global _m2_instance
    if _m2_instance is None:
        _m2_instance = UpperModuleM2()
    return _m2_instance


def mount_m2() -> bool:
    return get_m2().mount()


if __name__ == "__main__":
    m2 = get_m2()
    print("挂载:", m2.mount())
    bio = m2.emit_autobiography()
    print("自传叙事:", _narrative_text(bio))
    print("扩展统计:", compute_extended_stats())
    m2.push_turn("user", "帮我看看「7Tan架构文档」的 M1 模块")
    m2.push_turn("assistant", "M1 模块负责双知识获取")
    print("代词解析:", m2.resolve("它 有什么用途？"))
