# -*- coding: utf-8 -*-
"""
模块F：L1-记忆级自我学习闭环（L1 Memory-level Self-Learning Loop）

来源：智能生命项目 · 第四册设计稿（模块F完整设计）。
前置依赖：模块A（TanModelMemory）、模块B（PE/LP）、模块E（工作记忆）；模块D作为兜底防护。
定位：只修改模块A记忆库内记忆条目权重、新增/标记记忆，
      绝不修改源码，不改动程序参数（L2参数级学习/源码进化归属模块D，不在F范围内）。

完整闭环链路：
  预测(B.predict_outcome) → 获取现实观测结果 → compute_pe()/compute_lp() 计算误差与学习进度
  → PE/LP送入模块E工作记忆 → scratch_pad生成猜想假设（E模块）
  → decompose_goals生成验证子目标（E模块） → 执行验证（现实交互/历史记忆回溯验证）
  → F.evaluate_hypothesis()评估假设真伪置信度 → F.apply_memory_update()更新模块A长期记忆库
  → 更新后的记忆库参与下一轮世界模型预测，完成闭环

核心约束：猜想不会直接写入长期记忆；必须经过 evaluate_hypothesis 评估置信度，
          达到阈值才允许落地到记忆库，避免错误猜想直接污染记忆库。

安全红线（F5）：
  ✔ 永远不主动删除热记忆；只能下调权重。
  ✔ 所有修改操作产生变更日志记录到本地日志文件（*.hypothesis.log），便于回溯调试。
  ✔ 不修改源码、不修改全局超参数。

模块F 无条件启用，无需开关。
本模块自包含（仅依赖标准库 + loguru）。
"""
from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path
from typing import Optional

from loguru import logger

# ═══════════════ 阈值参数 ═══════════════
HYPO_MIN_TESTS = 2            # 最少验证次数，低于则 suspended
HYPO_PASS_THRESHOLD = 0.6     # 通过阈值 → verified
HYPO_REJECT_THRESHOLD = 0.3   # 拒绝阈值 → rejected
MEMORY_BUMP_STRENGTH = 0.08   # Mode1 记忆权重上调系数
MEMORY_WEAKEN_STRENGTH = 0.15 # Mode3 错误记忆权重下调系数

_HYPO_LOG_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "tan_hypothesis.log"


def _log_change(msg: str):
    """所有记忆变更追加写入 *.hypothesis.log（可审计）。"""
    try:
        _HYPO_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_HYPO_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception as e:
        logger.warning(f"假设日志写入失败: {e}")


class Hypothesis:
    """hypothesis_obj（F1 核心对象）"""

    __slots__ = ("hypothesis_id", "content", "source_trace_id", "confidence_raw",
                 "test_count", "success_count", "fail_count", "final_confidence",
                 "status", "created_ts", "updated_ts", "feedback_queue")

    def __init__(self, hypothesis_id: str, content: dict, source_trace_id: str,
                 confidence_raw: float):
        self.hypothesis_id = hypothesis_id
        self.content = content
        self.source_trace_id = source_trace_id
        self.confidence_raw = max(0.0, min(1.0, float(confidence_raw)))
        self.test_count = 0
        self.success_count = 0
        self.fail_count = 0
        self.final_confidence = self.confidence_raw
        self.status = "pending"     # pending|verified|rejected|suspended
        self.created_ts = time.time()
        self.updated_ts = time.time()
        self.feedback_queue: list = []   # 待处理的观测反馈（f_selflearn_tick 消费）

    def to_dict(self) -> dict:
        return {
            "hypothesis_id": self.hypothesis_id, "content": self.content,
            "source_trace_id": self.source_trace_id,
            "confidence_raw": self.confidence_raw,
            "test_count": self.test_count, "success_count": self.success_count,
            "fail_count": self.fail_count,
            "final_confidence": self.final_confidence, "status": self.status,
            "created_ts": self.created_ts, "updated_ts": self.updated_ts,
        }


