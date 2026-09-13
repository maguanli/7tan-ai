"""
视频剪辑器 — 项目管理（.7tanproj JSON 格式）

Phase 6 增强：+转场序列化 + 滤镜序列化 + 关键帧序列化
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger
from src.ui.video_editor.data_models import (
    Project, ProjectData, Track, Clip, SubtitleClip, Transition,
    FilterConfig, Keyframe,
)
from src.ui.video_editor.utils import now_iso


class ProjectManager:
    def __init__(self):
        self._recent: list[str] = []
        self._autosave_timer = None

    def new_project(self, name: str = "未命名项目",
                    resolution: tuple = (1920, 1080),
                    fps: int = 30) -> Project:
        p = Project(
            name=name, resolution=resolution, fps=fps,
            created_at=now_iso(), modified_at=now_iso(),
        )
        p.tracks = [
            Track(type="video"),
            Track(type="audio"),
            Track(type="audio"),
            Track(type="subtitle"),
        ]
        p.transitions = []
        logger.info(f"新建项目: {name}")
        return p

    def save(self, project: Project, path: str = None) -> bool:
        target = path or project.file_path
        if not target:
            logger.warning("未指定保存路径")
            return False

        project.modified_at = now_iso()
        pd = project.to_data()

        try:
            data = {
                "version": pd.version,
                "name": pd.name,
                "resolution": list(pd.resolution),
                "fps": pd.fps,
                "duration": pd.duration,
                "created_at": pd.created_at,
                "modified_at": pd.modified_at,
                "tracks": self._serialize_tracks(pd.tracks),
                "cover_data": pd.cover_data,
                "transitions": self._serialize_transitions(
                    getattr(project, 'transitions', []) or []
                ),
                "undo_stack": [],
            }
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            project.file_path = target
            self._add_recent(target)
            logger.info(f"项目已保存: {target}")
            return True
        except Exception as e:
            logger.error(f"保存失败: {e}")
            return False

    def load(self, path: str) -> Optional[Project]:
        if not os.path.exists(path):
            logger.warning(f"项目文件不存在: {path}")
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            pd = ProjectData(
                version=data.get("version", "1.0"),
                name=data.get("name", ""),
                resolution=tuple(data.get("resolution", [1920, 1080])),
                fps=data.get("fps", 30),
                duration=data.get("duration", 0.0),
                created_at=data.get("created_at", ""),
                modified_at=data.get("modified_at", ""),
                tracks=self._deserialize_tracks(data.get("tracks", [])),
                cover_data=data.get("cover_data"),
                transitions=self._deserialize_transitions(
                    data.get("transitions", [])
                ),
            )
            p = pd.to_project(path)
            self._add_recent(path)
            logger.info(f"项目已加载: {path}")
            return p
        except Exception as e:
            logger.error(f"加载失败: {path} — {e}")
            return None

    def auto_save(self, project: Project):
        if not project.file_path:
            return
        self.save(project, project.file_path)

    def get_recent_projects(self) -> list[str]:
        return [r for r in self._recent if os.path.exists(r)]

    def recover_autosave(self) -> Optional[Project]:
        tmp = Path("data/autosave.7tanproj")
        if tmp.exists():
            return self.load(str(tmp))
        return None

    def _add_recent(self, path: str):
        if path in self._recent:
            self._recent.remove(path)
        self._recent.insert(0, path)
        self._recent = self._recent[:10]

    # ---- 序列化 ----

    @staticmethod
    def _serialize_tracks(tracks: list) -> list:
        result = []
        for t in tracks:
            clips = []
            for c in t.clips:
                if isinstance(c, Clip):
                    clips.append({
                        "_type": "Clip", "id": c.id,
                        "source_path": c.source_path, "type": c.type,
                        "track_index": c.track_index,
                        "timeline_start": c.timeline_start,
                        "source_start": c.source_start,
                        "source_end": c.source_end,
                        "duration": c.duration, "speed": c.speed,
                        "properties": c.properties,
                        "filters": ProjectManager._serialize_filters(
                            getattr(c, 'filters', []) or []
                        ),
                        "keyframes": ProjectManager._serialize_keyframes(
                            getattr(c, 'keyframes', []) or []
                        ),
                    })
                elif isinstance(c, SubtitleClip):
                    clips.append({
                        "_type": "SubtitleClip", "id": c.id,
                        "text": c.text, "start_time": c.start_time,
                        "end_time": c.end_time, "track_index": c.track_index,
                        "font": c.font, "font_size": c.font_size,
                        "color": c.color, "position": c.position,
                        "has_outline": c.has_outline,
                    })
            result.append({
                "type": t.type, "clips": clips,
                "muted": t.muted, "locked": t.locked,
            })
        return result

    @staticmethod
    def _serialize_filters(filters: list) -> list:
        return [
            {
                "id": f.id, "type": f.type, "enabled": f.enabled,
                "brightness": f.brightness, "contrast": f.contrast,
                "saturation": f.saturation, "hue": f.hue,
                "gamma": f.gamma, "blur_strength": f.blur_strength,
                "sharpen_strength": f.sharpen_strength,
                "vignette_strength": f.vignette_strength,
                "lut_path": f.lut_path, "custom_filter": f.custom_filter,
            }
            for f in filters if isinstance(f, FilterConfig)
        ]

    @staticmethod
    def _serialize_keyframes(keyframes: list) -> list:
        return [
            {
                "id": k.id, "time": k.time, "property": k.property,
                "value": k.value, "easing": k.easing, "params": k.params,
            }
            for k in keyframes if isinstance(k, Keyframe)
        ]

    @staticmethod
    def _serialize_transitions(transitions: list) -> list:
        return [
            {
                "id": t.id, "type": t.type, "duration": t.duration,
                "prev_clip_id": t.prev_clip_id, "next_clip_id": t.next_clip_id,
                "params": t.params,
            }
            for t in transitions if isinstance(t, Transition)
        ]

    # ---- 反序列化 ----

    @staticmethod
    def _deserialize_tracks(data: list) -> list:
        tracks = []
        for td in data:
            t = Track(
                type=td.get("type", "video"),
                muted=td.get("muted", False),
                locked=td.get("locked", False),
            )
            for cd in td.get("clips", []):
                if cd.get("_type") == "SubtitleClip":
                    t.clips.append(SubtitleClip(
                        id=cd["id"], text=cd.get("text", ""),
                        start_time=cd.get("start_time", 0),
                        end_time=cd.get("end_time", 0),
                        track_index=cd.get("track_index", 0),
                        font=cd.get("font", "Microsoft YaHei"),
                        font_size=cd.get("font_size", 24),
                        color=cd.get("color", "#FFFFFF"),
                        position=cd.get("position", "bottom"),
                        has_outline=cd.get("has_outline", True),
                    ))
                else:
                    clip = Clip(
                        id=cd["id"], source_path=cd["source_path"],
                        type=cd["type"], track_index=cd.get("track_index", 0),
                        timeline_start=cd.get("timeline_start", 0),
                        source_start=cd.get("source_start", 0),
                        source_end=cd.get("source_end", 0),
                        duration=cd.get("duration", 0),
                        speed=cd.get("speed", 1.0),
                        properties=cd.get("properties", {}),
                        filters=ProjectManager._deserialize_filters(
                            cd.get("filters", [])
                        ),
                        keyframes=ProjectManager._deserialize_keyframes(
                            cd.get("keyframes", [])
                        ),
                    )
                    t.clips.append(clip)
            tracks.append(t)
        return tracks

    @staticmethod
    def _deserialize_filters(data: list) -> list:
        result = []
        for fd in data:
            result.append(FilterConfig(
                id=fd.get("id", ""), type=fd.get("type", "color"),
                enabled=fd.get("enabled", True),
                brightness=fd.get("brightness", 0.0),
                contrast=fd.get("contrast", 1.0),
                saturation=fd.get("saturation", 1.0),
                hue=fd.get("hue", 0.0), gamma=fd.get("gamma", 1.0),
                blur_strength=fd.get("blur_strength", 0.0),
                sharpen_strength=fd.get("sharpen_strength", 0.0),
                vignette_strength=fd.get("vignette_strength", 0.0),
                lut_path=fd.get("lut_path", ""),
                custom_filter=fd.get("custom_filter", ""),
            ))
        return result

    @staticmethod
    def _deserialize_keyframes(data: list) -> list:
        result = []
        for kd in data:
            result.append(Keyframe(
                id=kd.get("id", ""), time=kd.get("time", 0.0),
                property=kd.get("property", "opacity"),
                value=kd.get("value", 1.0),
                easing=kd.get("easing", "linear"),
                params=kd.get("params", {}),
            ))
        return result

    @staticmethod
    def _deserialize_transitions(data: list) -> list:
        result = []
        for td in data:
            result.append(Transition(
                id=td.get("id", ""), type=td.get("type", "fade"),
                duration=td.get("duration", 0.5),
                prev_clip_id=td.get("prev_clip_id", ""),
                next_clip_id=td.get("next_clip_id", ""),
                params=td.get("params", {}),
            ))
        return result
