"""
AI 剪辑引擎 — 自然语言驱动剪辑

Phase 5: 意图识别 + NL→结构化操作 + 执行管道

架构（参见文档第七章）：
  用户自然语言 → 意图解析 → 结构化指令 → EditorAPI 执行 → 结果反馈
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional, Callable

from loguru import logger


# ======================================================================
#  意图结构
# ======================================================================

@dataclass
class ClipIntent:
    """解析后的剪辑意图"""
    action: str                          # import / delete_clip / swap_clips / split /
                                         # set_speed / make_cover / start_recording /
                                         # stop_recording / export / undo / redo /
                                         # add_subtitle / ai_dub / unknown
    params: dict = field(default_factory=dict)
    confidence: float = 0.0
    raw_text: str = ""


# ======================================================================
#  剪辑引擎
# ======================================================================

class AIClipEngine:
    """AI 剪辑引擎

    解析用户自然语言 → ClipIntent → 调用 EditorAPI 执行

    使用方式:
        engine = AIClipEngine(editor_page)
        result = engine.process("把第2段加速2倍")
        # → "✅ 已将第2段速度设为 2.0x"
    """

    # ---- 意图关键词表 ----
    INTENT_PATTERNS: list[tuple[str, str, list[str]]] = [
        # (action, 正则, 触发词列表)
        ("undo",     r"撤销|undo|回退|回到上一步|返回上一步|我不喜欢|不对", []),
        ("redo",     r"重做|redo|恢复|还原", []),
        ("export",   r"导出|export", []),
        ("delete_clip", r"删除第?(\d+)?段|删掉第?(\d+)?段|去掉第?(\d+)?段|移除第?(\d+)?段", []),
        ("swap_clips",  r"交换第?(\d+)和第?(\d+)|第?(\d+)和第?(\d+)换", []),
        ("split",    r"切[割开]|分割|从第?(\d+)秒.*切", []),
        ("set_speed",   r"加速|减速|变速|(\d+)倍速|速度.*?(\d+)", []),
        ("add_subtitle", r"添加字幕|加字幕|生成字幕|识别字幕|字幕", []),
        ("ai_dub",   r"配音|语音|朗读|配音.*文字|文字.*配音", []),
        ("make_cover",  r"封面|缩略图|封图|做.*封面|生成.*封面", []),
        ("start_recording", r"开始录屏|录屏|录制|开始录制", []),
        ("stop_recording",  r"停止录屏|停止录制|结束录屏|结束录制", []),
        ("import",   r"导入|添加素材|加入.*(mp4|mov|avi|mkv|mp3|wav|png|jpg)", []),
    ]

    def __init__(self, editor_page):
        """editor_page: VideoEditorPage 实例"""
        self._editor = editor_page
        self._api = editor_page.api
        self._last_intent: Optional[ClipIntent] = None

    # ==================================================================
    #  公开接口
    # ==================================================================

    def process(self, text: str) -> str:
        """处理一条自然语言指令，返回反馈消息"""
        text = text.strip()
        if not text:
            return ""

        intent = self._parse(text)
        self._last_intent = intent
        logger.info(f"[AI剪辑] 意图: {intent.action} (置信度 {intent.confidence:.2f}) ← \"{text}\"")

        if intent.action == "unknown":
            return self._unknown_response(text)

        return self._execute(intent)

    def process_stream(self, text: str,
                       on_chunk: Optional[Callable[[str], None]] = None) -> str:
        """流式处理（预留，目前同步执行）"""
        result = self.process(text)
        if on_chunk:
            on_chunk(result)
        return result

    @property
    def last_intent(self) -> Optional[ClipIntent]:
        return self._last_intent

    # ==================================================================
    #  意图解析
    # ==================================================================

    def _parse(self, text: str) -> ClipIntent:
        """自然语言 → ClipIntent"""
        text_lower = text.lower()

        for action, pattern, _triggers in self.INTENT_PATTERNS:
            m = re.search(pattern, text_lower)
            if m:
                params = self._extract_params(action, text, m)
                confidence = self._calc_confidence(action, text, m)
                return ClipIntent(
                    action=action, params=params,
                    confidence=confidence, raw_text=text,
                )

        # 未匹配 → unknown
        return ClipIntent(action="unknown", params={}, confidence=0.0, raw_text=text)

    def _extract_params(self, action: str, text: str,
                        match: re.Match) -> dict:
        """从匹配中提取结构化参数"""
        params: dict = {}
        groups = match.groups()

        try:
            if action == "delete_clip":
                idx = self._first_group_int(groups)
                if idx is not None:
                    params["clip_index"] = idx

            elif action == "swap_clips":
                nums = [int(g) for g in groups if g and g.isdigit()]
                if len(nums) >= 2:
                    params["index_a"], params["index_b"] = nums[0], nums[1]

            elif action == "split":
                sec = self._first_group_int(groups)
                if sec is not None:
                    params["time"] = float(sec)

            elif action == "set_speed":
                nums = [float(g) for g in groups if g and self._is_number(g)]
                if nums:
                    params["speed"] = nums[0]

            elif action == "export":
                params.update(self._parse_export_params(text))

        except Exception as e:
            logger.warning(f"[AI剪辑] 参数提取异常: {e}")

        return params

    def _parse_export_params(self, text: str) -> dict:
        """解析导出参数：分辨率/帧率/格式"""
        p: dict = {}
        # 分辨率: 1080p / 4K / 1920x1080
        if m := re.search(r'(\d{3,4})p', text):
            h = int(m.group(1))
            p["resolution"] = f"{h*16//9}x{h}"
        elif m := re.search(r'(\d{3,4})\s*[x×]\s*(\d{3,4})', text):
            p["resolution"] = f"{m.group(1)}x{m.group(2)}"
        # 帧率
        if m := re.search(r'(\d+)\s*帧', text):
            p["fps"] = int(m.group(1))
        # 格式
        if "mp4" in text.lower():
            p["format"] = "mp4"
        elif "mov" in text.lower():
            p["format"] = "mov"
        elif "gif" in text.lower():
            p["format"] = "gif"
        return p

    def _calc_confidence(self, action: str, text: str,
                         match: re.Match) -> float:
        """计算意图置信度 0~1"""
        base = 0.85 if action != "unknown" else 0.0

        # 有具体参数加置信度
        groups = [g for g in match.groups() if g]
        if groups:
            base = min(base + 0.1, 1.0)

        # 文本较长但匹配短 → 降置信度
        if len(text) > 30 and len(match.group()) < 5:
            base = max(base - 0.15, 0.5)

        return base

    # ==================================================================
    #  执行
    # ==================================================================

    def _execute(self, intent: ClipIntent) -> str:
        """执行 ClipIntent，返回用户反馈"""
        p = intent.params

        try:
            # -- 撤销 / 重做 --
            if intent.action == "undo":
                if self._editor._undo_manager.undo(self._editor.project):
                    self._editor._sync_timeline()
                    return "✅ 已撤销上一步操作"
                return "⚠️ 没有可撤销的操作"

            if intent.action == "redo":
                if self._editor._undo_manager.redo(self._editor.project):
                    self._editor._sync_timeline()
                    return "✅ 已重做"
                return "⚠️ 没有可重做的操作"

            # -- 导入 --
            if intent.action == "import":
                path = self._extract_path(intent.raw_text)
                if path:
                    self._editor.media_bin.add_media_batch([path])
                    return f"✅ 已导入: {path}"
                return "⚠️ 未能识别文件路径，请手动导入"

            # -- 删除片段 --
            if intent.action == "delete_clip":
                idx = p.get("clip_index")
                if idx:
                    clips = self._editor.project.all_clips
                    if 1 <= idx <= len(clips):
                        self._editor._delete_clip_by_index(idx - 1)
                        return f"✅ 已删除第{idx}段"
                # 无索引 → 删除当前选中的
                cid = self._editor.timeline.get_selected_clip_id()
                if cid:
                    self._editor._on_delete_clip(cid)
                    return "✅ 已删除选中片段"
                return "⚠️ 请指定要删除第几段，或先点击选中一个片段"

            # -- 交换 --
            if intent.action == "swap_clips":
                a, b = p.get("index_a", 0), p.get("index_b", 0)
                clips = self._editor.project.all_clips
                if 1 <= a <= len(clips) and 1 <= b <= len(clips):
                    ca, cb = clips[a-1], clips[b-1]
                    # 在轨道内交换
                    for track in self._editor.project.tracks:
                        try:
                            ia = track.clips.index(ca)
                            ib = track.clips.index(cb)
                            track.clips[ia], track.clips[ib] = track.clips[ib], track.clips[ia]
                            break
                        except ValueError:
                            pass
                    self._editor._sync_timeline()
                    return f"✅ 已交换第{a}段和第{b}段"
                return "⚠️ 片段索引超出范围"

            # -- 切割 --
            if intent.action == "split":
                time = p.get("time")
                if time is not None:
                    self._editor.player.seek(time)
                    self._editor._on_cut()
                    return f"✅ 已在 {time:.1f} 秒处切割"
                # 无时间 → 当前播放头
                self._editor._on_cut()
                return "✅ 已在当前位置切割"

            # -- 变速 --
            if intent.action == "set_speed":
                speed = p.get("speed", 1.0)
                cid = self._editor.timeline.get_selected_clip_id()
                if cid:
                    for clip in self._editor.project.all_clips:
                        if clip.id == cid:
                            clip.speed = speed
                            self._editor._update_clip_display(clip)
                            return f"✅ 已将片段速度设为 {speed}x"
                return f"⚠️ 请先点击选中一个片段再变速"

            # -- AI 配音 --
            if intent.action == "ai_dub":
                text = self._extract_quote(intent.raw_text)
                self._editor._on_ai_dub_real(text)
                return f"🎙️ AI配音已启动" + (f": \"{text}\"" if text else "")

            # -- AI 字幕 --
            if intent.action == "add_subtitle":
                self._editor._on_ai_subtitle_real()
                return "📝 AI字幕生成已启动"

            # -- 封面 --
            if intent.action == "make_cover":
                title = self._extract_quote(intent.raw_text)
                if not title:
                    title = self._editor.project.name
                self._editor._on_ai_generate_cover_real(title)
                return f"🖼️ AI封面生成中: \"{title}\""

            # -- 录屏 --
            if intent.action == "start_recording":
                self._editor._start_recording()
                return "🔴 录屏已启动"

            if intent.action == "stop_recording":
                self._editor._on_overlay_stop()
                return "✅ 录屏已停止"

            # -- 导出 --
            if intent.action == "export":
                return self._execute_export(p)

        except Exception as e:
            logger.exception(f"[AI剪辑] 执行异常: {e}")
            return f"❌ 执行失败: {e}"

        return "✅ 操作完成"

    def _execute_export(self, params: dict) -> str:
        """执行导出"""
        resolution = params.get("resolution", "1920x1080")
        fps = params.get("fps", 30)
        fmt = params.get("format", "mp4")

        from pathlib import Path
        output = str(Path.home() / "Desktop" /
                     f"{self._editor.project.name}.{fmt}")
        ok = self._editor._export_video(output, resolution, fps, "libx264")
        if ok:
            return f"✅ 导出完成: {output}"
        return "❌ 导出失败"

    # ==================================================================
    #  工具方法
    # ==================================================================

    def _first_group_int(self, groups: tuple) -> Optional[int]:
        for g in groups:
            if g and g.isdigit():
                return int(g)
        return None

    @staticmethod
    def _is_number(s: str) -> bool:
        try:
            float(s)
            return True
        except ValueError:
            return False

    def _extract_path(self, text: str) -> Optional[str]:
        """从文本中提取文件路径"""
        # 引号路径
        m = re.search(r'["\"]([A-Za-z]:\\[^"\"]+?\.[a-zA-Z0-9]+)["\"]', text)
        if m:
            return m.group(1)
        # 无引号但明显是路径
        m = re.search(r'([A-Za-z]:\\\S+\.(mp4|mov|avi|mkv|mp3|wav|png|jpg|jpeg))',
                      text, re.IGNORECASE)
        if m:
            return m.group(1)
        return None

    def _extract_quote(self, text: str) -> str:
        """提取引号内文本"""
        m = re.search(r'["\u201c]([^"\u201d]+)["\u201d]', text)
        if m:
            return m.group(1)
        # 「」
        m = re.search(r'「([^」]+)」', text)
        if m:
            return m.group(1)
        return ""

    def _unknown_response(self, text: str) -> str:
        """未识别意图时的反馈"""
        hints = [
            "💡 试试这些指令：",
            "• \"导入桌面上的视频\"",
            "• \"删除第2段\"",
            "• \"从30秒处切开\"",
            "• \"把第1段加速2倍\"",
            "• \"帮我做一个封面\"",
            "• \"导出为1080p 60帧\"",
            "• \"撤销\"",
        ]
        return "\n".join(hints)
