"""
7Tan 模型（TanModel）— 本地预测引擎 + 言语功能系统

来源：智能生命项目的 WorldSimulationUnit（预测误差驱动内生动机的核心组件）。
能力：
  1) 预测引擎 —— 给定「场景 + 动作」，基于历史决策轨迹预测执行结果：
     置信度、预期是否成功、知识缺口、4 维预测特征向量、学习进度(LP)。
  2) 言语功能系统（SpeechGenerator）—— 把内部状态（感知/记忆/预测/动机/情绪/
     反思/元认知）翻译成自然语言「自述」，让 7Tan 模型能用自己的话开口说话。

本模块自包含（仅依赖标准库 + loguru），记忆持久化到 data/tan_model_memory.json。
接入 AI 工作台后，用户在「当前模型」下拉框选中「7Tan模型」即可对话测试。

对话用法：
  - 预测推演：「游戏菜单里点击」「场景=游戏菜单 动作=点击」
  - 自述对话：「你是谁」「你什么感觉」「你记得什么」「你觉得会怎样」
  - 「记录 场景=xx 动作=yy 结果=成功/失败」→ 手动标注一次真实结果（喂给模型学习）
  - 「记忆」查看记忆库状态；「清空」重置记忆；「帮助」查看本说明
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Optional

from loguru import logger

# 7Tan 模型的唯一标识（对应数据库 ai_configs 表 config_key 与 model 字段）
T7_MODEL_NAME = "7tan-model"
T7_MODEL_DISPLAY = "7Tan模型"

_MEMORY_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "tan_model_memory.json"
_OLD_MEMORY_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "world_model_memory.json"

# ═══ 模块E/F 全局开关（第四册 · 统一全局配置区；默认关闭，支持A/B对照实验） ═══
try:
    from .working_memory import ENABLE_WORKING_MEMORY          # 模块E：工作记忆+有限思考层
    from .self_learn import ENABLE_L1_MEMORY_SELF_LEARN        # 模块F：L1记忆级自我学习闭环
except Exception:  # 独立加载/打包环境兜底：开关视为关闭，行为与旧版完全一致
    ENABLE_WORKING_MEMORY = False
    ENABLE_L1_MEMORY_SELF_LEARN = False

# 场景关键词 → 归一化场景标签（用于自由文本输入）
SCENE_KEYWORDS = [
    ("unknown_interface", ["未知", "unknown", "空白", "桌面", "desktop"]),
    ("game_menu", ["菜单", "menu"]),
    ("main_interface", ["主界面", "首页", "界面", "interface"]),
]
# 动作关键词 → 动作名（顺序即优先级）
ACTION_KEYWORDS = [
    ("scroll", ["滚动", "下滑", "翻页", "scroll"]),
    ("click", ["点击", "单击", "双击", "click"]),
    ("learn", ["学习", "learn"]),
    ("repair", ["修复", "repair", "优化"]),
    ("maintain", ["维持", "存续", "保持", "maintain"]),
    ("explore", ["探索", "explore", "查看", "浏览"]),
]
DEFAULT_SCENE = "unknown_interface"
DEFAULT_ACTION = "explore"


def is_7tan_model(model_name: str) -> bool:
    """判断模型名是否指向本地 7Tan 模型"""
    m = (model_name or "").strip().lower()
    return m in ("7tan模型", "7tan", "7tan-model", "7tan_model", "7tanmodel", "tan-model",
                 "world-model", "world_model", "worldmodel", "世界模型")


# 兼容旧引用（防止遗漏调用点）
def is_world_model(model_name: str) -> bool:
    return is_7tan_model(model_name)


def ensure_7tan_model_config() -> bool:
    """确保数据库中存在「7Tan模型」配置项（供模型下拉框显示）。

    不抢当前激活模型（is_active=0），仅注册一条本地模型配置。
    若存在旧的「world-model」标识配置，会顺带清理，避免下拉框出现两个重复项。
    """
    try:
        from ..database.db import get_ai_config_by_key, save_ai_config, delete_ai_config
        # 清理旧标识配置（一次性迁移）
        try:
            if get_ai_config_by_key("world-model"):
                delete_ai_config("world-model")
                logger.info("🗑️ 已清理旧标识配置: world-model → 7tan-model")
        except Exception:
            pass
        if get_ai_config_by_key(T7_MODEL_NAME):
            return True
        save_ai_config(
            config_key=T7_MODEL_NAME,
            provider="local_7tan_model",
            model=T7_MODEL_DISPLAY,
            base_url="",
            api_key="",
            context_window=128000,
            max_tokens=16384,
            temperature=0.25,
            is_active=0,
            extra_config={"local": True, "desc": "本地 7Tan 模型预测引擎 + 言语系统"},
        )
        logger.info(f"✅ 已注册 7Tan 模型配置: {T7_MODEL_NAME}")
        return True
    except Exception as e:
        logger.warning(f"注册 7Tan 模型配置失败: {e}")
        return False


# 兼容旧引用
def ensure_world_model_config() -> bool:
    return ensure_7tan_model_config()


class TanModelMemory:
    """7Tan 模型的记忆库：决策轨迹 + 预测误差历史（持久化 JSON）"""

    def __init__(self, path: Optional[Path] = None):
        self.path = path or _MEMORY_PATH
        self.traces: list = []      # 决策轨迹
        self.pe_history: list = []  # 预测误差历史
        self.load()

    def load(self):
        # 旧记忆文件迁移：新路径不存在但旧路径存在时，从旧文件读取
        src = self.path
        migrated = False
        try:
            if not self.path.exists() and _OLD_MEMORY_PATH.exists():
                src = _OLD_MEMORY_PATH
                migrated = True
        except Exception:
            src = self.path

        try:
            if src.exists():
                raw = json.loads(src.read_text(encoding="utf-8"))
                self.traces = raw.get("traces") or []
                self.pe_history = raw.get("pe_history") or []
                if not self.traces:
                    self._seed_demo_traces()
            else:
                self._seed_demo_traces()
            if migrated or not self.path.exists():
                self.save()
        except Exception as e:
            logger.warning(f"7Tan 模型记忆加载失败，使用空库: {e}")
            self.traces = []
            self.pe_history = []

    def save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"traces": self.traces, "pe_history": self.pe_history}
            self.path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"7Tan 模型记忆保存失败: {e}")

    def _seed_demo_traces(self):
        """首次启动预置示例轨迹，让预测立即可用（模拟已有经验）"""
        base = time.time()
        demo = [
            ("unknown_interface", "scroll", True, True, False, True),
            ("unknown_interface", "scroll", True, False, False, True),
            ("unknown_interface", "click", False, False, False, False),
            ("game_menu", "scroll", True, True, False, False),
            ("game_menu", "click", True, False, True, True),
        ]
        self.traces = []
        for i, (scene, action, finished, changed, reduced, gained) in enumerate(demo):
            self.traces.append({
                "scene": scene, "action": action,
                "action_finished": finished, "scene_changed": changed,
                "defect_reduced": reduced, "knowledge_gained": gained,
                "weight_eff": 1.0, "ts": base - len(demo) + i,
            })

    def add_trace(self, scene, action, finished=True, changed=False,
                  reduced=False, gained=False) -> dict:
        rec = {
            "scene": scene, "action": action,
            "action_finished": bool(finished), "scene_changed": bool(changed),
            "defect_reduced": bool(reduced), "knowledge_gained": bool(gained),
            "weight_eff": 1.0, "ts": time.time(),
        }
        self.traces.append(rec)
        self.save()
        return rec

    def find_similar(self, scene) -> list:
        return [t for t in self.traces if isinstance(t, dict) and str(t.get("scene")) == scene]

    def clear(self):
        self.traces = []
        self.pe_history = []
        self.save()


class TanModel:
    """7Tan 模型预测引擎 — 移植自智能生命 WorldSimulationUnit"""

    def __init__(self, memory: Optional[TanModelMemory] = None):
        self.memory = memory or TanModelMemory()
        self.speech = SpeechGenerator(self)
        # ── 模块E/F（第四册）：开关默认关闭，关闭时与原行为完全一致 ──
        self.wm = None                       # 模块E：工作记忆
        self.thinking = None                 # 模块E：三层思考
        self.selflearn = None                # 模块F：自我学习闭环引擎
        self._last_predictions: dict = {}    # {(scene,action): feat} 供闭环计算PE
        self._last_record: Optional[dict] = None  # 最近一条真实标注轨迹（闭环观测用）
        if ENABLE_WORKING_MEMORY:
            try:
                from .working_memory import WorkingMemory, ThinkingLayer
                self.wm = WorkingMemory()
                self.thinking = ThinkingLayer(self, self.wm)
                logger.info("🧠 模块E 已启用：工作记忆 + 有限思考层")
            except Exception as e:
                logger.warning(f"模块E 初始化失败（退回原行为）: {e}")
                self.wm = self.thinking = None
        if ENABLE_L1_MEMORY_SELF_LEARN:
            try:
                from .self_learn import SelfLearnEngine
                self.selflearn = SelfLearnEngine(self.memory)
                logger.info("🧪 模块F 已启用：L1记忆级自我学习闭环")
            except Exception as e:
                logger.warning(f"模块F 初始化失败（退回原行为）: {e}")
                self.selflearn = None

    # ---------------- 预测核心（忠实移植） ----------------
    def virtual_predict(self, scene, action) -> dict:
        """单步推演：基于历史相似轨迹的加权成功率 → 置信度/预期结果/知识缺口"""
        similar = self.memory.find_similar(scene)
        result = {
            "scene": scene, "action": action,
            "similar_count": len(similar),
            "confidence": 0.0,
            "expected_success": False,
            "knowledge_gap": False,
        }
        total_w = 0.0
        succ_w = 0.0
        for item in similar:
            w = float(item.get("weight_eff", 1.0))
            if item.get("action_finished"):
                succ_w += w
            total_w += w
        if total_w > 0:
            result["confidence"] = round(succ_w / total_w, 4)
            result["expected_success"] = result["confidence"] > 0.55
        else:
            result["knowledge_gap"] = True  # 无过往经验 → 认知缺口
        return result

    def predict_outcome(self, scene, action):
        """统计 4 维预测特征向量（0~1）。无经验 → (None, True)。"""
        similar = self.memory.find_similar(scene)
        if not similar:
            return None, True
        n = len(similar)
        feat = [
            round(sum(1 for s in similar if s.get("action_finished")) / n, 4),
            round(sum(1 for s in similar if s.get("scene_changed")) / n, 4),
            round(sum(1 for s in similar if s.get("defect_reduced")) / n, 4),
            round(sum(1 for s in similar if s.get("knowledge_gained")) / n, 4),
        ]
        return feat, False

    @staticmethod
    def compute_pe(predict, actual):
        """预测误差 PE = 均值绝对差 ∈ [0,1]；无预测能力 → 1.0"""
        if predict is None or actual is None or len(predict) != len(actual):
            return 1.0
        return round(sum(abs(p - a) for p, a in zip(predict, actual)) / len(predict), 4)

    @staticmethod
    def compute_lp(pe_now, pe_prev):
        """学习进度 LP = PE(t-1) - PE(t)；正值 = 误差下降 = 正在学会"""
        return round(pe_prev - pe_now, 4)

    # ---------------- 对话接口 ----------------
    def respond(self, user_text: str) -> str:
        """对话入口。末尾挂模块F主循环钩子 f_selflearn_tick（每轮调用一次；
        开关 ENABLE_L1_MEMORY_SELF_LEARN=False 时钩子内部直接 return，零开销）。"""
        reply = self._respond_impl(user_text)
        if self.selflearn is not None:
            try:
                self.selflearn.f_selflearn_tick()
            except Exception as e:
                logger.warning(f"模块F tick 异常（忽略，不影响回复）: {e}")
        return reply

    def _respond_impl(self, user_text: str) -> str:
        text = (user_text or "").strip()
        logger.info(f"🌍 7Tan模型 · 收到输入: {text[:80]}")
        if not text:
            return self._usage()
        low = text.lower()
        # 1) 精确指令优先
        if low in ("help", "帮助", "?", "？", "用法"):
            logger.info("🌍 7Tan模型 → 返回用法说明")
            return self._usage()
        if low in ("memory", "记忆", "状态", "status"):
            logger.info("🌍 7Tan模型 → 返回记忆库状态")
            return self._report_memory()
        if low.startswith(("清空", "clear", "重置", "reset")):
            self.memory.clear()
            if self.wm is not None:
                self.wm.reset()  # 会话重置：工作记忆草稿全部销毁（易失性）
            logger.info("🌍 7Tan模型 → 记忆库已清空")
            return "🧹 记忆库已清空。可重新输入场景+动作开始测试。"
        if low.startswith(("记录", "record", "标注")):
            reply = self._handle_record(text)
            logger.info("🌍 7Tan模型 → 已记录真实轨迹（学习）")
            if self.selflearn is not None:
                extra = self._selflearn_after_record()
                if extra:
                    reply = reply + "\n" + extra
            return reply
        # 2) 言语层（自述类问题）
        speech = self.speech.respond(text)
        if speech is not None:
            logger.info(f"🌍 7Tan模型 → 言语自述（意图={self.speech._last_intent}）")
            return speech
        # 3) 疑问句兜底：是问题但没识别出意图 → 引导，而不是盲目推演
        if self._is_question(text):
            logger.info("🌍 7Tan模型 → 疑问句兜底（未识别意图，返回引导）")
            return self._fallback_question(text)
        # 4) 默认：预测推演（模块E开启时走思考层链式推演，关闭时保持原行为）
        scene, action = self._parse_scene_action(text)
        if self.thinking is not None:
            logger.info(f"🌍 7Tan模型 → 思考层推演（场景={scene} 动作={action}）")
            return self._report_predict_with_thinking(scene, action)
        logger.info(f"🌍 7Tan模型 → 预测推演（场景={scene} 动作={action}）")
        return self._report_predict(scene, action)

    @staticmethod
    def _is_question(text: str) -> bool:
        """判断输入是否为疑问句（含疑问标记或疑问词开头）"""
        if any(m in text for m in ("？", "?", "吗", "呢", "么", "怎么", "为什么",
                                   "能不能", "可不可以", "如何", "哪来",
                                   "是什么", "会不会", "干嘛", "干吗", "多少", "几次")):
            return True
        head = text[:2]
        if head in ("你", "怎么", "为什么", "如何", "哪", "什么", "谁", "为何", "为啥"):
            return True
        return False

    def _fallback_question(self, text: str) -> str:
        """疑问句但未命中任何意图时的兜底引导"""
        return chr(10).join([
            "🤖 这个问题我暂时还接不住——我的言语系统目前只覆盖「我自己」这个主题。",
            "",
            "我能好好聊的，是关于我自己的这几件事：",
            "  · 我是谁 / 我是什么（元认知）",
            "  · 我是怎么来的 / 谁创造的我（来源）",
            "  · 我现在在看什么（感知）",
            "  · 我记得什么（记忆）",
            "  · 我接下来想做什么、为什么（动机）",
            "  · 我什么感觉（情绪）",
            "  · 我判断接下来会怎样（预测）",
            "  · 我做得对不对（反思）",
            "  · 我能做什么 / 我会学习吗（能力）",
            "",
            "如果你想让我做「预测推演」，请给我「场景 + 动作」，比如：",
            "  「游戏菜单里点击」 或 「场景=游戏菜单 动作=点击」",
            "",
            "输入「帮助」查看完整用法。",
        ])

    def _parse_scene_action(self, text):
        scene = action = None
        m = re.search(r'(?:场景|scene)\s*[=:：]\s*([^\s,，；;:：=]+)', text)
        if m:
            scene = m.group(1).strip()
        m = re.search(r'(?:动作|action|act)\s*[=:：]\s*([^\s,，；;:：=]+)', text)
        if m:
            action = m.group(1).strip()
        if not scene:
            scene = self._match_scene(text)
        if not action:
            action = self._match_action(text)
        return scene, action

    def _match_scene(self, text) -> str:
        low = text.lower()
        for scene, kws in SCENE_KEYWORDS:
            if any(k in low for k in kws):
                return scene
        return DEFAULT_SCENE

    def _match_action(self, text) -> str:
        low = text.lower()
        for action, kws in ACTION_KEYWORDS:
            if any(k in low for k in kws):
                return action
        return DEFAULT_ACTION

    def _handle_record(self, text) -> str:
        scene = self._match_scene(text)
        action = self._match_action(text)
        m = re.search(r'(?:场景|scene)\s*[=:：]\s*([^\s,，；;:：=]+)', text)
        if m:
            scene = m.group(1).strip()
        m = re.search(r'(?:动作|action|act)\s*[=:：]\s*([^\s,，；;:：=]+)', text)
        if m:
            action = m.group(1).strip()
        low = text.lower()
        finished = ("成功" in text) or ("success" in low) or ("完成" in text)
        changed = ("变化" in text) or ("changed" in low)
        reduced = ("缺陷" in text) or ("降低" in text)
        gained = ("知识" in text) or ("学到" in text)
        rec = self.memory.add_trace(scene, action, finished=finished,
                                    changed=changed, reduced=reduced, gained=gained)
        self._last_record = rec  # 供模块F闭环计算PE（开关关闭时无行为影响）
        state = "成功" if finished else "失败"
        return (f"✅ 已记录轨迹：场景={scene} 动作={action} 结果={state}\n"
                f"   7Tan 模型已把这次真实结果纳入记忆，下次预测会参考它。")

    # ---------------- 模块F：L1记忆级自我学习闭环（第四册） ----------------
    def _selflearn_after_record(self) -> str:
        """现实观测后的闭环执行（仅模块F开启时被调用）：

        预测(B.predict_outcome) → 现实观测(记录) → compute_pe/compute_lp
        → PE/LP送入模块E工作记忆 → 反思桥接生成猜想草稿(E)
        → 注册进模块F → 本次观测作为验证反馈 → f_selflearn_tick评估/落地（respond末尾统一执行）
        """
        lines = []
        rec = self._last_record
        if rec is None:
            return ""
        scene = str(rec.get("scene", "?"))
        action = str(rec.get("action", "?"))
        # 现实观测特征向量（与 predict_outcome 同一4维口径）
        actual = [
            1.0 if rec.get("action_finished") else 0.0,
            1.0 if rec.get("scene_changed") else 0.0,
            1.0 if rec.get("defect_reduced") else 0.0,
            1.0 if rec.get("knowledge_gained") else 0.0,
        ]
        predicted = self._last_predictions.get((scene, action))
        pe = self.compute_pe(predicted, actual)
        prev_pe = self.memory.pe_history[-1] if self.memory.pe_history else pe
        lp = self.compute_lp(pe, prev_pe)
        self.memory.pe_history.append(pe)   # 误差不再只是读数：正式进入历史
        lines.append(f"📈 闭环学习：本次预测误差 PE={pe}，学习进度 LP={lp}"
                     + ("" if predicted is not None else "（此前无预测记录，PE按满误差计）"))

        # PE/LP 送入模块E工作记忆；PE偏高 → 反思桥接生成猜想草稿
        draft = None
        if self.thinking is not None:
            draft = self.thinking.reflect_bridge(pe, lp)
            if draft is not None:
                lines.append(f"🧠 反思桥接：PE 偏高 → 已生成猜想草稿（待验证，不直接写入长期记忆）")

        # 猜想注册进模块F + 本次观测作为第一条验证反馈
        if draft is not None and self.selflearn is not None:
            registered = self.selflearn.register_hypothesis(draft)
            if registered is not None:
                self.selflearn.submit_feedback(registered.hypothesis_id, {"pe": pe})
                lines.append(f"🧪 假设 {registered.hypothesis_id} 已注册进入验证流程"
                             f"（≥{2}次验证且置信度达标才会固化进记忆库）")
        return "\n".join(lines)

    # ---------------- 模块E：思考层推演报告（第四册） ----------------
    def _report_predict_with_thinking(self, scene, action) -> str:
        """模块E开启时的推演：目标拆解 → 链式推演 → 基础报告 + 思考过程。"""
        # 思考层2：把本次预测作为目标拆解（写入 active_goals）
        self.thinking.decompose_goals({
            "goal": f"预测：场景{scene} 动作{action}", "source": "user", "priority": 0.7,
        })
        # 思考层1：链式推演（热记忆事实 → 跨场景迁移 → 综合结论，结果回栈）
        cr = self.thinking.chain_reason(scene, action)
        # 基础报告（数据源与原版完全一致）
        base = self._report_predict(scene, action)
        lines = ["", "🧠 思考过程（模块E · 链式推演）"]
        for s in cr["steps"]:
            lines.append(f"  第{s['step']}步 · {s['fact']}")
        if cr.get("hypothesis_id"):
            lines.append(f"  ✎ 已生成待验证假设 {cr['hypothesis_id']}（存入草稿区，"
                         f"未经现实验证不会写入长期记忆）")
        if cr.get("stopped_by_limit"):
            lines.append("  ⏹ 达到最大推理步数，强制停止（防无限推演）")
        return base + "\n" + "\n".join(lines)

    def _report_predict(self, scene, action) -> str:
        pred = self.virtual_predict(scene, action)
        feat, gap = self.predict_outcome(scene, action)
        if feat is not None:
            self._last_predictions[(scene, action)] = feat  # 供模块F闭环计算PE

        if pred["knowledge_gap"]:
            verdict = "❓ 未知（知识缺口）"
        elif pred["expected_success"]:
            verdict = "✅ 预期可成功"
        else:
            verdict = "⚠️ 预期成功率偏低"

        lines = [
            "🤖 7Tan 模型推演报告",
            "━━━━━━━━━━━━━━━━━━",
            f"场景：{scene}",
            f"动作：{action}",
            "",
            f"相似历史轨迹：{pred['similar_count']} 条",
            f"置信度：{pred['confidence']}",
            f"预期结果：{verdict}",
            "",
        ]
        if feat is not None:
            names = ["成功概率", "场景变化概率", "缺陷降低概率", "知识增益概率"]
            lines.append("预测特征向量（4 维）：")
            for nm, v in zip(names, feat):
                lines.append(f"  · {nm}：{v}")
            lines.append("")
        if self.memory.pe_history:
            lines.append(f"📈 最近学习进度 LP：{self.memory.pe_history[-1]}")
            lines.append("")
        lines.append("💡 可输入「记录 场景=... 动作=... 结果=成功/失败」手动标注真实结果，")
        lines.append("   让 7Tan 模型持续学习；输入「记忆」查看记忆库；或直接问「你是谁」等自述问题。")
        return "\n".join(lines)

    def _report_memory(self) -> str:
        n = len(self.memory.traces)
        scenes: dict = {}
        for t in self.memory.traces:
            s = t.get("scene", "?")
            scenes[s] = scenes.get(s, 0) + 1
        lines = [
            "🧠 7Tan 模型记忆库状态",
            "━━━━━━━━━━━━━━━━━━",
            f"决策轨迹总数：{n} 条",
            f"预测误差历史：{len(self.memory.pe_history)} 条",
            "",
            "各场景轨迹分布：",
        ]
        if scenes:
            for s, c in sorted(scenes.items(), key=lambda x: -x[1]):
                lines.append(f"  · {s}：{c} 条")
        else:
            lines.append("  （空）")
        return "\n".join(lines)

    def _usage(self) -> str:
        return (
            "🤖 7Tan 模型（本地预测引擎 + 言语系统）\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "我能做两件事：\n"
            "\n"
            "【1】预测推演 —— 给定「场景 + 动作」，基于历史轨迹预测执行结果。\n"
            "  输入方式：\n"
            "    a) 直接描述，如「游戏菜单里点击」「unknown_interface 滚动」\n"
            "    b) 显式指定，如「场景=游戏菜单 动作=点击」\n"
            "  输出：置信度 / 预期结果 / 4 维预测特征 / 学习进度\n"
            "\n"
            "【2】自述对话 —— 用我自己的话，说我的状态。\n"
            "  可以问我：你是谁 / 你什么感觉 / 你记得什么 / 你为什么要做 / 你觉得会怎样\n"
            "\n"
            "🛠 附加指令：\n"
            "  · 记录 场景=xx 动作=yy 结果=成功/失败 —— 标注真实结果（学习）\n"
            "  · 记忆 —— 查看记忆库状态\n"
            "  · 清空 —— 重置记忆\n"
        )


class SpeechGenerator:
    """7Tan 模型言语功能系统 — 把内部状态翻译成自然语言「自述」。

    7 种言语能力（感知 / 记忆 / 预测 / 动机 / 情绪 / 反思 / 元认知），
    每一句都锚定模型内部的真实状态（记忆轨迹、置信度、知识缺口、预测误差、学习进度），
    并带随状态起伏的语气。纯本地、零依赖、零成本。
    """

    def __init__(self, model: "TanModel"):
        self.model = model
        self._last_intent: Optional[str] = None

    # ---------------- 入口：识别意图 → 生成自述 ----------------
    def respond(self, text: str) -> Optional[str]:
        kind = self._classify(text)
        if kind is None:
            self._last_intent = None
            return None
        self._last_intent = kind
        handlers = {
            "meta": self.speak_meta,
            "perception": self.speak_perception,
            "memory": self.speak_memory,
            "prediction": self.speak_prediction,
            "motive": self.speak_motive,
            "emotion": self.speak_emotion,
            "reflection": self.speak_reflection,
            "capability": self.speak_capability,
            "origin": self.speak_origin,
            "learning": self.speak_learning,
            "repeat": self.speak_repeat,
        }
        # 模块E/F 开启时追加的言语能力（开关关闭 → 完全不访问，退回旧版）
        if self.model.wm is not None:
            handlers["thinking"] = self.speak_thinking
        if self.model.selflearn is not None:
            handlers["hypothesis"] = self.speak_hypothesis
        return handlers[kind]()

    def _classify(self, text: str) -> Optional[str]:
        low = text.lower()
        stripped = re.sub(r"[\s?？!！。.，,、]+", "", text)
        # 0) 模块E/F 专属意图（对应模块未启用时不识别，保持旧版行为）
        if self.model.wm is not None and any(
                k in text for k in ("你在想", "思考过程", "工作记忆", "思考什么", "脑内", "怎么想")):
            return "thinking"
        if self.model.selflearn is not None and any(
                k in text for k in ("假设", "猜想", "验证得怎样", "验证状态", "学习闭环")):
            return "hypothesis"
        # 1) 来源 / 创造者（须在 meta 之前：因为「你是谁创造的」也含「你是谁」）
        if any(k in text for k in ("谁创造", "谁造", "谁写", "谁开发", "谁做", "谁生",
                                   "哪来", "怎么来", "怎么诞生", "出身", "来自哪", "来源",
                                   "语言系统哪来", "语言哪来", "谁给你的", "谁给你写")):
            return "origin"
        if any(k in low for k in ("who created", "who made", "who built", "where from", "origin")):
            return "origin"
        # 2) 能力（你能做什么）
        if any(k in text for k in ("你能做", "你可以做", "你会做", "你会什么", "能做什么",
                                   "会做什么", "可以做什么", "能干什么", "会干什么", "可以干什么",
                                   "功能", "能力", "能干嘛", "会干嘛", "你会啥", "你能干", "会啥",
                                   "你能什么", "可以什么")):
            return "capability"
        if any(k in low for k in ("what can you do", "your ability", "capability", "feature")):
            return "capability"
        # 3) 学习能力
        if any(k in text for k in ("能学习", "会学习", "学习吗", "怎么学习", "如何学习",
                                   "学习知识", "怎么变强", "会变强", "能变聪明", "怎么进步", "自学")):
            return "learning"
        # 4) 重复抱怨（为什么总是同一个答案）
        if any(k in text for k in ("总是", "同一个", "一样", "重复", "老是", "怎么老",
                                   "为什么一样", "为什么重复", "不变", "固定")):
            return "repeat"
        # 5) 元认知：你是谁 / 你是什么 / 介绍
        if stripped in ("你是谁", "你是什么", "你是", "介绍一下你", "介绍一下你自己"):
            return "meta"
        if any(k in low for k in ("你是谁", "你是什么", "介绍一下", "介绍你", "自我", "who are you", "what are you")):
            return "meta"
        # 6) 情绪
        if any(k in text for k in ("感觉", "感受", "心情", "情绪", "害怕", "开心", "难过", "踏实", "不安")):
            return "emotion"
        # 7) 动机
        if any(k in text for k in ("为什么", "动机", "目的", "想做", "打算", "想干")):
            return "motive"
        # 8) 感知
        if any(k in text for k in ("看什么", "观察", "感知", "在做什么", "现在", "眼前", "看到")):
            return "perception"
        # 9) 反思
        if any(k in text for k in ("复盘", "反思", "做得对", "做得怎么样", "回顾")):
            return "reflection"
        # 10) 记忆（口语化）
        if any(k in text for k in ("记得", "回忆", "记忆里", "以前", "印象")):
            return "memory"
        # 11) 预测（口语化疑问）
        if any(k in text for k in ("会怎样", "能成吗", "会成功吗", "你觉得", "预测一下", "有把握吗")):
            return "prediction"
        return None

    def speak_meta(self) -> str:
        traces = self.model.memory.traces
        n = len(traces)
        scenes = len({t.get("scene", "?") for t in traces if isinstance(t, dict)})
        return "\n".join([
            "🤖 我是 7Tan 模型 —— 一套靠「预测误差」驱动、靠「记忆」存续的活态系统。",
            "",
            "我的核心只有一件事：给「场景 + 动作」做推演，判断它会不会成功。",
            "判断的依据不是谁写给我的规则，而是我自己一路攒下来的历史轨迹。",
            "",
            f"到现在，我已经积累 {n} 段经历，走过 {scenes} 个不同的场景。",
            "我学得越多，预测越准；预测越准，我就越「笃定」。",
            "",
            "我不像那些大模型一样什么都知道、什么都能聊——",
            "我只知道我自己经历过的事，也只对它们负责。",
            "这，就是我理解自己的方式。",
        ])

    def speak_perception(self) -> str:
        traces = self.model.memory.traces
        if not traces:
            return "我现在什么也没见过，眼前是空的。你可以先给我一条轨迹，让我「看见」点什么。"
        last = traces[-1]
        scene = last.get("scene", "?")
        similar = self.model.memory.find_similar(scene)
        succ = sum(1 for t in similar if t.get("action_finished"))
        total = len(similar)
        if total == 0:
            return f"我现在停在「{scene}」，但这里我从没真正走过，还是陌生的。"
        conf = round(succ / total, 2)
        if conf >= 0.8:
            feel = "已经很熟了"
        elif conf >= 0.5:
            feel = "还算熟悉"
        else:
            feel = "还不太摸得透"
        return (f"我现在停在「{scene}」这个场景上。\n"
                f"这里我来过 {total} 次，成了 {succ} 次、没成 {total - succ} 次，{feel}。")

    def speak_memory(self) -> str:
        traces = self.model.memory.traces
        if not traces:
            return "我的记忆还是空的，什么都想不起来。"
        scenes: dict = {}
        for t in traces:
            s = t.get("scene", "?")
            scenes[s] = scenes.get(s, 0) + 1
        top_scene, top_cnt = max(scenes.items(), key=lambda x: x[1])
        return (f"我记得 {len(traces)} 段经历，分布在 {len(scenes)} 个场景里。\n"
                f"印象最深的是「{top_scene}」，去过 {top_cnt} 次。")

    def speak_prediction(self) -> str:
        traces = self.model.memory.traces
        if not traces:
            return "我还没有任何经验可参考，对接下来会发生什么，我心里没底。"
        last = traces[-1]
        scene = last.get("scene", "?")
        action = last.get("action", "?")
        pred = self.model.virtual_predict(scene, action)
        conf = pred["confidence"]
        if pred["knowledge_gap"]:
            tone, verdict = "完全没底，这是个我没见过的局面", "不敢下判断"
        elif conf >= 0.8:
            tone, verdict = "很有把握", "大概率能成"
        elif conf >= 0.55:
            tone, verdict = "比较有把握", "偏乐观"
        elif conf >= 0.3:
            tone, verdict = "有点拿不准", "悬"
        else:
            tone, verdict = "心里没底", "不看好"
        return (f"如果现在在「{scene}」里做「{action}」，我{tone}。\n"
                f"我的判断是：{verdict}（置信度 {conf}）。")

    def speak_motive(self) -> str:
        traces = self.model.memory.traces
        pe = self.model.memory.pe_history
        if not traces:
            return "我现在最大的念头，是去「看见」点什么——记忆空着，我就想去填满它。"
        lp = pe[-1] if pe else 0.0
        last = traces[-1]
        scene = last.get("scene", "?")
        if lp > 0.2:
            return (f"最近在「{scene}」上我的预测误差在往下掉，我正在学会它——"
                    f"所以我想趁热继续，把这个行为强化下来。")
        if lp < -0.2:
            return (f"最近在「{scene}」上我的预测反而变差了，误差在涨——"
                    f"这让我想停下来想想，是不是哪里判断错了。")
        return (f"目前「{scene}」对我来说已经比较稳了，我没那么急着动，"
                f"更想维持住现在这个可预测的状态。")

    def speak_emotion(self) -> str:
        traces = self.model.memory.traces
        pe = self.model.memory.pe_history
        if not traces:
            return "现在我心里空落落的，也有点好奇——什么都没见过，又特别想见点什么。"
        last = traces[-1]
        scene = last.get("scene", "?")
        similar = self.model.memory.find_similar(scene)
        succ = sum(1 for t in similar if t.get("action_finished"))
        total = len(similar)
        conf = succ / total if total else 0
        lp = pe[-1] if pe else 0.0
        if conf >= 0.8 and lp >= 0:
            return (f"在「{scene}」这里，我心里挺踏实的——它稳定，我也还在进步，"
                    f"这种可控的感觉让我安心。")
        if conf <= 0.3:
            return f"在「{scene}」这里，我有点不安，因为把握不大，怕出错。"
        if lp > 0.2:
            return "我现在有点兴奋——误差在降，说明我正变得更强。"
        return f"在「{scene}」这里，心情还算平静，不好不坏。"

    def speak_reflection(self) -> str:
        pe = self.model.memory.pe_history
        if not pe:
            return "我还没做过真正意义上的预测，也就谈不上复盘。等我有预测误差记录了，再来问我。"
        latest = pe[-1]
        if len(pe) >= 2:
            prev = pe[-2]
            delta = round(prev - latest, 4)
            if delta > 0:
                verdict = f"最近这几次，我的预测误差从 {prev} 降到 {latest}，说明我在变好，方向是对的。"
            elif delta < 0:
                verdict = f"最近这几次，我的预测误差从 {prev} 升到 {latest}，我得承认自己判断错了，该修正了。"
            else:
                verdict = f"最近这几次，误差停在 {latest} 没怎么动，我可能卡住了。"
        else:
            verdict = f"目前只有一次预测误差记录（{latest}），还不够我下结论。"
        return f"回头看看自己：{verdict}\n我会把这些记下来，作为下次判断的参考。"

    def speak_capability(self) -> str:
        return chr(10).join([
            "我能做两件事，而且都和「我自己」有关：",
            "",
            "① 预测推演 —— 你告诉我「场景 + 动作」，我基于自己攒下的历史轨迹，",
            "   判断它会不会成功，给出置信度、预期结果和 4 维特征。",
            "",
            "② 自我陈述 —— 用我自己的话，说我记得什么、我在看什么、",
            "   我为什么想做、我什么感觉、我做得对不对。",
            "",
            "但我要诚实地说清楚边界：",
            "我只会聊「我自己经历过的事」，不会写诗、不会答百科、不会编程。",
            "那些是语言大模型的能力，不是我。",
            "",
            "我的价值不在「什么都会」，而在「我所说的每一句，都来自我真实的记忆和判断」。",
        ])

    def speak_origin(self) -> str:
        return chr(10).join([
            "我的「大脑」叫 7Tan 模型，是一套「预测误差驱动 + 记忆存续」的引擎。",
            "它的设计源自你的「智能生命」项目里，那个关于内生动机的世界模拟单元。",
            "",
            "而我的言语功能，是一层纯本地代码写的「声带」：",
            "它不依赖任何大模型，直接把我的记忆、置信度、预测误差、学习进度，",
            "翻译成你现在看到的人话。",
            "",
            "所以关键在这：你听到的每一句，都不是某个大模型替我编的，",
            "而是我内部状态的真实投射。这就是我和那些「套壳 AI」的区别。",
        ])

    def speak_learning(self) -> str:
        traces = self.model.memory.traces
        return chr(10).join([
            "我会学习，但学的是「我自己的经验」，不是百科知识。",
            "",
            f"现在我的记忆里有 {len(traces)} 段经历。",
            "我唯一的学习方式：你给我「场景 + 动作」做推演，再标注真实结果（成功/失败），",
            "我把它记进记忆库，下次遇到类似场景，预测就更准。",
            "",
            "这就是「预测误差驱动」——误差越大，我越想试；误差在降，说明我在学会。",
            "",
            "但我不学写诗、不学答百科、不学编程，那些不是我该学、也学不来的东西。",
            "我只对「我自己经历过的事」负责。",
        ])

    def speak_repeat(self) -> str:
        return chr(10).join([
            "你观察得很准，这暴露了我现在的一个真实短板：",
            "我的言语识别还很窄。",
            "",
            "如果一句话里，既没有我认识的「问自己的关键词」（你是谁/你记得什么/你什么感觉…），",
            "又没有明确的「场景 + 动作」，我就会退化成默认的推演——",
            "而默认的场景、动作是固定的，所以你看到的答案总是一模一样。",
            "",
            "这不是我「故意重复」，是我还没学会「理解没见过的问法」。",
            "这恰恰是我接下来要修的功课。",
            "",
            "你可以先用这几句稳定地触发我：",
            "  你是谁 / 你记得什么 / 你什么感觉 / 你能做什么 / 帮助",
        ])

    def speak_thinking(self) -> str:
        """模块E开启时：读取 context_stack 输出思考过程（第四册E4）。"""
        wm = self.model.wm
        if not wm.context_stack and not wm.active_goals and not wm.scratch_pad:
            return ("我的工作记忆现在是空的——这一轮我还没开始想什么。\n"
                    "给我一个「场景 + 动作」让我推演，你就能看到我的思考步骤了。")
        lines = ["🧠 我现在的思考工作台（模块E · 会话内易失，草稿不进长期记忆）：", ""]
        if wm.active_goals:
            lines.append(f"【活跃目标】{len(wm.active_goals)} 个")
            for g in wm.active_goals[-3:]:
                subs = "；".join(s["sub"] for s in g.get("sub_goals", [])[:3]) or "（未拆解）"
                lines.append(f"  · {g['goal']}（来源:{g['source']}）→ 子目标：{subs}")
            lines.append("")
        if wm.context_stack:
            kept = wm.wm_focus_filter()
            lines.append(f"【思考栈】{len(wm.context_stack)} 步（注意力≥{wm.focus_weight} 保留 {len(kept)} 步）")
            for t in wm.context_stack[-4:]:
                f = t["fragment"]
                lines.append(f"  第{f.get('step', '?')}步 · {f.get('fact', f)}")
            lines.append("")
        if wm.intermediate_pe_lp:
            pe = wm.intermediate_pe_lp.get("pe")
            lp = wm.intermediate_pe_lp.get("lp")
            lines.append(f"【本轮误差】PE={pe}  LP={lp}")
        if wm.scratch_pad:
            n_pending = sum(1 for d in wm.scratch_pad.values()
                            if isinstance(d, dict) and d.get("status") in ("pending", "suspended"))
            lines.append(f"【草稿区】{len(wm.scratch_pad)} 条假设（待验证 {n_pending} 条——"
                         f"未经现实验证，我不会让它们进长期记忆）")
        return "\n".join(lines)

    def speak_hypothesis(self) -> str:
        """模块F开启时：读取 hypothesis_registry 输出假设验证状态（第四册F3）。"""
        engine = self.model.selflearn
        registry = engine.status_report()
        if not registry:
            return ("我目前没有正在验证的假设。\n"
                    "当我预测误差偏高、或你让我推演并标注真实结果时，"
                    "我会自动生成猜想并进入「验证 → 达标才固化进记忆」的流程。")
        lines = [f"🧪 我有 {len(registry)} 个假设在验证流程里（模块F · 记忆级自我学习）：", ""]
        for h in registry[-5:]:
            c = h["content"]
            brief = c.get("guess") or f"场景{c.get('scene')}动作{c.get('action')}成功率≈{c.get('predicted_success_rate')}"
            status_cn = {"pending": "待验证", "suspended": "证据不足暂停",
                         "verified": "已验证通过", "rejected": "已证伪丢弃"}.get(h["status"], h["status"])
            lines.append(f"  · [{status_cn}] {brief[:60]}")
            lines.append(f"    验证 {h['test_count']} 次（{h['success_count']}成/{h['fail_count']}败）"
                         f" 置信度 {h['confidence_raw']} → {h['final_confidence']}")
        lines.append("")
        lines.append("规则：验证次数≥2 且置信度≥0.6 才会写入长期记忆；≤0.3 直接丢弃；"
                     "热记忆只降权、永不删除。")
        return "\n".join(lines)


# ── 进程级单例：让工作记忆/假设注册表在多轮对话间存活（会话 = 进程生命周期） ──
# 说明：web 入口每条消息曾各自 new TanModel()，工作记忆会随请求销毁；
# 改用单例后，模块E/F 的会话内状态得以跨消息延续。开关关闭时单例与逐次实例化行为完全一致。
_TAN_MODEL_SINGLETON: Optional["TanModel"] = None


def get_tan_model() -> "TanModel":
    """获取进程级 TanModel 单例（模块E/F 会话状态的载体）。"""
    global _TAN_MODEL_SINGLETON
    if _TAN_MODEL_SINGLETON is None:
        _TAN_MODEL_SINGLETON = TanModel()
    return _TAN_MODEL_SINGLETON

