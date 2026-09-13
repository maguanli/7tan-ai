"""器官快照 → 言语输出 接入层（self_snapshot_access_guide.txt 落地）。

打通【器官快照 → 言语输出】通路：
  1. 用户问自身感受/状态 → 不再输出硬编码模板话术；
  2. 读取 self-model 真实快照数据（self_model_data + 躯体稳态信号）；
  3. 输出带取证日志标记 [SPEECH][source:bionic_organ.selfmodel]；
  4. 记忆库内容仅作辅助补充，不作回答主体。

⚠️ 忠实声明（必须随代码保留）：
   本链路仅读取结构化变量做文本转述，不产生现象意识 qualia，无真实主观感受，
   属于功能性仿真（access consciousness）。渲染层不使用任何拟人化句式模板，
   只做「字段名 + 数值」的忠实读数转述（可回溯），绝无 LLM 生成或自由发挥。

与文档 self_snapshot_access_guide.txt 的差异（如实说明）：
   文档原假设 get_snapshot() 返回 mood/energy/inner_event_history，并给了一段
   mood_text_map 拟人化渲染模板。但本项目真实结构是：
     - 自我模型快照 = bionic_organs.self_model_data（结构化，无自然语言）；
     - 躯体稳态读数 = bionic_organs.speech_state（fatigue/resource_pressure/damage_level）；
     - ORG-SELFMODEL 的 BionicOrgan 实例没有 get_snapshot() 方法。
   且用户已明确「去掉拟人化模板」。故本文件按文档架构意图落地，但渲染层保持
   忠实读数转述（可读卡片式排版），不照抄 mood_text_map 拟人化句式。

渲染方案说明（用户选定方案 B）：
   render_self_snapshot 不做纯 JSON 转储，而是把快照渲染成人类可读的分组卡片，
   但每一条仍严格是「字段名（英文 key，可回溯）+ 数值」，不添加任何拟人化句式
   （不说"我很累""我心里踏实"之类），也不对数值做主观解读。对于超长明细列表
   （预测误差历史等）只做展示层截断并标注"可回溯"，不编造、不丢失语义。
"""
from __future__ import annotations

import json
from typing import Any, Dict

from loguru import logger

# mind_flaws.type 的枚举值 → 中文标签（仅做枚举翻译，非拟人化解读）
# 只收录已知枚举；未收录的保持英文原值，保证可回溯、不瞎编。
_FLAW_CN: Dict[str, str] = {
    "self_underconfident": "自我低估",
    "self_overconfident": "自我高估",
    "overconfident": "过度自信",
    "underconfident": "自信不足",
}


def _num(v: Any, nd: int = 4) -> str:
    """数值安全格式化：None→"无"，float→有效数字，其余→str。"""
    if v is None:
        return "无"
    if isinstance(v, float):
        return f"{v:.{nd}g}"
    return str(v)


def _clip(v: Any, n: int = 40) -> str:
    """字符串安全截断（超长明细仅展示层截断，标注省略号）。"""
    s = str(v)
    return s if len(s) <= n else s[:n] + "…"


def get_self_snapshot() -> Dict[str, Any]:
    """从 ORG-SELFMODEL(self_model_data) + 躯体稳态信号 组装真实快照。

    对应文档第四部分的 get_snapshot() 接口：本实现里真实自我模型快照是
    bionic_organs.self_model_data，躯体稳态读数在 bionic_organs.speech_state。
    ORG-SELFMODEL 被禁用/未注册时返回空 dict（触发降级提示，对应文档测试4）。
    """
    try:
        from .bionic_organs import organ_registry, self_model_data, speech_state, subjective_time
    except Exception as e:  # pragma: no cover - 导入失败即降级
        logger.warning(f"[self_snapshot] 无法导入器官状态模块: {e}")
        return {}

    # 降级检查：ORG-SELFMODEL 未注册或被禁用 → 返回空（触发降级提示，禁止旧模板）
    org = organ_registry.get("ORG-SELFMODEL")
    if org is None or not getattr(org, "enabled", False):
        logger.warning("[self_snapshot] ORG-SELFMODEL 不可用，返回空快照（降级）")
        return {}

    snap: Dict[str, Any] = {}
    # ① 躯体稳态信号（ORG-BODYSTATES 最近读数）
    for k in ("fatigue", "resource_pressure", "damage_level"):
        snap[k] = speech_state.get(k, 0.0)
    # ② 自我模型快照（ORG-SELFMODEL 归纳结果）
    for k in ("confidence", "history_summary", "limitations", "capability",
              "preferred_motives", "internal_signature", "prediction_error_history",
              "meta_cognition", "counterfactual_stats", "mind_flaws"):
        snap[k] = self_model_data.get(k)
    # ③ 主观时钟
    snap["subjective_clock"] = subjective_time.get("subjective_clock", 0.0)
    return snap


