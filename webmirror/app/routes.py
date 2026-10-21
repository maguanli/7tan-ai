"""HTTP 接口：创建/监控/预览/下载镜像任务。"""
from __future__ import annotations

import asyncio
import json
import mimetypes
import os
import time

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from .manager import DOWNLOADS_DIR, manager
from .paths import url_to_relpath

router = APIRouter()

TEXT_EXTS = {".html", ".htm", ".css", ".js", ".json", ".txt", ".xml", ".md",
             ".svg", ".csv", ".log", ".yml", ".yaml", ".ini", ".conf"}


def _get_task(tid: str):
    task = manager.get(tid)
    if not task:
        raise HTTPException(404, f"任务不存在: {tid}")
    return task


# ---------------------------------------------------------------------------
# 任务管理
# ---------------------------------------------------------------------------

@router.get("/api/health")
async def health():
    return {
        "ok": True,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tasks": len(manager.tasks),
        "running": sum(1 for t in manager.tasks.values() if t.status == "running"),
        "downloads_dir": DOWNLOADS_DIR,
    }


@router.post("/api/tasks")
async def create_tasks(payload: dict):
    """创建并立即启动镜像任务。url 字段支持多行（每行一个网址）。"""
    raw = (payload.get("url") or "").strip()
    if not raw:
        raise HTTPException(400, "请填写起始网址")
    urls = [u.strip() for u in raw.replace(",", "\n").splitlines() if u.strip()]
    if not urls:
        raise HTTPException(400, "请填写起始网址")

    created = []
    for u in urls[:20]:                       # 单次最多 20 个站点
        params = dict(payload)
        params["url"] = u
        try:
            task = manager.create(params)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        manager.start(task)
        created.append(task.info())
    return {"ok": True, "count": len(created), "tasks": created}


@router.get("/api/tasks")
async def list_tasks():
    return {"ok": True, "tasks": manager.list()}


@router.get("/api/tasks/{tid}")
async def get_task(tid: str):
    task = _get_task(tid)
    return {"ok": True, "task": task.info()}


@router.get("/api/tasks/{tid}/logs")
async def get_logs(tid: str, since: int = 0):
    task = _get_task(tid)
    logs, seq = task.logs_since(since)
    return {"ok": True, "logs": logs, "seq": seq}


@router.post("/api/tasks/{tid}/cancel")
async def cancel_task(tid: str):
    task = _get_task(tid)
    ok = manager.cancel(task)
    return {"ok": ok, "status": task.status}


@router.post("/api/tasks/{tid}/resume")
async def resume_task(tid: str):
    """续抓：用原输出目录重启任务，自动从 _mirror_state.json 接着抓。"""
    task = _get_task(tid)
    if task.status == "running":
        return {"ok": False, "status": task.status, "message": "任务正在运行"}
    manager.start(task)
    return {"ok": True, "status": task.status}


@router.post("/api/tasks/{tid}/delete")
@router.delete("/api/tasks/{tid}")
async def delete_task(tid: str, remove_files: bool = True):
    ok = manager.delete(tid, remove_files=remove_files)
    if not ok:
        raise HTTPException(404, "任务不存在")
    return {"ok": True}


# ---------------------------------------------------------------------------
# 实时进度（SSE）
# ---------------------------------------------------------------------------

@router.get("/api/tasks/{tid}/events")
async def task_events(tid: str, request: Request):
    task = _get_task(tid)

    async def gen():
        seq = 0
        idle_after_end = 0
        # 首帧：全量日志（最多 200 条）
        try:
            while True:
                if await request.is_disconnected():
                    break
                logs, seq = task.logs_since(seq)
                payload = {
                    "type": "state",
                    "task": task.info(),
                    "logs": logs,
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                if task.status in ("done", "error", "cancelled", "interrupted"):
                    idle_after_end += 1
                    if idle_after_end >= 2:
                        yield f"data: {json.dumps({'type': 'end', 'status': task.status})}\n\n"
                        break
                else:
                    idle_after_end = 0
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            return

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# 文件浏览 / 下载
# ---------------------------------------------------------------------------

@router.get("/api/tasks/{tid}/tree")
async def task_tree(tid: str):
    task = _get_task(tid)
    return {"ok": True, "tree": manager.build_tree(task), "size": manager.dir_size(task)}


@router.get("/api/tasks/{tid}/raw")
async def task_raw(tid: str, path: str = Query(...), as_text: bool = False):
    """预览镜像下来的单个文件（HTML/图片等）。"""
    task = _get_task(tid)
    try:
        full = manager.resolve_file(task, path)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, f"文件不存在: {path}") from exc

    ext = os.path.splitext(full)[1].lower()
    if as_text or ext in TEXT_EXTS:
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(500_000)
            return JSONResponse({"ok": True, "path": path, "text": content,
                                 "size": os.path.getsize(full)})
        except OSError as exc:
            raise HTTPException(500, str(exc)) from exc
    return FileResponse(full, filename=os.path.basename(full))


