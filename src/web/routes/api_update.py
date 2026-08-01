"""
更新 API — 软件在线更新

GET  /api/update/check     — 检查更新（同步）
POST /api/update/download  — 后台下载更新包（返回 task_id）
GET  /api/update/progress  — 查询下载进度
POST /api/update/apply     — 应用更新（返回后 UI 应退出主程序）
"""
import threading
import time

from fastapi import APIRouter, HTTPException
from loguru import logger

from ...core import updater

router = APIRouter(prefix="/api/update", tags=["update"])

# 全局下载任务状态 {task_id: {status, done, total, path, error}}
_tasks: dict[str, dict] = {}
_lock = threading.Lock()


@router.get("/check")
async def check_update():
    """检查更新 → 返回当前版本 / 最新版本信息"""
    info = updater.check_for_update()
    if info is None:
        return {"has_update": False, "current": updater.APP_VERSION, "latest": None}
    if isinstance(info, dict) and "error" in info:
        return {
            "has_update": False,
            "current": updater.APP_VERSION,
            "latest": None,
            "error": info["error"],
        }
    return {
        "has_update": True,
        "current": updater.APP_VERSION,
        "latest": info,
    }


@router.post("/download")
async def download():
    """后台下载最新更新包 → {task_id}"""
    info = updater.check_for_update()
    if not info or not isinstance(info, dict) or "url" not in info:
        raise HTTPException(400, "当前没有可用更新")

    task_id = f"t{int(time.time())}"
    state = {
        "id": task_id,
        "status": "downloading",
        "done": 0,
        "total": 0,
        "path": "",
        "error": "",
    }
    with _lock:
        _tasks[task_id] = state

    def _run():
        try:
            path = updater.download_update(
                info,
                progress_cb=lambda d, t: state.update(done=d, total=t),
            )
            state.update(status="done", path=path)
        except Exception as exc:
            logger.error(f"update download failed: {exc}")
            state.update(status="error", error=str(exc))

    threading.Thread(target=_run, daemon=True, name="updater-dl").start()
    return {"task_id": task_id}


@router.get("/progress")
async def progress(task_id: str = ""):
    """查询下载进度"""
    if not task_id:
        raise HTTPException(400, "缺少 task_id")
    with _lock:
        st = _tasks.get(task_id)
    if not st:
        raise HTTPException(404, "任务不存在")
    return st


@router.post("/apply")
async def apply():
    """应用最近一次已下载完成的更新包 → {ok, message}"""
    with _lock:
        done = [t for t in _tasks.values() if t.get("status") == "done"]
    if not done:
        raise HTTPException(400, "没有已下载完成的更新包")
    st = max(done, key=lambda t: t.get("id", ""))
    ok, msg = updater.apply_update(st["path"])
    if not ok:
        raise HTTPException(500, msg)
    return {"ok": True, "message": msg}
