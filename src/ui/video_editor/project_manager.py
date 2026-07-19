"""
视频剪辑器 — 项目管理（.7tanproj JSON 格式）
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger
from src.ui.video_editor.data_models import Project, ProjectData, Track
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
                "undo_stack": [],  # 命令对象不可序列化，只存计数
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
        # 检查临时目录
        tmp = Path("data/autosave.7tanproj")
        if tmp.exists():
            return self.load(str(tmp))
        return None

    def _add_recent(self, path: str):
        if path in self._recent:
            self._recent.remove(path)
        self._recent.insert(0, path)
        self._recent = self._recent[:10]

    @staticmethod
    def _serialize_tracks(tracks: list) -> list:
        result = []
        for t in tracks:
            clips = []
            for c in t.clips:
                if hasattr(c, "source_path"):  # Clip
                    clips.append({
                        "_type": "Clip", "id": c.id,
                        "source_path": c.source_path, "type": c.type,
                        "track_index": c.track_index,
                        "timeline_start": c.timeline_start,
                        "source_start": c.source_start,
                        "source_end": c.source_end,
                        "duration": c.duration, "speed": c.speed,
                        "properties": c.properties,
                    })
                else:  # SubtitleClip
                    clips.append({
                        "_type": "SubtitleClip", "id": c.id,
                        "text": c.text, "start_time": c.start_time,
                        "end_time": c.end_time, "track_index": c.track_index,
                        "font": c.font, "font_size": c.font_size,
                        "color": c.color, "position": c.position,
                        "has_outline": c.has_outline,
                    })
            result.append({"type": t.type, "clips": clips, "muted": t.muted, "locked": t.locked})
        return result

    @staticmethod
    def _deserialize_tracks(data: list) -> list:
        from src.ui.video_editor.data_models import Clip, SubtitleClip
        tracks = []
        for td in data:
            t = Track(type=td.get("type", "video"), muted=td.get("muted", False),
                       locked=td.get("locked", False))
            for cd in td.get("clips", []):
                if cd.get("_type") == "SubtitleClip":
                    t.clips.append(SubtitleClip(
                        id=cd["id"], text=cd.get("text",""),
                        start_time=cd.get("start_time",0),
                        end_time=cd.get("end_time",0),
                        font=cd.get("font","Microsoft YaHei"),
                        font_size=cd.get("font_size",24),
                        color=cd.get("color","#FFFFFF"),
                        position=cd.get("position","bottom"),
                        has_outline=cd.get("has_outline",True),
                    ))
                else:
                    t.clips.append(Clip(
                        id=cd["id"], source_path=cd["source_path"],
                        type=cd["type"], track_index=cd.get("track_index",0),
                        timeline_start=cd.get("timeline_start",0),
                        source_start=cd.get("source_start",0),
                        source_end=cd.get("source_end",0),
                        duration=cd.get("duration",0),
                        speed=cd.get("speed",1.0),
                        properties=cd.get("properties",{}),
                    ))
            tracks.append(t)
        return tracks
