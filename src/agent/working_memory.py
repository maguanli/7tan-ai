# -*- coding: utf-8 -*-
"""
模块E：工作记忆 + 有限思考层（Working Memory & Limited Thinking Layer）

来源：智能生命项目 · 第四册设计稿（模块E完整设计）。
定位：短时思考工作台，和模块A长期记忆库（TanModelMemory）严格区分。
  - 工作记忆 = 会话内易失缓冲区：思考中间片段、活跃目标、草稿假设。
  - 会话结束草稿丢弃；仅经过校验的结论才允许写入模块A长期记忆。
  - 默认读取模块A【热记忆】；冷记忆不自动进入，必须显式检索调入。

三层思考子能力（搭建在工作记忆之上）：
  思考层1 链式推演：热记忆事实 → 假设链 → 推演结果回栈作为下一步输入，最大步数强制停止。
  思考层2 目标拆解 decompose_goals()：把B模块动机/用户目标拆解为子目标写入 active_goals。
  思考层3 反思桥接：PE/LP 送入工作记忆；PE 持续偏高 → scratch_pad 生成猜想 → 转待验证子目标。

⚠️ 边界：E 只负责「生成猜想与待验证目标」，不自动修改策略；
   完整自我学习闭环（评估+落地记忆）由模块F（self_learn.py）实现。

模块E 无条件启用，无需开关。
本模块自包含（仅依赖标准库 + loguru）。
"""
from __future__ import annotations

import re
import time
import uuid
from typing import Optional

from loguru import logger

# ═══════════════ 容量保护参数 ═══════════════
WM_STACK_MAX = 10               # context_stack 最大步数（设计稿建议 8-12，取 10）
WM_FOCUS_DEFAULT = 0.5          # 默认注意力权重 0-1
WM_HOT_WEIGHT_MIN = 0.5         # 热记忆判定阈值：weight_eff >= 此值才算热记忆


