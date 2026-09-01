"""
世界模型（World Model）— 本地预测引擎

来源：智能生命项目的 WorldSimulationUnit（预测误差驱动内生动机的核心组件）。
能力：给定「场景 + 动作」，基于历史决策轨迹预测执行结果——
      置信度、预期是否成功、知识缺口、4 维预测特征向量、学习进度(LP)。

本模块自包含（仅依赖标准库 + loguru），记忆持久化到 data/world_model_memory.json。
接入 AI 工作台后，用户在「当前模型」下拉框选中「世界模型」即可对话测试。

对话用法：
  - 直接描述场景与动作，如「游戏菜单里点击」「unknown_interface 滚动」
  - 或显式指定：场景=游戏菜单 动作=点击
  - 「记录 场景=xx 动作=yy 结果=成功/失败」→ 手动标注一次真实结果（喂给世界模型学习）
  - 「记忆」查看记忆库状态；「清空」重置记忆；「帮助」查看本说明
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Optional

from loguru import logger

# 世界模型的唯一标识（对应数据库 ai_configs 表 config_key 与 model 字段）
WORLD_MODEL_NAME = "world-model"
WORLD_MODEL_DISPLAY = "世界模型"

_MEMORY_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "world_model_memory.json"

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


def is_world_model(model_name: str) -> bool:
    """判断模型名是否指向本地世界模型"""
    m = (model_name or "").strip().lower()
    return m in ("世界模型", "world-model", "world_model", "worldmodel")


def ensure_world_model_config() -> bool:
    """确保数据库中存在「世界模型」配置项（供模型下拉框显示）。

    不抢当前激活模型（is_active=0），仅注册一条本地模型配置。
    """
    try:
        from ..database.db import get_ai_config_by_key, save_ai_config
        if get_ai_config_by_key(WORLD_MODEL_NAME):
            return True
        save_ai_config(
            config_key=WORLD_MODEL_NAME,
            provider="local_world_model",
            model=WORLD_MODEL_DISPLAY,
            base_url="",
            api_key="",
            context_window=128000,
            max_tokens=16384,
            temperature=0.25,
            is_active=0,
            extra_config={"local": True, "desc": "本地世界模型预测引擎"},
        )
        logger.info(f"✅ 已注册世界模型配置: {WORLD_MODEL_NAME}")
        return True
    except Exception as e:
        logger.warning(f"注册世界模型配置失败: {e}")
        return False


class WorldModelMemory:
    """世界模型的记忆库：决策轨迹 + 预测误差历史（持久化 JSON）"""

    def __init__(self, path: Optional[Path] = None):
        self.path = path or _MEMORY_PATH
        self.traces: list = []      # 决策轨迹
        self.pe_history: list = []  # 预测误差历史
        self.load()

    def load(self):
        try:
            if self.path.exists():
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                self.traces = raw.get("traces") or []
                self.pe_history = raw.get("pe_history") or []
                if not self.traces:
                    self._seed_demo_traces()
            else:
                self._seed_demo_traces()
                self.save()
        except Exception as e:
            logger.warning(f"世界模型记忆加载失败，使用空库: {e}")
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
            logger.warning(f"世界模型记忆保存失败: {e}")

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


class WorldModel:
    """世界模型预测引擎 — 移植自智能生命 WorldSimulationUnit"""

    def __init__(self, memory: Optional[WorldModelMemory] = None):
        self.memory = memory or WorldModelMemory()

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
        text = (user_text or "").strip()
        if not text:
            return self._usage()
        low = text.lower()
        if low in ("help", "帮助", "?", "？", "用法"):
            return self._usage()
        if low in ("memory", "记忆", "状态", "status"):
            return self._report_memory()
        if low.startswith(("清空", "clear", "重置", "reset")):
            self.memory.clear()
            return "🧹 记忆库已清空。可重新输入场景+动作开始测试。"
        if low.startswith(("记录", "record", "标注")):
            return self._handle_record(text)
        # 默认：预测推演
        scene, action = self._parse_scene_action(text)
        return self._report_predict(scene, action)

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
        self.memory.add_trace(scene, action, finished=finished,
                              changed=changed, reduced=reduced, gained=gained)
        state = "成功" if finished else "失败"
        return (f"✅ 已记录轨迹：场景={scene} 动作={action} 结果={state}\n"
                f"   世界模型已把这次真实结果纳入记忆，下次预测会参考它。")

    def _report_predict(self, scene, action) -> str:
        pred = self.virtual_predict(scene, action)
        feat, gap = self.predict_outcome(scene, action)

        if pred["knowledge_gap"]:
            verdict = "❓ 未知（知识缺口）"
        elif pred["expected_success"]:
            verdict = "✅ 预期可成功"
        else:
            verdict = "⚠️ 预期成功率偏低"

        lines = [
            "🌍 世界模型推演报告",
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
        lines.append("   让世界模型持续学习；输入「记忆」查看记忆库。")
        return "\n".join(lines)

    def _report_memory(self) -> str:
        n = len(self.memory.traces)
        scenes: dict = {}
        for t in self.memory.traces:
            s = t.get("scene", "?")
            scenes[s] = scenes.get(s, 0) + 1
        lines = [
            "🧠 世界模型记忆库状态",
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
            "🌍 世界模型（本地预测引擎）\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "给定「场景 + 动作」，基于历史轨迹预测执行结果。\n"
            "\n"
            "📥 输入方式：\n"
            "  1) 直接描述，如「游戏菜单里点击」「unknown_interface 滚动」\n"
            "  2) 显式指定，如「场景=游戏菜单 动作=点击」\n"
            "\n"
            "📤 输出：置信度 / 预期结果 / 4 维预测特征 / 学习进度\n"
            "\n"
            "🛠 附加指令：\n"
            "  · 记录 场景=xx 动作=yy 结果=成功/失败 —— 标注真实结果（学习）\n"
            "  · 记忆 —— 查看记忆库状态\n"
            "  · 清空 —— 重置记忆\n"
        )
