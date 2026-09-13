"""
视频剪辑器 — 命令模式（Undo/Redo）
每个操作封装为 Command 对象，支持 Ctrl+Z / Ctrl+Y

Phase 3: +裁剪(TrimClipCommand) +切割撤销修复
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.ui.video_editor.data_models import Project


class ClipCommand(ABC):
    description: str = ""
    @abstractmethod
    def execute(self, project: Project) -> bool: ...
    @abstractmethod
    def undo(self, project: Project) -> bool: ...
    def redo(self, project: Project) -> bool: return self.execute(project)


class AddClipCommand(ClipCommand):
    def __init__(self, track_index: int, clip_data: dict):
        self.ti = track_index; self.cd = clip_data; self.description = "添加片段"
    def execute(self, p) -> bool:
        from src.ui.video_editor.data_models import Clip
        if self.ti < len(p.tracks): p.tracks[self.ti].clips.append(Clip(**self.cd)); return True
        return False
    def undo(self, p) -> bool:
        if self.ti < len(p.tracks):
            cid = self.cd.get("id","")
            p.tracks[self.ti].clips = [c for c in p.tracks[self.ti].clips if getattr(c,"id","")!=cid]
            return True
        return False


class DeleteClipCommand(ClipCommand):
    def __init__(self, ti: int, ci: int, cd: dict):
        self.ti = ti; self.ci = ci; self.cd = cd; self.description = "删除片段"
    def execute(self, p) -> bool:
        if self.ti < len(p.tracks):
            t = p.tracks[self.ti]
            if 0 <= self.ci < len(t.clips): t.clips.pop(self.ci); return True
        return False
    def undo(self, p) -> bool:
        from src.ui.video_editor.data_models import Clip
        if self.ti < len(p.tracks):
            t = p.tracks[self.ti]; idx = min(self.ci, len(t.clips))
            t.clips.insert(idx, Clip(**self.cd)); return True
        return False


class MoveClipCommand(ClipCommand):
    def __init__(self, ti: int, ci: int, old_s: float, new_s: float):
        self.ti = ti; self.ci = ci; self.old = old_s; self.new = new_s
        self.description = f"移动 {old_s:.1f}s->{new_s:.1f}s"
    def execute(self, p) -> bool: return self._s(p, self.new)
    def undo(self, p) -> bool: return self._s(p, self.old)
    def _s(self, p, v):
        if self.ti < len(p.tracks):
            t = p.tracks[self.ti]
            if 0 <= self.ci < len(t.clips): t.clips[self.ci].timeline_start = v; return True
        return False


class SplitClipCommand(ClipCommand):
    def __init__(self, ti: int, ci: int, st: float, nd: dict, oe: float, ns: float):
        self.ti = ti; self.ci = ci; self.st = st; self.nd = nd; self.oe = oe; self.ns = ns
        self.description = f"切割 @{st:.1f}s"
    def execute(self, p) -> bool:
        from src.ui.video_editor.data_models import Clip
        if self.ti < len(p.tracks):
            t = p.tracks[self.ti]
            if 0 <= self.ci < len(t.clips):
                c = t.clips[self.ci]; c.source_end = self.ns
                c.duration = self.ns - c.source_start
                t.clips.insert(self.ci+1, Clip(**self.nd)); return True
        return False
    def undo(self, p) -> bool:
        if self.ti < len(p.tracks):
            t = p.tracks[self.ti]
            if 0 <= self.ci < len(t.clips):
                t.clips[self.ci].source_end = self.oe
                t.clips[self.ci].duration = self.oe - t.clips[self.ci].source_start
            if self.ci+1 < len(t.clips): t.clips.pop(self.ci+1)
            return True
        return False


class TrimClipCommand(ClipCommand):
    """裁剪片段 — 拖拽首尾边缘改变入点/出点"""
    def __init__(self, ti: int, ci: int,
                 old_start: float, new_start: float,
                 old_source_start: float, new_source_start: float,
                 old_source_end: float, new_source_end: float,
                 old_duration: float, new_duration: float):
        self.ti = ti; self.ci = ci
        self.old_ts = old_start; self.new_ts = new_start
        self.old_ss = old_source_start; self.new_ss = new_source_start
        self.old_se = old_source_end; self.new_se = new_source_end
        self.old_dur = old_duration; self.new_dur = new_duration
        edge = "左" if abs(old_start - new_start) > 0.01 else "右"
        self.description = f"裁剪{edge}边缘 {old_duration:.1f}s->{new_duration:.1f}s"
    def execute(self, p) -> bool:
        return self._apply(p, self.new_ts, self.new_ss, self.new_se, self.new_dur)
    def undo(self, p) -> bool:
        return self._apply(p, self.old_ts, self.old_ss, self.old_se, self.old_dur)
    def _apply(self, p, ts, ss, se, dur):
        if self.ti < len(p.tracks):
            t = p.tracks[self.ti]
            if 0 <= self.ci < len(t.clips):
                c = t.clips[self.ci]
                c.timeline_start = ts
                c.source_start = ss
                c.source_end = se
                c.duration = dur
                return True
        return False


class SetSpeedCommand(ClipCommand):
    def __init__(self, ti: int, ci: int, old_v: float, new_v: float):
        self.ti = ti; self.ci = ci; self.old = old_v; self.new = new_v
        self.description = f"变速 {old_v}x->{new_v}x"
    def execute(self, p) -> bool: return self._s(p, self.new)
    def undo(self, p) -> bool: return self._s(p, self.old)
    def _s(self, p, v):
        if self.ti < len(p.tracks):
            t = p.tracks[self.ti]
            if 0 <= self.ci < len(t.clips): t.clips[self.ci].speed = v; return True
        return False


class UndoManager:
    def __init__(self, max_depth: int = 50):
        self._u = []; self._r = []; self._md = max_depth
    @property
    def can_undo(self) -> bool: return len(self._u) > 0
    @property
    def can_redo(self) -> bool: return len(self._r) > 0
    @property
    def undo_description(self) -> str:
        return self._u[-1].description if self._u else ""
    def execute(self, cmd, p) -> bool:
        if cmd.execute(p):
            self._u.append(cmd); self._r.clear()
            if len(self._u) > self._md: self._u.pop(0)
            return True
        return False
    def undo(self, p) -> bool:
        if not self._u: return False
        cmd = self._u.pop()
        if cmd.undo(p): self._r.append(cmd); return True
        self._u.append(cmd); return False
    def redo(self, p) -> bool:
        if not self._r: return False
        cmd = self._r.pop()
        if cmd.redo(p): self._u.append(cmd); return True
        self._r.append(cmd); return False
    def clear(self): self._u.clear(); self._r.clear()
