"""
视频剪辑器 — 编辑器 API（供 AI 调用）

所有公开方法构成 AI 剪辑引擎的操作接口。
AI 自然语言指令解析后的结构化 JSON 最终调用此 API。
"""
from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from dataclasses import asdict

if TYPE_CHECKING:
    from src.ui.video_editor.data_models import Project, Clip, RecordingConfig
    from src.ui.video_editor.editor_window import VideoEditorPage

from loguru import logger
from src.ui.video_editor.data_models import Clip as ClipModel, Track, SubtitleClip
from src.ui.video_editor.utils import generate_clip_id, get_media_type, get_media_duration_ffprobe


class EditorAPI:
    """剪辑器公开 API — 供 AI 和内部模块调用"""

    def __init__(self, editor: "VideoEditorPage"):
        self._editor = editor

    @property
    def project(self) -> "Project":
        return self._editor.project

    # ---- 素材管理 ----

    def import_media(self, file_path: str) -> Optional[dict]:
        """导入媒体文件到素材库。返回素材信息字典。"""
        import os
        if not os.path.exists(file_path):
            logger.warning(f"文件不存在: {file_path}")
            return None

        media_type = get_media_type(file_path)
        if media_type == "unknown":
            logger.warning(f"不支持的格式: {file_path}")
            return None

        duration = get_media_duration_ffprobe(file_path) if media_type != "image" else None
        info = {
            "id": generate_clip_id(),
            "path": file_path,
            "name": os.path.basename(file_path),
            "type": media_type,
            "duration": duration or 0.0,
        }
        self._editor._media_bin_add(info)
        logger.info(f"导入素材: {info['name']} ({media_type})")
        return info

    def import_media_batch(self, file_paths: list[str]) -> list[dict]:
        """批量导入"""
        return [r for fp in file_paths if (r := self.import_media(fp))]

    # ---- 时间轴操作 ----

    def add_clip_to_timeline(self, media_info: dict, track_index: int = 0,
                              timeline_start: float = 0.0) -> Optional[str]:
        """把素材添加到时间轴"""
        mt = media_info.get("type", "video")
        if mt == "audio" and track_index == 0:
            track_index = 1  # 音频默认放到音频轨

        cid = generate_clip_id()
        dur = media_info.get("duration", 0.0)
        if mt == "image":
            dur = 5.0  # 图片默认 5 秒

        clip = ClipModel(
            id=cid,
            source_path=media_info["path"],
            type=mt,
            track_index=track_index,
            timeline_start=timeline_start,
            source_start=0.0,
            source_end=dur,
            duration=dur,
        )

        # 确保目标轨道存在
        while len(self.project.tracks) <= track_index:
            track_type = "video" if len(self.project.tracks) == 0 else "audio"
            self.project.tracks.append(Track(type=track_type))

        self.project.tracks[track_index].clips.append(clip)
        self._editor._timeline_refresh()
        logger.info(f"添加片段: {media_info['name']} -> 轨道{track_index} @{timeline_start:.1f}s")
        return cid

    def delete_clip(self, track_index: int, clip_index: int) -> bool:
        """删除指定片段"""
        if track_index < len(self.project.tracks):
            t = self.project.tracks[track_index]
            if 0 <= clip_index < len(t.clips):
                t.clips.pop(clip_index)
                self._editor._timeline_refresh()
                return True
        return False

    def move_clip(self, track_index: int, clip_index: int,
                  new_timeline_start: float) -> bool:
        """移动片段"""
        if track_index < len(self.project.tracks):
            t = self.project.tracks[track_index]
            if 0 <= clip_index < len(t.clips):
                t.clips[clip_index].timeline_start = max(0, new_timeline_start)
                self._editor._timeline_refresh()
                return True
        return False

    def split_clip(self, track_index: int, clip_index: int,
                   split_time: float) -> bool:
        """切割片段"""
        if track_index >= len(self.project.tracks):
            return False
        t = self.project.tracks[track_index]
        if clip_index < 0 or clip_index >= len(t.clips):
            return False

        c = t.clips[clip_index]
        if split_time <= c.source_start or split_time >= c.source_end:
            return False

        new_id = generate_clip_id()
        new_clip = ClipModel(
            id=new_id,
            source_path=c.source_path,
            type=c.type,
            track_index=track_index,
            timeline_start=c.timeline_start + (split_time - c.source_start) / c.speed,
            source_start=split_time,
            source_end=c.source_end,
            duration=c.source_end - split_time,
            speed=c.speed,
        )
        c.source_end = split_time
        c.duration = split_time - c.source_start
        t.clips.insert(clip_index + 1, new_clip)
        self._editor._timeline_refresh()
        logger.info(f"切割: 轨道{track_index}#{clip_index} @{split_time:.1f}s")
        return True

    def set_speed(self, track_index: int, clip_index: int, speed: float) -> bool:
        """设置变速（0.25x ~ 4.0x）"""
        speed = max(0.25, min(4.0, speed))
        if track_index < len(self.project.tracks):
            t = self.project.tracks[track_index]
            if 0 <= clip_index < len(t.clips):
                t.clips[clip_index].speed = speed
                self._editor._timeline_refresh()
                return True
        return False

    def swap_clips(self, track_index: int, index_a: int, index_b: int) -> bool:
        """交换两个片段位置"""
        if track_index < len(self.project.tracks):
            t = self.project.tracks[track_index]
            mx = max(index_a, index_b)
            if mx < len(t.clips) and index_a != index_b:
                t.clips[index_a], t.clips[index_b] = t.clips[index_b], t.clips[index_a]
                self._editor._timeline_refresh()
                return True
        return False

    # ---- 字幕 ----

    def add_subtitle(self, text: str, start_time: float, end_time: float,
                      track_index: int = 0) -> Optional[str]:
        """添加字幕"""
        sid = generate_clip_id()
        sub = SubtitleClip(id=sid, text=text, start_time=start_time, end_time=end_time,
                           track_index=track_index)

        # 确保字幕轨道存在
        while len(self.project.tracks) <= 3:
            self.project.tracks.append(Track(type="subtitle" if len(self.project.tracks) >= 3 else "audio"))
        if len(self.project.tracks) <= 3:
            self.project.tracks.append(Track(type="subtitle"))

        # 字幕轨在索引 3（视频0，音频1，音频2，字幕3）
        sub_track_idx = 3
        while len(self.project.tracks) <= sub_track_idx:
            self.project.tracks.append(Track(type="subtitle"))
        self.project.tracks[sub_track_idx].clips.append(sub)
        self._editor._timeline_refresh()
        return sid

    # ---- 录屏 ----

    def start_recording(self, config: Optional["RecordingConfig"] = None) -> bool:
        """开始录屏"""
        return self._editor._start_recording(config)

    def stop_recording(self) -> Optional[str]:
        """停止录屏，返回录制文件路径"""
        return self._editor._stop_recording()

    # ---- 封面 ----

    def make_cover(self, prompt: str = "") -> Optional[dict]:
        """生成封面。有 prompt 走 AI 模式，无 prompt 打开手动编辑器。"""
        if prompt:
            return self._editor._ai_generate_cover(prompt)
        else:
            self._editor._open_cover_editor()
            return {"status": "manual_mode"}

    # ---- 导出 ----

    def export(self, output_path: str = "", resolution: str = "1920x1080",
               fps: int = 30, codec: str = "libx264") -> bool:
        """导出视频"""
        return self._editor._export_video(output_path, resolution, fps, codec)

    # ---- 撤销/重做 ----

    def undo(self) -> bool:
        return self._editor._undo_manager.undo(self.project)

    def redo(self) -> bool:
        return self._editor._undo_manager.redo(self.project)

    # ---- 播放控制 ----

    def play(self): self._editor._player_play()
    def pause(self): self._editor._player_pause()
    def seek(self, time_sec: float): self._editor._player_seek(time_sec)
    def get_current_time(self) -> float:
        return self._editor._player_get_time()