@router.get("/api/tasks/{tid}/serve")
async def task_serve(tid: str, path: str = Query(...)):
    """以内联方式返回文件（供 iframe 预览 HTML 页面）。"""
    task = _get_task(tid)
    try:
        full = manager.resolve_file(task, path)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(404, f"文件不存在: {path}") from exc
    # 显式带上 charset：否则浏览器只能靠页面内的声明去猜，容易乱码
    media_type = mimetypes.guess_type(full)[0] or "application/octet-stream"
    if media_type.startswith("text/") and "charset" not in media_type:
        media_type += "; charset=utf-8"
    return FileResponse(full, media_type=media_type)


@router.get("/mirror/{tid}/{path:path}")
async def mirror_serve(tid: str, path: str):
    """按镜像原本的目录结构对外提供文件。

    预览 iframe 必须走这里：页面内 `../i.293.net/2018/style.css` 这类相对路径
    只有落在「保持原路径」的 URL 下才能正确解析，否则样式/图片全部 404。
    """
    task = _get_task(tid)
    path = (path or "").replace("\\", "/").lstrip("/")
    if not path or path.endswith("/"):
        path += "index.html"
    try:
        full = manager.resolve_file(task, path)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except FileNotFoundError:
        # 目录形式访问（/mirror/<tid>/quhao.293.net）时补 index.html
        try:
            full = manager.resolve_file(task, path.rstrip("/") + "/index.html")
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(404, f"文件不存在: {path}") from exc

    media_type = mimetypes.guess_type(full)[0] or "application/octet-stream"
    if media_type.startswith("text/") and "charset" not in media_type:
        media_type += "; charset=utf-8"
    return FileResponse(full, media_type=media_type)


@router.get("/api/tasks/{tid}/download")
async def task_download(tid: str):
    task = _get_task(tid)
    if task.status == "running":
        raise HTTPException(409, "任务仍在运行中，请等待完成后再打包下载")
    try:
        zip_path = await asyncio.to_thread(manager.make_zip, task)
    except Exception as exc:                  # noqa: BLE001
        raise HTTPException(500, f"打包失败: {exc}") from exc
    host = task.cfg.start_url.split("//")[-1].split("/")[0] or "site"
    return FileResponse(zip_path, filename=f"{host}_{task.id}.zip",
                        media_type="application/zip")


@router.get("/api/tasks/{tid}/manifest")
async def task_manifest(tid: str, limit: int = 500):
    task = _get_task(tid)
    data = manager.manifest(task)
    data["files"] = (data.get("files") or [])[:limit]
    return {"ok": True, "manifest": data}


# ---------------------------------------------------------------------------
# 路径映射预览（不用真抓，直接看 URL 会存到哪）
# ---------------------------------------------------------------------------

@router.get("/api/pathpreview")
async def path_preview(
    url: str,
    param_mode: str = "dir",
    extensionless: str = "index",
    with_host: bool = True,
):
    url = (url or "").strip()
    if not url:
        raise HTTPException(400, "请提供 url")
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
    try:
        rel = url_to_relpath(url, param_mode=param_mode,
                             extensionless=extensionless, with_host=with_host)
    except Exception as exc:                  # noqa: BLE001
        raise HTTPException(400, f"无法解析: {exc}") from exc
    return {"ok": True, "url": url, "relpath": rel}