class WorkingMemory:
    """工作记忆：会话内易失缓冲区（E1 核心数据结构）"""

    def __init__(self, stack_max: int = WM_STACK_MAX):
        self.context_stack: list = []        # 思考步骤栈，保存链式推演片段
        self.active_goals: list = []         # 当前激活目标（B模块动机 / 用户指令）
        self.intermediate_pe_lp: dict = {}   # 会话临时 PE、LP 中间计算结果
        self.focus_weight: float = WM_FOCUS_DEFAULT  # 注意力权重 0-1
        self.scratch_pad: dict = {}          # 草稿区：未验证假设、猜想、待测试思路
        self.stack_max = max(1, int(stack_max))
        self.created_ts = time.time()
        # ── 对话上下文槽位（读上下文 + 记住用户，跨消息存活，进程内） ──
        self.dialog_slots: dict = {
            "user_name": None,       # 用户自称/被称呼的名字（如 老马）
            "topic": None,           # 当前话题
            "recent_events": [],     # 最近事件链 [{role, content, ts}]
            "turn_count": 0,         # 累计对话轮数
        }
        self.dialog_events_max = 20

    # ---------------- E2 对外接口 ----------------
    def wm_push_thought(self, thought_fragment: dict, focus: Optional[float] = None) -> bool:
        """将一条思考片段压入思考栈，附带注意力权重。

        容量保护：超过 stack_max 自动丢弃最早的思考片段，防止内存无限膨胀。
        """
        if not isinstance(thought_fragment, dict) or not thought_fragment:
            return False
        f = self.focus_weight if focus is None else max(0.0, min(1.0, float(focus)))
        item = {
            "thought_id": uuid.uuid4().hex[:12],
            "fragment": thought_fragment,
            "focus": f,
            "ts": time.time(),
        }
        self.context_stack.append(item)
        while len(self.context_stack) > self.stack_max:
            dropped = self.context_stack.pop(0)
            logger.debug(f"🧠 工作记忆栈溢出，丢弃最早片段: {dropped['thought_id']}")
        return True

    def wm_pop_thought(self) -> Optional[dict]:
        """弹出最近思考片段，支持思考回溯撤销。"""
        if not self.context_stack:
            return None
        return self.context_stack.pop()

    def wm_set_active_goal(self, motive_obj) -> bool:
        """接收B模块输出的动机对象 / 用户外部目标，置入 active_goals。"""
        if not isinstance(motive_obj, dict) or not motive_obj.get("goal"):
            return False
        goal = {
            "goal": str(motive_obj["goal"]),
            "source": str(motive_obj.get("source", "user")),   # motive(B模块) / user(用户)
            "priority": float(motive_obj.get("priority", 0.5)),
            "sub_goals": list(motive_obj.get("sub_goals", [])),
            "ts": time.time(),
        }
        # 同名目标去重（保留新的）
        self.active_goals = [g for g in self.active_goals if g["goal"] != goal["goal"]]
        self.active_goals.append(goal)
        # 活跃目标同样有容量保护（最多 8 个，优先级低的先淘汰）
        self.active_goals.sort(key=lambda g: -g["priority"])
        del self.active_goals[8:]
        return True

    def wm_focus_filter(self, items: Optional[list] = None) -> list:
        """根据 focus_weight 过滤内容，模拟注意力筛选。

        不传 items 时过滤 context_stack；传入时按每项的 focus 字段过滤。
        只保留 focus >= focus_weight 的内容（按 focus 降序）。
        """
        src = items if items is not None else self.context_stack
        kept = [x for x in src if float(x.get("focus", 0.0)) >= self.focus_weight]
        kept.sort(key=lambda x: -float(x.get("focus", 0.0)))
        return kept

    def wm_persist_to_longterm(self, memory) -> int:
        """将工作记忆中验证完成的结论回写到模块A长期记忆；草稿不保存。

        只固化 scratch_pad 中 status=verified 的结论（由模块F评估通过）。
        返回固化条数。草稿（pending/suspended/rejected）一律不写。
        """
        persisted = 0
        for k, draft in list(self.scratch_pad.items()):
            if not isinstance(draft, dict):
                continue
            if draft.get("status") != "verified":
                continue  # 草稿不保存 —— 只有验证过的结论才允许写入长期记忆
            try:
                content = draft.get("content") or {}
                memory.add_trace(
                    content.get("scene", "unknown_interface"),
                    content.get("action", "explore"),
                    finished=bool(content.get("finished", False)),
                    changed=bool(content.get("changed", False)),
                    reduced=bool(content.get("reduced", False)),
                    gained=bool(content.get("gained", True)),
                )
                # 固化后从草稿区移除（已落地长期记忆）
                del self.scratch_pad[k]
                persisted += 1
                logger.info(f"🧠 工作记忆 → 长期记忆固化: {k}")
            except Exception as e:
                logger.warning(f"工作记忆固化失败（跳过）: {e}")
        return persisted

    # ---------------- 对话上下文槽位（E1.5 读上下文 + 用户记忆） ----------------
    def wm_observe_dialog(self, role: str, content: str) -> None:
        """记录一轮对话到事件链（容量保护：只保留最近 N 轮）。"""
        if not content or not str(content).strip():
            return
        self.dialog_slots["recent_events"].append({
            "role": "user" if str(role) == "user" else "assistant",
            "content": str(content).strip()[:200],
            "ts": time.time(),
        })
        self.dialog_slots["turn_count"] += 1
        while len(self.dialog_slots["recent_events"]) > self.dialog_events_max:
            self.dialog_slots["recent_events"].pop(0)

    def wm_remember_user_name(self, name: str) -> bool:
        """记住用户名字（去重）。"""
        name = (name or "").strip()
        if not name or len(name) > 12:
            return False
        if self.dialog_slots["user_name"] == name:
            return True
        self.dialog_slots["user_name"] = name
        logger.info(f"🧠 工作记忆记住用户名字: {name}")
        return True

    def wm_extract_user_name(self, text: str) -> Optional[str]:
        """从文本中提取用户自称/被称呼的名字。

        识别模式：
          「我叫老马」「我是老马」「叫我老马」「名字叫老马」「可以叫我老马」
          「老马」（单句自称短词）
        返回 None 表示没提取到。
        """
        if not text:
            return None
        t = str(text).strip()
        patterns = [
            r"(?:我叫|我是|叫我|名字叫|名叫|可以叫我|就叫我|喊我|我的名字是|我的称呼是|你就叫(?:我)?)\s*([\u4e00-\u9fa5A-Za-z0-9_·]{1,12})",
            r"^([\u4e00-\u9fa5]{1,3}哥|[" + "\u4e00-\u9fa5" + "]{1,3}姐|老[\u4e00-\u9fa5]{1,3}|小[\u4e00-\u9fa5]{1,3}[\u4e00-\u9fa5]{0,2})[，,。!！?？]?$",
        ]
        for p in patterns:
            m = re.search(p, t)
            if m:
                name = m.group(1).strip()
                name = re.sub(r"[的了是吗啊呢吧，。！？,.!?]$", "", name)
                if name and len(name) <= 12 and not name.isdigit():
                    return name
        return None

    def wm_update_topic(self, text: str) -> None:
        """根据用户输入更新当前话题槽位（简单话题跟踪）。"""
        if not text or not str(text).strip():
            return
        t = str(text).strip()
        m = re.search(r"(?:我们在聊|刚才在聊|在聊|关于|讨论|话题是)\s*([\u4e00-\u9fa5A-Za-z0-9_·]{1,20})", t)
        if m:
            topic = m.group(1).strip()
            # 显式匹配也要排除疑问词（「我们在聊什么」的「什么」不是话题）
            if not any(q in topic for q in ("吗", "什么", "怎么", "为什么", "哪", "如何")):
                self.dialog_slots["topic"] = topic
            return
        if not self.dialog_slots["topic"]:
            # 疑问句不当话题（「我们在聊什么」的「什么」不是话题）
            if any(q in t for q in ("吗", "什么", "怎么", "为什么", "多少", "几",
                                    "哪", "能不能", "如何", "？", "?")):
                return
            clean = re.sub(r"[\s?？!！。.，,、：:；;]+", "", t)[:12]
            if clean:
                self.dialog_slots["topic"] = clean

    def wm_dialog_summary(self) -> str:
        """生成对话上下文摘要（供言语层引用）。"""
        slots = self.dialog_slots
        parts = []
        if slots["user_name"]:
            parts.append(f"正在和我对话的人自称「{slots['user_name']}」")
        if slots["topic"]:
            parts.append(f"当前话题：{slots['topic']}")
        if slots["recent_events"]:
            last = slots["recent_events"][-1]
            who = "你" if last["role"] == "user" else "我"
            parts.append(f"上一轮：{who}说「{last['content'][:60]}」")
        return "；".join(parts) if parts else "（无）"

    # ---------------- 生命周期 ----------------
    def reset(self):
        """会话结束：草稿全部销毁、思考栈清空、目标清空（易失性）。"""
        n_draft = len(self.scratch_pad)
        self.context_stack = []
        self.active_goals = []
        self.intermediate_pe_lp = {}
        self.scratch_pad = {}
        self.focus_weight = WM_FOCUS_DEFAULT
        if n_draft:
            logger.info(f"🧠 会话结束，工作记忆草稿已销毁（{n_draft} 条未验证猜想丢弃）")

    def snapshot(self) -> dict:
        """导出调试快照（*.workingmem.json 用）。"""
        return {
            "context_stack": [
                {"thought_id": t["thought_id"], "focus": t["focus"],
                 "fragment": t["fragment"], "ts": t["ts"]}
                for t in self.context_stack
            ],
            "active_goals": self.active_goals,
            "intermediate_pe_lp": self.intermediate_pe_lp,
            "focus_weight": self.focus_weight,
            "scratch_pad": self.scratch_pad,
            "stack_max": self.stack_max,
            "created_ts": self.created_ts,
        }

    # ---------------- 草稿区辅助 ----------------
    def draft_hypothesis(self, content: dict, confidence_raw: float,
                         source_trace_id: str = "", kind: str = "chain") -> Optional[dict]:
        """在 scratch_pad 生成一条假设草稿（未验证，status=pending）。

        注意：这里只生成草稿；注册进模块F、评估、落地由 SelfLearnEngine 负责。
        """
        if not isinstance(content, dict) or not content:
            return None
        c = max(0.0, min(1.0, float(confidence_raw)))
        hid = f"h{uuid.uuid4().hex[:10]}"
        draft = {
            "hypothesis_id": hid,
            "content": content,
            "source_trace_id": source_trace_id,
            "confidence_raw": c,
            "kind": kind,             # chain(链式推演) / reflect(反思桥接) / user(用户)
            "status": "pending",      # pending → suspended/verified/rejected（模块F流转）
            "created_ts": time.time(),
        }
        self.scratch_pad[hid] = draft
        # 草稿区容量保护：最多 12 条，最旧的 pending 先丢弃
        if len(self.scratch_pad) > 12:
            for k in list(self.scratch_pad.keys())[:-12]:
                if self.scratch_pad[k].get("status") in ("pending", "suspended"):
                    del self.scratch_pad[k]
                    break
        return draft