class SelfLearnEngine:
    """模块F引擎：注册假设 → 评估 → 落地记忆，闭合学习闭环。"""

    def __init__(self, memory):
        self.memory = memory                    # 模块A：TanModelMemory
        self.hypothesis_registry: list = []     # 全部待评估 hypothesis_obj 引用

    # ---------------- F6 对话经验入库（对话成为长期记忆的一部分） ----------------
    def learn_from_dialog(self, user_text: str, reply: str, intent=None) -> bool:
        """把一轮对话作为「对话经验」写入长期记忆（scene=dialog）。

        内容型记忆：
          1. 对话原文（截断）入库 —— 让「记得聊过什么」成为可检索的真实记忆；
          2. 规则型知识提取 —— 从对话中抽出事实条目（我是谁 / 7Tan 是什么 /
             能力边界），存入知识库（knowledge），供后续直接引用回答。
        只记客观事实，不记隐私细节。
        """
        try:
            topic = (str(user_text or "").strip())[:40] or "?"
            act = f"answer_{intent}" if intent else "answer_unknown"
            # ① 对话原文（放宽截断）入库：内容型记忆的原料
            self.memory.add_trace(
                scene="dialog",
                action=act,
                finished=True,
                changed=False,
                reduced=False,
                gained=True,   # 每次对话都有知识增益
                user_text=(str(user_text or "").strip())[:120],
                reply=(str(reply or "").strip())[:200],
                intent=str(intent or "unknown"),
            )
            # ② 规则型知识提取：从本轮对话中抽出事实，存入知识库
            try:
                facts = self._extract_knowledge(str(user_text or ""), str(reply or ""), intent)
                for key, content in facts.items():
                    self.memory.add_knowledge(key, content, source="dialog", confidence=0.9)
            except Exception as e:
                logger.warning(f"对话知识提取失败（不影响入库）: {e}")
            _log_change(f"对话经验入库: 主题={topic[:20]} 答复方式={act}")
            return True
        except Exception as e:
            logger.warning(f"对话经验入库失败: {e}")
            return False

    def _extract_knowledge(self, user_text: str, reply: str, intent=None) -> dict:
        """规则型事实提取（纯本地，不接外部引擎）。

        只做高置信度的显式模式，避免误提取：
          - 「我叫X / 我是X / 记住我叫X」 → user_name（用户身份）
          - 用户主动纠正能力边界（「你不会X / 你答非所问」） → capability_boundary
          - 「7Tan 是什么」类提问 + 回复要点 → what_is_7tan（模型自我认知）
        """
        facts: dict = {}
        ut = (user_text or "").strip()
        rp = (reply or "").strip()
        # 1) 用户身份：我叫X / 我是X / 记住我叫X / 我（就）是老X
        m = None
        for pat in (r"记住?\s*我\s*(?:叫|是)\s*([\u4e00-\u9fa5A-Za-z0-9_]{1,12})",
                    r"我\s*(?:叫|是)\s*([\u4e00-\u9fa5A-Za-z0-9_]{1,12})"):
            m = m or re.search(pat, ut)
        if m:
            name = m.group(1).strip()
            if name and name not in ("7Tan", "模型", "机器人", "你"):
                facts["user_name"] = f"和我对话的用户叫「{name}」。"
        # 2) 能力边界：用户指出我做不到的事
        for pat in (r"你(?:不会|不懂|没有|缺乏)\s*([\u4e00-\u9fa5A-Za-z0-9_]{2,16})",
                    r"(?:答非所问|答不对题|没(?:有)?思考能力)"):
            if re.search(pat, ut):
                facts["capability_boundary"] = (
                    "我的能力边界：纯本地规则引擎，没有语义理解与真推理；"
                    "用户指出过我会「答非所问/答不对题」，我不会编程、不会写诗。"
                )
                break
        # 3) 自我认知：7Tan 是什么
        if re.search(r"7[_-]?tan|7坛模型|7Tan模型", ut, re.I) and re.search(r"是什么|你是谁|你是什么|介绍一下", ut):
            facts["what_is_7tan"] = (
                "7Tan 模型是本地预测引擎 + 言语系统：基于记忆轨迹做预测推演，"
                "记忆存 SQLite 数据库；能自述、能推演、能诚实说不知道。"
            )
        return facts

    # ---------------- F2-1 注册假设 ----------------
    def register_hypothesis(self, hypothesis_obj) -> Optional[Hypothesis]:
        """注册假设进入 hypothesis_registry，初始化计数器；做基础格式校验。

        防护：拒绝空内容、置信度越界的假设。
        输入可来自E模块 scratch_pad 草稿（dict）或已构造的 Hypothesis。
        """
        if isinstance(hypothesis_obj, Hypothesis):
            hypo = hypothesis_obj
        elif isinstance(hypothesis_obj, dict):
            content = hypothesis_obj.get("content")
            if not isinstance(content, dict) or not content:
                logger.warning("模块F：拒绝注册空内容假设")
                return None
            raw = hypothesis_obj.get("confidence_raw", 0.5)
            try:
                raw = float(raw)
            except (TypeError, ValueError):
                logger.warning(f"模块F：拒绝注册（置信度非法: {raw}）")
                return None
            if raw < 0.0 or raw > 1.0:
                logger.warning(f"模块F：拒绝注册（置信度越界: {raw}）")
                return None
            hid = str(hypothesis_obj.get("hypothesis_id") or f"h{uuid.uuid4().hex[:10]}")
            hypo = Hypothesis(hid, content, str(hypothesis_obj.get("source_trace_id", "")), raw)
        else:
            logger.warning("模块F：拒绝注册（假设对象类型非法）")
            return None

        # 同ID去重
        self.hypothesis_registry = [h for h in self.hypothesis_registry
                                    if h.hypothesis_id != hypo.hypothesis_id]
        self.hypothesis_registry.append(hypo)
        _log_change(f"REGISTER {hypo.hypothesis_id} raw={hypo.confidence_raw} "
                    f"content={json.dumps(hypo.content, ensure_ascii=False)[:200]}")
        logger.info(f"🧪 模块F：假设已注册 {hypo.hypothesis_id}（raw={hypo.confidence_raw}）")
        return hypo

    # ---------------- F2-2 评估假设 ----------------
    def evaluate_hypothesis(self, hypothesis_id: str, observation_feedback) -> Optional[Hypothesis]:
        """输入假设ID + 现实观测反馈（成功/失败、新PE数值），更新计数与状态。

        ① 根据反馈标记本次验证成功/失败，更新 test_count/success_count/fail_count
        ② final_confidence = raw * (1 + (success-fail)/max(test,1))，钳位 [0,1]
        ③ 状态机：test<MIN → suspended；>=PASS → verified；<=REJECT → rejected；否则 suspended
        """
        hypo = self._find(hypothesis_id)
        if hypo is None:
            logger.warning(f"模块F：评估失败，假设不存在 {hypothesis_id}")
            return None

        success = self._interpret_feedback(hypo, observation_feedback)
        hypo.test_count += 1
        if success:
            hypo.success_count += 1
        else:
            hypo.fail_count += 1

        # ② 校正置信度（钳位防溢出）
        corrected = hypo.confidence_raw * (1 + (hypo.success_count - hypo.fail_count) / max(hypo.test_count, 1))
        hypo.final_confidence = round(max(0.0, min(1.0, corrected)), 4)

        # ③ 状态流转
        if hypo.test_count < HYPO_MIN_TESTS:
            hypo.status = "suspended"       # 样本不足，证据不够，暂不处理
        elif hypo.final_confidence >= HYPO_PASS_THRESHOLD:
            hypo.status = "verified"
        elif hypo.final_confidence <= HYPO_REJECT_THRESHOLD:
            hypo.status = "rejected"
        else:
            hypo.status = "suspended"
        hypo.updated_ts = time.time()

        _log_change(f"EVALUATE {hypo.hypothesis_id} feedback={observation_feedback!r} "
                    f"success={success} test={hypo.test_count} s={hypo.success_count} "
                    f"f={hypo.fail_count} final={hypo.final_confidence} → {hypo.status}")
        logger.info(f"🧪 模块F：假设 {hypo.hypothesis_id} 评估 → {hypo.status}"
                    f"（final={hypo.final_confidence}, {hypo.success_count}成/{hypo.fail_count}败）")
        return hypo

    def _interpret_feedback(self, hypo: Hypothesis, observation_feedback) -> bool:
        """解读观测反馈：True=验证成功 False=验证失败（按假设类型区分语义）。

        支持：bool / 数字(>=0.5为成功) / dict（按假设类型解读）。
        dict 约定：
          {"success": bool} 直接采用；
          {"pe": float}：
            · chain 类假设（预测成功率）→ PE < 0.35 = 预测准了 = 验证成功
            · stale_memory_suspect 类（旧经验过时）→ PE >= 0.35 = 证实记忆过时 = 验证成功
          {"actual_success": bool}（现实轨迹结果）：
            · chain 类 → 与假设预测方向一致即成功
            · stale 类 → 现实结果与旧记忆相悖 = 证实过时 = 成功
        """
        if isinstance(observation_feedback, bool):
            return observation_feedback
        if isinstance(observation_feedback, (int, float)):
            return observation_feedback >= 0.5
        if isinstance(observation_feedback, dict):
            is_stale = (hypo.content or {}).get("type") == "stale_memory_suspect"
            if "success" in observation_feedback:
                return bool(observation_feedback["success"])
            if "pe" in observation_feedback:
                pe = float(observation_feedback["pe"])
                return pe >= 0.35 if is_stale else pe < 0.35
            if "actual_success" in observation_feedback:
                actual = bool(observation_feedback["actual_success"])
                if is_stale:
                    old_rate = float(hypo.content.get("old_success_rate", 0.5))
                    # 旧记忆说会败、现实成了（或反之）→ 证实旧记忆过时
                    return actual != (old_rate >= 0.5)
                predicted = hypo.content.get("predicted_success_rate")
                if predicted is None:
                    return actual
                return (float(predicted) >= 0.55) == actual
        return False

    # ---------------- F2-3 落地记忆更新 ----------------
    def apply_memory_update(self, hypo: Hypothesis) -> Optional[dict]:
        """仅当 status == "verified" 才执行。三种更新模式操作模块A记忆库。

        Mode 1 更新已有记忆条目：weight_eff += 0.08 * final_confidence（钳位上限1.0）
        Mode 2 新增记忆条目：全新经验 → weight_eff 初始 = final_confidence，打时间戳
        Mode 3 削弱错误旧记忆：weight_eff -= 0.15 * (1 - final_confidence)，下限0；
               不直接删除热记忆，仅降权；冷记忆交给A模块兜底淘汰机制处理。
        """
        if hypo.status != "verified":
            return None
        content = hypo.content or {}
        mode_result = {"hypothesis_id": hypo.hypothesis_id, "mode": None, "changed": 0}
        # 安全红线：首次落地修改前，先做记忆 .bak 快照（可回退兜底）
        if not getattr(self, "_bak_done", False):
            self.backup_memory()
            self._bak_done = True

        # ── Mode 3：削弱错误旧记忆（假设证明旧记忆错误） ──
        if content.get("type") == "stale_memory_suspect":
            scene = content.get("scene")
            affected = 0
            for t in self.memory.traces:
                if isinstance(t, dict) and str(t.get("scene")) == scene:
                    old_w = float(t.get("weight_eff", 1.0))
                    new_w = max(0.0, old_w - MEMORY_WEAKEN_STRENGTH * (1 - hypo.final_confidence))
                    t["weight_eff"] = round(new_w, 4)
                    affected += 1
            if affected:
                self.memory.save()
                mode_result.update(mode=3, changed=affected)
                _log_change(f"APPLY-MODE3 {hypo.hypothesis_id} weaken scene={scene} "
                            f"traces={affected} strength={MEMORY_WEAKEN_STRENGTH}*(1-{hypo.final_confidence})")
                logger.info(f"🧪 模块F Mode3：削弱场景「{scene}」旧记忆权重（{affected} 条，未删除）")
            return mode_result

        # ── Mode 1：更新已有记忆（假设有来源轨迹 → 加固） ──
        src_id = hypo.source_trace_id
        target = None
        if src_id:
            for t in self.memory.traces:
                if isinstance(t, dict) and str(t.get("trace_id", "")) == str(src_id):
                    target = t
                    break
        if target is not None:
            old_w = float(target.get("weight_eff", 1.0))
            new_w = min(1.0, old_w + MEMORY_BUMP_STRENGTH * hypo.final_confidence)
            target["weight_eff"] = round(new_w, 4)
            target["last_access_ts"] = time.time()
            self.memory.save()
            mode_result.update(mode=1, changed=1)
            _log_change(f"APPLY-MODE1 {hypo.hypothesis_id} bump trace={src_id} "
                        f"weight {old_w} → {new_w}")
            logger.info(f"🧪 模块F Mode1：加固记忆 {src_id} 权重 {old_w} → {new_w}")
            return mode_result

        # ── Mode 2：新增记忆条目（全新经验） ──
        rec = self.memory.add_trace(
            content.get("scene", "unknown_interface"),
            content.get("action", "explore"),
            finished=bool(content.get("finished", False)),
            changed=bool(content.get("changed", False)),
            reduced=bool(content.get("reduced", False)),
            gained=bool(content.get("gained", True)),
        )
        rec["weight_eff"] = round(max(0.0, min(1.0, hypo.final_confidence)), 4)
        rec["created_ts"] = time.time()
        rec["last_access_ts"] = time.time()
        self.memory.save()
        mode_result.update(mode=2, changed=1)
        _log_change(f"APPLY-MODE2 {hypo.hypothesis_id} new-trace scene={content.get('scene')} "
                    f"action={content.get('action')} weight={rec['weight_eff']}")
        logger.info(f"🧪 模块F Mode2：验证通过的猜想固化为新记忆（权重={rec['weight_eff']}）")
        return mode_result

    # ---------------- F2-4 主循环钩子 ----------------
    def f_selflearn_tick(self) -> dict:
        """主循环钩子：每轮调用一次。

        遍历 hypothesis_registry；对有新观测反馈的假设执行 evaluate_hypothesis；
        对 verified 状态执行 apply_memory_update；清理过期 suspended/pending 假设。
        本钩子无条件执行（无开关）。
        """
        evaluated = applied = cleaned = 0
        for hypo in list(self.hypothesis_registry):
            # 1) 消费待处理反馈
            while hypo.feedback_queue:
                fb = hypo.feedback_queue.pop(0)
                self.evaluate_hypothesis(hypo.hypothesis_id, fb)
                evaluated += 1
            # 2) verified → 落地记忆
            if hypo.status == "verified":
                if self.apply_memory_update(hypo):
                    applied += 1
                # verified 已处理完毕，从注册表移除（结论已固化）
                self.hypothesis_registry.remove(hypo)
            # 3) rejected → 直接丢弃，不写入长期记忆库
            elif hypo.status == "rejected":
                self.hypothesis_registry.remove(hypo)
                _log_change(f"DISCARD {hypo.hypothesis_id} rejected（不写入长期记忆）")
                cleaned += 1
            # 4) 过期 suspended/pending 清理（超过 1 小时且无新反馈）
            elif hypo.status in ("pending", "suspended"):
                if time.time() - hypo.updated_ts > 3600 and not hypo.feedback_queue:
                    self.hypothesis_registry.remove(hypo)
                    _log_change(f"EXPIRE {hypo.hypothesis_id} {hypo.status}（超时清理，会话草稿销毁）")
                    cleaned += 1
        if evaluated or applied or cleaned:
            logger.info(f"🧪 模块F tick：评估{evaluated} 落地{applied} 清理{cleaned} "
                        f"（注册表剩余{len(self.hypothesis_registry)}）")
        return {"enabled": True, "evaluated": evaluated,
                "applied": applied, "cleaned": cleaned}

    # ---------------- 辅助 ----------------
    def _find(self, hypothesis_id: str) -> Optional[Hypothesis]:
        for h in self.hypothesis_registry:
            if h.hypothesis_id == hypothesis_id:
                return h
        return None

    def submit_feedback(self, hypothesis_id: str, observation_feedback) -> bool:
        """把一条观测反馈排入假设的待处理队列（由 f_selflearn_tick 消费）。"""
        hypo = self._find(hypothesis_id)
        if hypo is None:
            return False
        hypo.feedback_queue.append(observation_feedback)
        return True

    def status_report(self) -> list:
        """对外输出：当前假设、验证次数、置信度（SpeechGenerator 开关开启时可读）。"""
        return [h.to_dict() for h in self.hypothesis_registry]

    # ---------------- 记忆bak回退兜底（第四册F5第5条 / 清单第16项） ----------------
    def backup_memory(self) -> Optional[Path]:
        """对模块A记忆文件做 .bak 快照（F 首次修改记忆前自动调用）。"""
        try:
            src_path = self.memory.path
            if src_path.exists():
                bak = src_path.with_suffix(src_path.suffix + ".bak")
                bak.write_bytes(src_path.read_bytes())
                _log_change(f"BACKUP memory → {bak.name}")
                logger.info(f"🧪 模块F：记忆库已备份 → {bak.name}")
                return bak
        except Exception as e:
            logger.warning(f"记忆备份失败（不影响学习）: {e}")
        return None

    def rollback_memory(self) -> bool:
        """从 .bak 快照回退记忆库（世界模型置信度持续恶化时的最后防线）。"""
        try:
            src_path = self.memory.path
            bak = src_path.with_suffix(src_path.suffix + ".bak")
            if not bak.exists():
                logger.warning("记忆回退失败：无 .bak 快照")
                return False
            src_path.write_bytes(bak.read_bytes())
            self.memory.load()  # 重新加载回退后的记忆
            _log_change("ROLLBACK memory from .bak")
            logger.info("🧪 模块F：记忆库已从 .bak 快照回退")
            return True
        except Exception as e:
            logger.warning(f"记忆回退异常: {e}")
            return False

    def confidence_health(self, window: int = 4) -> dict:
        """世界模型置信度健康监测：最近 window 次 PE 是否持续上升（恶化）。

        返回 {"trend": "improving|stable|worsening|unknown", "pe_recent": [...]}
        worsening 时建议触发记忆bak回退（由上层/D模块兜底决定）。
        """
        pe = self.memory.pe_history
        if len(pe) < 2:
            return {"trend": "unknown", "pe_recent": pe[-window:]}
        recent = pe[-window:]
        rising = all(recent[i + 1] > recent[i] for i in range(len(recent) - 1))
        falling = all(recent[i + 1] < recent[i] for i in range(len(recent) - 1))
        trend = "worsening" if rising else ("improving" if falling else "stable")
        return {"trend": trend, "pe_recent": recent}
