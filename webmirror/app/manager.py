"""
任务管理器：创建/启动/停止镜像任务，维护实时进度、日志、文件树与打包下载。
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import time
import uuid
import zipfile
from collections import deque
from datetime import datetime
from typing import Any

from .crawler import CrawlConfig, Mirror, normalize_url

def _data_root() -> str:
    """数据根目录（存放 downloads/）。

    - 源码运行：webmirror/ 目录
    - 打包成 exe：exe 所在目录。__file__ 在 PyInstaller 下指向临时解包目录
      (_MEIPASS)，若沿用它，抓下来的整站会写进临时目录、进程一退就没了。
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


BASE_DIR = _data_root()
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")
INDEX_FILE = os.path.join(DOWNLOADS_DIR, "_tasks.json")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def is_within(root: str, target: str) -> bool:
    """判断 target 是否位于 root 目录内（防目录穿越）。"""
    root_abs = os.path.abspath(root)
    target_abs = os.path.abspath(target)
    return target_abs == root_abs or target_abs.startswith(root_abs + os.sep)


class Task:
    """一次镜像任务的内存态。"""

    def __init__(self, cfg: CrawlConfig, task_id: str | None = None):
        self.id = task_id or (datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6])
        self.cfg = cfg
        self.status = "pending"          # pending/running/done/error/cancelled
        self.created_at = _now()
        self.started_at: str | None = None
        self.finished_at: str | None = None
        self.error: str | None = None
        self.stats: dict[str, Any] = {}
        self.logs: deque = deque(maxlen=2000)
        self._log_seq = 0
        self.mirror: Mirror | None = None
        self._job: asyncio.Task | None = None

    # ---- 输出目录 ----
    @property
    def out_root(self) -> str:
        return self.cfg.out_root or os.path.join(DOWNLOADS_DIR, self.id)

    def __getitem__(self, key: str):
        return getattr(self, key)

    def info(self, with_logs: bool = False) -> dict:
        data = {
            "id": self.id,
            "start_url": self.cfg.start_url,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error": self.error,
            "out_root": self.out_root,
            "stats": self.stats,
            "config": self.cfg.to_dict(),
            "log_count": self._log_seq,
        }
        if with_logs:
            data["logs"] = list(self.logs)
        return data

    def append_log(self, entry: dict) -> None:
        self.logs.append(entry)
        self._log_seq += 1

    def logs_since(self, seq: int) -> tuple[list[dict], int]:
        """返回自 seq 之后的新日志（用于 SSE 增量推送）。"""
        total = self._log_seq
        logs = list(self.logs)
        if seq >= total:
            return [], total
        return logs[max(0, len(logs) - (total - seq)):], total