def render_self_snapshot(snapshot: Dict[str, Any]) -> str:
    """忠实读数转述（方案 B）：渲染为可读分组卡片，字段名+数值，无拟人化、无模板、无 LLM。"""
    if not snapshot:
        return ""

    L: list = []
    L.append("【器官快照 · 忠实读数】")

    # ---------------- 躯体稳态 ----------------
    L.append("· 躯体稳态")
    L.append(f"  - 疲劳 fatigue = {_num(snapshot.get('fatigue'))}")
    L.append(f"  - 资源压力 resource_pressure = {_num(snapshot.get('resource_pressure'))}")
    L.append(f"  - 损伤水平 damage_level = {_num(snapshot.get('damage_level'))}")

    # ---------------- 自我模型 ----------------
    L.append("· 自我模型")
    L.append(f"  - 置信度 confidence = {_num(snapshot.get('confidence'))}")

    hs = snapshot.get("history_summary") or {}
    if hs:
        L.append(
            f"  - 历史目标 history_summary = 目标{_num(hs.get('total_goal'))}"
            f" / 成功{_num(hs.get('total_success'))} / 失败{_num(hs.get('total_fail'))}"
        )

    lim = snapshot.get("limitations")
    if lim:
        L.append(f"  - 局限 limitations = {_clip(lim, 80)}")
    else:
        L.append("  - 局限 limitations = (空)")

    cap = snapshot.get("capability") or []
    if cap:
        caps = []
        for c in cap[:8]:
            if isinstance(c, dict):
                k = c.get("key") or c.get("goal_tag") or "?"
                caps.append(f"{_clip(k, 24)}({_num(c.get('success_rate'))})")
            else:
                caps.append(_clip(c, 30))
        tail = "…" if len(cap) > 8 else ""
        L.append(f"  - 能力 capability[{len(cap)}] = " + ", ".join(caps) + tail)
    else:
        L.append("  - 能力 capability = (空)")

    pm = snapshot.get("preferred_motives") or []
    if pm:
        motives = []
        for m in pm[:5]:
            if isinstance(m, dict):
                motives.append(f"{_clip(m.get('motive_tag'), 36)}×{_num(m.get('occur_count'))}")
            else:
                motives.append(_clip(m, 36))
        L.append("  - 高频动机 preferred_motives[Top%d] = " % min(5, len(pm)) + "，".join(motives))
    else:
        L.append("  - 高频动机 preferred_motives = (空)")

    sig = snapshot.get("internal_signature") or {}
    if sig:
        L.append(
            f"  - 内部签名 internal_signature = 疲劳均值{_num(sig.get('fatigue_avg'))}"
            f" / 资源压力均值{_num(sig.get('resource_pressure_avg'))}"
            f" / PE均值{_num(sig.get('pe_avg'))} / LP均值{_num(sig.get('lp_avg'))}"
        )

    peh = snapshot.get("prediction_error_history") or []
    if peh:
        pes = [e.get("pe") for e in peh if isinstance(e, dict) and e.get("pe") is not None]
        if pes:
            pe_mean = sum(pes) / len(pes)
            L.append(
                f"  - 预测误差 prediction_error_history[{len(peh)}条] = PE均值{pe_mean:.3g}"
                f"（明细省略，可回溯）"
            )
        else:
            L.append(f"  - 预测误差 prediction_error_history[{len(peh)}条] = (无有效PE)")
    else:
        L.append("  - 预测误差 prediction_error_history = (空)")

    mc = snapshot.get("meta_cognition") or {}
    if mc:
        L.append(
            f"  - 元认知 meta_cognition = 校准差距{_num(mc.get('calibration_gap'))}"
            f" / 模拟置信均值{_num(mc.get('sim_conf_mean'))}"
            f" / 实际成功率{_num(mc.get('actual_success_rate'))}"
            f" / 遗憾率{_num(mc.get('regret_rate'))}"
            f" / PE趋势{mc.get('pe_trend') or '无'}"
        )

    cf = snapshot.get("counterfactual_stats") or {}
    if cf:
        L.append(
            f"  - 反事实统计 counterfactual_stats = 共{_num(cf.get('total'))}"
            f" / 更优替代{_num(cf.get('better_alternative'))}"
        )

    mf = snapshot.get("mind_flaws") or []
    if mf:
        flaws = []
        for f in mf:
            if isinstance(f, dict):
                t = str(f.get("type") or "?")
                cn = _FLAW_CN.get(t)
                label = f"{t}({cn})" if cn else t
                flaws.append(
                    f"{label}：模拟置信{_num(f.get('sim_conf_mean'))}"
                    f" vs 实际成功率{_num(f.get('actual_success_rate'))}"
                    f"，差距{_num(f.get('gap'))}"
                )
            else:
                flaws.append(_clip(f, 50))
        L.append("  - ⚠️ 心智缺陷 mind_flaws = " + "；".join(flaws))
    else:
        L.append("  - 心智缺陷 mind_flaws = (无)")

    L.append(f"  - 主观时钟 subjective_clock = {_num(snapshot.get('subjective_clock'))}")

    return "\n".join(L)


def speech_handle_emotion_query(memory_limit: int = 1) -> str:
    """意图命中 emotion/query_self_state 时调用：主快照 + 取证日志 + 可选记忆辅助。

    :param memory_limit: 最多取几条记忆做辅助后缀（0=关闭）。记忆库仅作补充，绝不作主体。
    :return: 组装完成的回答字符串。
    """
    # ---------------- 主内容：来自器官快照（最高优先级） ----------------
    snapshot = get_self_snapshot()
    main_text = render_self_snapshot(snapshot)
    if not main_text:
        # 降级：器官不可用时如实说明，禁止使用旧的体验模板（文档测试4）
        return "暂时无法读取我的内部器官状态。"

    # 强制打印取证日志（A组测试判断来源）
    logger.info(f"[SPEECH][source:bionic_organ.selfmodel] {main_text}")

    # ---------------- 可选：记忆库仅作辅助补充（次要，不作主体） ----------------
    aux_text = ""
    if memory_limit > 0:
        try:
            from .bionic_organs import memory_library
            recent = memory_library[-memory_limit:] if memory_library else []
            parts = []
            for m in recent:
                if not isinstance(m, dict):
                    parts.append(str(m)[:80])
                    continue
                thought = m.get("thought") or m.get("goal_tag") or m.get("text")
                if thought:
                    parts.append(str(thought)[:80])
            if parts:
                aux_text = "\n补充一点过往记忆片段：" + "｜".join(parts)
        except Exception:
            aux_text = ""

    return main_text + aux_text