class ThinkingLayer:
    """三层思考子能力（E3），搭建在 WorkingMemory 之上。

    只生成猜想与待验证目标，不自动修改策略（那是模块F的职责）。
    """

    def __init__(self, model, wm: WorkingMemory):
        self.model = model          # TanModel（提供 memory / virtual_predict）
        self.wm = wm

    # ---------------- 思考层1：链式推演 ----------------
    def chain_reason(self, scene: str, action: str, max_steps: int = 3) -> dict:
        """链式推演：A→B，B→C ⇒ 推导 A→C。

        流程（设计稿E3思考层1）：
          1. 从热记忆提取相关事实压入 context_stack
          2. scratch_pad 生成推演假设链
          3. 推演结果放回工作记忆栈作为下一步输入
          4. 达到最大推理步数强制停止，防止无限推演

        推演算法（基于记忆条目的场景/结果关联）：
          步骤1 同场景归纳：场景S中动作A的历史成功率 c1
          步骤2 跨场景迁移：动作A在其它场景的成功率 c2（同动作泛化）
          步骤3 综合结论：c = w1*c1 + w2*c2（有同场景经验时以本场景为主）
        """
        mem = self.model.memory
        steps = []
        # ── 步骤1：同场景事实（热记忆优先） ──
        similar = [t for t in mem.find_similar(scene)
                   if float(t.get("weight_eff", 1.0)) >= WM_HOT_WEIGHT_MIN] \
                  or mem.find_similar(scene)
        c1 = None
        if similar:
            succ = sum(1 for t in similar if t.get("action_finished"))
            c1 = round(succ / len(similar), 4)
            fact1 = {"step": 1, "kind": "same_scene",
                     "fact": f"场景{scene}中动作{action}历史成功率={c1}（{len(similar)}条轨迹）",
                     "value": c1}
            self.wm.wm_push_thought(fact1, focus=0.9)
            steps.append(fact1)

        # ── 步骤2：跨场景迁移（同动作在其它场景的表现） ──
        c2 = None
        others = [t for t in mem.traces
                  if isinstance(t, dict) and t.get("action") == action
                  and str(t.get("scene")) != scene]
        if others:
            succ2 = sum(1 for t in others if t.get("action_finished"))
            c2 = round(succ2 / len(others), 4)
            fact2 = {"step": 2, "kind": "cross_scene",
                     "fact": f"动作{action}在其它场景成功率={c2}（{len(others)}条轨迹）→ 迁移参考",
                     "value": c2}
            self.wm.wm_push_thought(fact2, focus=0.6)
            steps.append(fact2)

        # ── 步骤3：综合推演结论（结果回栈，作为下一步输入） ──
        if c1 is not None and c2 is not None:
            w1, w2 = 0.7, 0.3
            c_final = round(w1 * c1 + w2 * c2, 4)
            basis = "同场景为主+跨场景迁移修正"
        elif c1 is not None:
            c_final = c1
            basis = "仅有同场景经验"
        elif c2 is not None:
            c_final = round(c2 * 0.6, 4)  # 只有迁移经验 → 打折
            basis = "仅跨场景迁移（无本场景经验，置信度打折）"
        else:
            c_final = None
            basis = "无任何相关经验（知识缺口）"

        conclusion = {"step": 3, "kind": "conclusion",
                      "fact": f"综合推演：场景{scene}+动作{action} 成功率≈{c_final}（{basis}）",
                      "value": c_final}
        self.wm.wm_push_thought(conclusion, focus=1.0)
        steps.append(conclusion)

        # ── 假设链写入草稿区（未验证） ──
        draft = None
        if c_final is not None:
            draft = self.wm.draft_hypothesis(
                content={"scene": scene, "action": action,
                         "predicted_success_rate": c_final, "basis": basis},
                confidence_raw=c_final,
                kind="chain",
            )

        # 达到最大步数强制停止（steps 长度天然 <= 3，这里显式守卫）
        stopped_by_limit = len(steps) >= max_steps

        return {
            "scene": scene, "action": action,
            "steps": steps,
            "conclusion": c_final,
            "basis": basis,
            "hypothesis_id": draft["hypothesis_id"] if draft else None,
            "stopped_by_limit": stopped_by_limit,
        }

    # ---------------- 思考层2：目标拆解 ----------------
    def decompose_goals(self, motive_obj: dict) -> list:
        """把B模块动机 / 用户目标拆解为子目标，写入 active_goals。

        示例（设计稿）：B模块检测高LP → 内生动机「该领域预测误差高，需要探索学习」
          子目标1：检索相关历史热记忆
          子目标2：生成待验证假设存入草稿区
          子目标3：生成可用于检验假设的动作/查询
        """
        goal_text = str(motive_obj.get("goal", ""))
        source = str(motive_obj.get("source", "user"))
        sub_goals = []

        if "探索" in goal_text or "学习" in goal_text or source == "motive":
            sub_goals = [
                {"sub": "检索相关历史热记忆", "done": False},
                {"sub": "生成待验证假设存入草稿区", "done": False},
                {"sub": "生成可用于检验假设的动作/查询", "done": False},
            ]
        elif "预测" in goal_text:
            sub_goals = [
                {"sub": "提取场景相关热记忆事实", "done": False},
                {"sub": "链式推演生成结论", "done": False},
                {"sub": "等待现实观测以校验预测", "done": False},
            ]
        else:
            sub_goals = [{"sub": f"处理目标：{goal_text[:40]}", "done": False}]

        motive_obj = dict(motive_obj)
        motive_obj["sub_goals"] = sub_goals
        self.wm.wm_set_active_goal(motive_obj)
        return sub_goals

    # ---------------- 思考层3：反思桥接 ----------------
    def reflect_bridge(self, pe: float, lp: float) -> Optional[dict]:
        """把PE/LP送入工作记忆；PE持续偏高 → scratch_pad生成猜想 → 转待验证子目标。

        返回生成的猜想草稿（可能为 None：PE 不高就不猜）。
        ⚠️ 只生成猜想，不修改策略 —— 评估与落地由模块F完成。
        """
        self.wm.intermediate_pe_lp = {"pe": pe, "lp": lp, "ts": time.time()}
        if pe < 0.4:
            return None  # 误差不高，无需反思猜想
        # PE 持续偏高 → 生成「哪里原有假设可能出错」的猜想
        traces = self.model.memory.traces
        worst_scene, worst_rate, worst_n = None, 1.0, 0
        scenes: dict = {}
        for t in traces:
            s = str(t.get("scene", "?"))
            scenes.setdefault(s, [0, 0])
            scenes[s][1] += 1
            if t.get("action_finished"):
                scenes[s][0] += 1
        for s, (succ, n) in scenes.items():
            rate = succ / n if n else 1.0
            if rate < worst_rate:
                worst_scene, worst_rate, worst_n = s, rate, n
        if worst_scene is None:
            return None
        guess = (f"预测误差偏高(PE={pe})，猜想：场景「{worst_scene}」的旧经验"
                 f"（成功率{round(worst_rate, 2)}，{worst_n}条）可能已过时或以偏概全，需要重新验证")
        draft = self.wm.draft_hypothesis(
            content={"type": "stale_memory_suspect", "scene": worst_scene,
                     "old_success_rate": round(worst_rate, 4), "trace_count": worst_n,
                     "guess": guess},
            confidence_raw=round(1.0 - worst_rate, 4),
            kind="reflect",
        )
        # 猜想转为待验证子目标
        self.wm.wm_set_active_goal({
            "goal": f"验证猜想：{worst_scene} 旧经验是否过时",
            "source": "motive",
            "priority": 0.8,
        })
        logger.info(f"🧠 反思桥接：PE={pe} 偏高 → 生成猜想草稿 {draft['hypothesis_id'] if draft else ''}")
        return draft