class TaskManager:
    """全局任务调度器（单进程内共享）。"""

    def __init__(self) -> None:
        self.tasks: dict[str, Task] = {}
        os.makedirs(DOWNLOADS_DIR, exist_ok=True)
        self._load_index()

    # ---------------- 持久化 ----------------

    def _load_index(self) -> None:
        """重启后恢复历史任务列表（只恢复元数据，不恢复爬取进程）。"""
        if not os.path.isfile(INDEX_FILE):
            return
        try:
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                items = json.load(f)
            for it in items:
                cfg = CrawlConfig(**{k: v for k, v in it.get("config", {}).items()
                                     if k in CrawlConfig.__dataclass_fields__})
                t = Task(cfg, task_id=it["id"])
                t.status = it.get("status", "done")
                if t.status == "running":
                    t.status = "interrupted"
                t.created_at = it.get("created_at", t.created_at)
                t.started_at = it.get("started_at")
                t.finished_at = it.get("finished_at")
                t.error = it.get("error")
                t.stats = it.get("stats", {})
                self.tasks[t.id] = t
        except Exception:                       # noqa: BLE001
            pass

    def _save_index(self) -> None:
        try:
            data = [t.info() for t in sorted(self.tasks.values(), key=lambda x: x.created_at, reverse=True)]
            with open(INDEX_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:                       # noqa: BLE001
            pass

    # ---------------- 任务生命周期 ----------------

    def create(self, params: dict) -> Task:
        start_url = (params.get("url") or "").strip()
        if not start_url:
            raise ValueError("必须提供起始网址")
        if not start_url.startswith(("http://", "https://")):
            start_url = "http://" + start_url

        def _int(key: str, default: int, lo: int, hi: int) -> int:
            try:
                v = int(params.get(key, default))
            except (TypeError, ValueError):
                v = default
            return max(lo, min(hi, v))

        cfg = CrawlConfig(
            start_url=normalize_url(start_url),
            max_depth=_int("max_depth", 3, 0, 20),
            max_pages=_int("max_pages", 300, 1, 2000000),
            max_assets=_int("max_assets", 5000, 0, 500000),
            concurrency=_int("concurrency", 8, 1, 64),
            same_domain=bool(params.get("same_domain", True)),
            asset_scope=params.get("asset_scope", "same_site") if params.get("asset_scope") in ("same_host", "same_site", "any") else "same_site",
            include_assets=bool(params.get("include_assets", True)),
            rewrite_links=bool(params.get("rewrite_links", True)),
            param_mode=params.get("param_mode", "dir") if params.get("param_mode") in ("dir", "hash", "ignore") else "dir",
            extensionless=params.get("extensionless", "index") if params.get("extensionless") in ("index", "html") else "index",
            with_host_dir=bool(params.get("with_host_dir", True)),
            obey_robots=bool(params.get("obey_robots", False)),
            resume=bool(params.get("resume", True)),
            delay=float(params.get("delay", 0) or 0),
            timeout=float(params.get("timeout", 20) or 20),
            retries=_int("retries", 2, 0, 5),
            exclude_patterns=params.get("exclude_patterns") or [],
            include_patterns=params.get("include_patterns") or [],
        )
        task = Task(cfg)
        cfg.out_root = os.path.join(DOWNLOADS_DIR, task.id)
        os.makedirs(cfg.out_root, exist_ok=True)
        self.tasks[task.id] = task
        task.append_log({"t": datetime.now().strftime("%H:%M:%S"), "level": "info",
                         "msg": f"任务已创建：{cfg.start_url}"})
        self._save_index()
        return task

    def start(self, task: Task) -> None:
        if task.status == "running":
            return

        last_save = [0.0]

        def on_event(kind: str, payload: dict) -> None:
            if kind == "log":
                task.append_log(payload)
            elif kind == "progress":
                task.stats = payload
                now = time.time()
                if now - last_save[0] >= 5:      # 节流：每 5 秒把进度写进索引
                    last_save[0] = now
                    self._save_index()
            elif kind == "done":
                task.stats = payload

        mirror = Mirror(task.cfg, on_event=on_event)
        task.mirror = mirror
        task.status = "running"
        task.started_at = _now()
        task.error = None

        async def _runner() -> None:
            try:
                stats = await mirror.run()
                task.stats = stats
                task.status = "cancelled" if task.mirror and task.mirror._stop.is_set() else "done"
            except Exception as exc:            # noqa: BLE001
                task.status = "error"
                task.error = str(exc)
                task.append_log({"t": datetime.now().strftime("%H:%M:%S"),
                                 "level": "error", "msg": f"任务异常终止：{exc}"})
            finally:
                task.finished_at = _now()
                self._save_index()

        task._job = asyncio.create_task(_runner())
        self._save_index()

    def cancel(self, task: Task) -> bool:
        if task.status != "running" or not task.mirror:
            return False
        task.mirror.stop()
        return True

    def delete(self, task_id: str, remove_files: bool = True) -> bool:
        task = self.tasks.get(task_id)
        if not task:
            return False
        if task.status == "running" and task.mirror:
            task.mirror.stop()
        if remove_files and os.path.isdir(task.out_root) and is_within(DOWNLOADS_DIR, task.out_root):
            shutil.rmtree(task.out_root, ignore_errors=True)
        self.tasks.pop(task_id, None)
        self._save_index()
        return True

    def get(self, task_id: str) -> Task | None:
        return self.tasks.get(task_id)

    def list(self) -> list[dict]:
        return [t.info() for t in sorted(self.tasks.values(),
                                         key=lambda x: x.created_at, reverse=True)]

    # ---------------- 文件浏览 ----------------

    def build_tree(self, task: Task, max_entries: int = 20000) -> dict:
        root = task.out_root
        if not os.path.isdir(root):
            return {"name": os.path.basename(root), "type": "dir", "children": [], "size": 0}

        count = 0
        # 单个目录最多枚举多少条。输出目录可能是「按 host 平铺」的单一大目录
        # （实测 youbian 任务约 150 万文件），绝不能对它做全量 scandir + 排序。
        per_dir_scan = 2000

        def walk(path: str, rel: str = "") -> dict:
            nonlocal count
            node = {
                "name": os.path.basename(path) or rel or "root",
                "path": rel,
                "type": "dir",
                "size": 0,
                "children": [],
            }
            # 性能要点（实测教训，勿回退）：
            # 早期写法是 sorted(os.scandir(path), key=lambda e: (not e.is_dir(), ...))
            # —— 先把整个目录枚举成 list、对每条取 is_dir()（一次 stat）、再整体排序；
            # 而 max_entries 的截断写在循环内部，拦不住前面的全量枚举。输出若是一个
            # 「按 host 平铺」的大目录（实测 youbian 任务约 150 万文件），UI 每打开/
            # 切任务调一次 /tree，就把该目录锁住数分钟，爬虫写入被拖死。
            # 现在：scandir 迭代器边扫边截断（最多 per_dir_scan 条），is_dir/大小在
            # 迭代过程中取好；超出上限则给节点打 truncated 标记，UI 可提示「已截断」。
            entries: list = []
            truncated = False
            try:
                with os.scandir(path) as it:
                    for i, e in enumerate(it):
                        if i >= per_dir_scan or count + len(entries) >= max_entries:
                            truncated = True
                            break
                        try:
                            isdir = e.is_dir()
                            sz = 0 if isdir else e.stat().st_size
                        except OSError:
                            isdir, sz = False, 0
                        entries.append(((not isdir, e.name.lower()), e.path, e.name, isdir, sz))
            except OSError:
                return node
            if truncated:
                node["truncated"] = True
            entries.sort(key=lambda t: t[0])
            for _key, epath, ename, isdir, sz in entries:
                if count >= max_entries:
                    break
                r = f"{rel}/{ename}" if rel else ename
                if isdir:
                    child = walk(epath, r)
                    node["size"] += child.get("size", 0)
                    node["children"].append(child)
                else:
                    count += 1
                    node["size"] += sz
                    node["children"].append({
                        "name": ename, "path": r, "type": "file", "size": sz,
                    })
            return node

        return walk(root)

    def resolve_file(self, task: Task, relpath: str) -> str:
        """把请求相对路径解析为真实文件路径（防穿越）。"""
        relpath = (relpath or "").replace("\\", "/").lstrip("/")
        full = os.path.abspath(os.path.join(task.out_root, *[p for p in relpath.split("/") if p]))
        if not is_within(task.out_root, full):
            raise ValueError("非法路径")
        if not os.path.isfile(full):
            raise FileNotFoundError(relpath)
        return full

    def make_zip(self, task: Task) -> str:
        """把任务目录打包为 zip，返回 zip 路径（缓存复用）。"""
        cache_dir = os.path.join(DOWNLOADS_DIR, "_zips")
        os.makedirs(cache_dir, exist_ok=True)
        zip_path = os.path.join(cache_dir, f"{task.id}.zip")
        if os.path.isfile(zip_path) and task.status != "running":
            return zip_path
        tmp = zip_path + ".tmp"
        host = os.path.basename(task.cfg.start_url.split("//")[-1].split("/")[0]) or "site"
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for base, _dirs, files in os.walk(task.out_root):
                for fn in files:
                    full = os.path.join(base, fn)
                    arc = os.path.join(host, os.path.relpath(full, task.out_root))
                    try:
                        zf.write(full, arc.replace("\\", "/"))
                    except OSError:
                        continue
        os.replace(tmp, zip_path)
        return zip_path

    def manifest(self, task: Task) -> dict:
        path = os.path.join(task.out_root, "_mirror_manifest.json")
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:                   # noqa: BLE001
                pass
        return {"files": [], "stats": task.stats}

    def dir_size(self, task: Task) -> int:
        """任务输出目录的总字节数。

        性能要点（实测教训，勿回退）：本函数由 /api/tasks/{id}/tree 直接调用。
        早期实现对输出目录做全量 os.walk + 逐文件 getsize；当输出是「按 host 平铺」
        的单个大目录时（实测 youbian 任务单目录约 150 万文件），一次调用要枚举并
        stat 150 万个文件，耗时以分钟计，期间把该目录锁住，爬虫的写入被拖死
        —— 实测端到端每项约 12 秒、吞吐被压在 2.7 页/秒，且与 concurrency/delay 无关。
        爬虫本身已在 stats["bytes"] 里累计字节数，优先直接用它，零磁盘 IO。
        """
        tracked = int(task.stats.get("bytes") or 0)
        if tracked > 0:
            return tracked

        total = 0
        scanned = 0
        cap = 200_000          # 兜底：无 stats 时最多 stat 20 万个文件，避免再次卡死
        for base, _dirs, files in os.walk(task.out_root):
            for fn in files:
                if scanned >= cap:
                    return total
                scanned += 1
                try:
                    total += os.path.getsize(os.path.join(base, fn))
                except OSError:
                    continue
        return total


manager = TaskManager()
