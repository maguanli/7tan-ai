
"""
AI 封面引擎 — 对话式封面生成 (Phase 5)

与 cover_editor 通过 load_result() 单向集成：
  AI生成结构化结果 → cover_editor.load_result() → 画布渲染 → 用户微调

支持模板匹配 + SD生图降级 + 版本历史
"""

from __future__ import annotations
import json, os
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal
from loguru import logger


class CoverAIEngine(QObject):
    """AI 封面引擎 — 自然语言 → 封面结构化结果"""

    finished = pyqtSignal(dict)    # 生成完成 → 结果字典
    progress = pyqtSignal(str)     # 进度消息
    error = pyqtSignal(str)

    TEMPLATES = [
        {"name": "游戏解说", "style": "游戏", "bg_color": "#0a0a1a", "font": "Microsoft YaHei",
         "title_pos": (640, 320), "sub_pos": (640, 420),
         "title_size": 72, "title_color": "#00FFFF", "sub_color": "#CCCCCC"},
        {"name": "Vlog", "style": "Vlog", "bg_color": "#f5f0e8", "font": "Microsoft YaHei",
         "title_pos": (640, 340), "sub_pos": (640, 440),
         "title_size": 56, "title_color": "#2d3436", "sub_color": "#636e72"},
        {"name": "教程", "style": "教程", "bg_color": "#ffffff", "font": "Microsoft YaHei",
         "title_pos": (80, 320), "sub_pos": (80, 420),
         "title_size": 52, "title_color": "#2d3436", "sub_color": "#636e72"},
        {"name": "搞笑", "style": "搞笑", "bg_color": "#ffd32a", "font": "Microsoft YaHei",
         "title_pos": (640, 300), "sub_pos": (640, 420),
         "title_size": 68, "title_color": "#d63031", "sub_color": "#2d3436"},
        {"name": "科技", "style": "科技", "bg_color": "#0c0c1d", "font": "Microsoft YaHei",
         "title_pos": (640, 320), "sub_pos": (640, 420),
         "title_size": 64, "title_color": "#0984e3", "sub_color": "#b2bec3"},
    ]

    def __init__(self):
        super().__init__()
        self._history: list[dict] = []   # 版本历史栈
        self._max_history = 20

    # ==== 公开接口 ====

    def generate(self, prompt: str, style: str = "auto") -> dict:
        """从自然语言生成封面结构化结果"""
        self.progress.emit("🤖 AI分析中…")

        # 1. 意图提取
        title, subtitle, detected_style, color_hint = self._extract_intent(prompt, style)
        self.progress.emit(f"📝 标题: {title} | 风格: {detected_style}")

        # 2. 匹配模板
        tmpl = self._match_template(detected_style)

        # 3. 构建结果
        result = self._build_result(title, subtitle, tmpl, color_hint)

        # 4. 推入版本历史
        self._history.append(result)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        self.progress.emit("✅ 封面生成完成")
        self.finished.emit(result)
        return result

    def modify(self, feedback: str, current_result: dict) -> dict:
        """根据反馈修改已有封面"""
        self.progress.emit("🔧 正在修改…")
        self._history.append(current_result)

        # 解析修改指令
        result = dict(current_result)

        # "标题放大" / "标题改小"
        if "放大" in feedback or "变大" in feedback:
            for layer in result.get("layers", []):
                if layer.get("type") == "text" and layer.get("role") == "title":
                    layer["size"] = min(layer.get("size", 64) + 12, 120)
        if "缩小" in feedback or "变小" in feedback:
            for layer in result.get("layers", []):
                if layer.get("type") == "text" and layer.get("role") == "title":
                    layer["size"] = max(layer.get("size", 64) - 12, 24)

        # "颜色改XX"
        import re
        color_map = {
            "红": "#e74c3c", "橙": "#e67e22", "黄": "#f1c40f",
            "绿": "#2ecc71", "蓝": "#3498db", "紫": "#9b59b6",
            "白": "#ffffff", "黑": "#000000", "灰": "#95a5a6",
            "青": "#00FFFF", "粉": "#fd79a8",
        }
        for cn, hexc in color_map.items():
            if f"改{cn}" in feedback or f"调{cn}" in feedback or f"{cn}色" in feedback:
                for layer in result.get("layers", []):
                    if layer.get("type") == "text":
                        layer["color"] = hexc

        # "副标题去掉" / "去掉副标题"
        if "去掉" in feedback and "副标题" in feedback:
            result["layers"] = [l for l in result.get("layers", []) if l.get("role") != "subtitle"]

        # "换个风格" → 切换模板
        if "换风格" in feedback or "换模板" in feedback:
            styles = [t["style"] for t in self.TEMPLATES]
            current_style = result.get("template_style", "")
            for s in styles:
                if s != current_style:
                    tmpl = self._match_template(s)
                    result.update(self._build_template_fields(tmpl))
                    result["template_style"] = s
                    break

        self.finished.emit(result)
        return result

    def undo(self) -> dict | None:
        """撤销到上一版本"""
        if len(self._history) > 1:
            # 当前版本弹出，返回上一版
            self._history.pop()
            return self._history[-1]
        return None

    # ==== 意图提取 ====

    def _extract_intent(self, prompt: str, style: str) -> tuple:
        """从自然语言提取：标题/副标题/风格/色彩偏好"""
        title = prompt.strip()
        subtitle = ""
        detected_style = style
        color_hint = ""

        # 按常见分隔符拆分标题/副标题
        for sep in ["——", "：", "|", "—", ":", " - "]:
            if sep in prompt:
                parts = prompt.split(sep, 1)
                title = parts[0].strip()
                subtitle = parts[1].strip() if len(parts) > 1 else ""
                break

        # 检测风格关键词
        style_keywords = {
            "游戏": ["游戏", "测评", "实况", "通关", "攻略", "电竞"],
            "Vlog": ["vlog", "日常", "生活", "旅行", "美食"],
            "教程": ["教程", "教学", "学习", "入门", "技巧", "方法"],
            "搞笑": ["搞笑", "沙雕", "翻车", "笑死", "离谱"],
            "科技": ["科技", "数码", "测评", "开箱", "手机", "电脑", "AI"],
        }
        if style == "auto":
            for sty, keywords in style_keywords.items():
                if any(kw in prompt for kw in keywords):
                    detected_style = sty
                    break
            if detected_style == "auto":
                detected_style = "科技"

        # 色彩偏好
        colors = {"赛博朋克": "#00FFFF", "暖色": "#e17055", "冷色": "#74b9ff",
                  "暗黑": "#2d3436", "清新": "#55efc4"}
        for kw, hexc in colors.items():
            if kw in prompt:
                color_hint = hexc
                break

        return title, subtitle, detected_style, color_hint

    # ==== 模板匹配 ====

    def _match_template(self, style: str) -> dict:
        for t in self.TEMPLATES:
            if t["style"] == style:
                return t
        return self.TEMPLATES[0]

    def _build_result(self, title: str, subtitle: str, tmpl: dict, color_hint: str) -> dict:
        layers = [{
            "type": "text", "role": "title", "content": title,
            "x": tmpl["title_pos"][0], "y": tmpl["title_pos"][1],
            "font": tmpl["font"], "size": tmpl["title_size"],
            "color": color_hint or tmpl["title_color"],
        }]
        if subtitle:
            layers.append({
                "type": "text", "role": "subtitle", "content": subtitle,
                "x": tmpl["sub_pos"][0], "y": tmpl["sub_pos"][1],
                "font": tmpl["font"], "size": 36,
                "color": tmpl["sub_color"],
            })

        return {
            "template_name": tmpl["name"],
            "template_style": tmpl["style"],
            "bg_color": tmpl["bg_color"],
            "background_file": "",
            "layers": layers,
        }

    def _build_template_fields(self, tmpl: dict) -> dict:
        return {
            "template_name": tmpl["name"],
            "template_style": tmpl["style"],
            "bg_color": tmpl["bg_color"],
        }

    # ==== SD 生图（预留接口） ====

    def generate_background_sd(self, prompt: str) -> str | None:
        """调用 SD WebUI API 生成背景图，返回路径或 None"""
        try:
            import requests
            import base64
            import tempfile

            resp = requests.post(
                "http://127.0.0.1:7860/sdapi/v1/txt2img",
                json={"prompt": prompt, "steps": 20, "width": 1280, "height": 720},
                timeout=60,
            )
            if resp.status_code == 200:
                img_b64 = resp.json()["images"][0]
                fd, path = tempfile.mkstemp(suffix=".png", prefix="sd_bg_")
                with open(path, "wb") as f:
                    f.write(base64.b64decode(img_b64))
                return path
        except Exception as e:
            logger.info(f"[封面AI] SD 不可用: {e}")
        return None

    @property
    def history(self) -> list[dict]:
        return self._history
