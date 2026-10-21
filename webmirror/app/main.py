"""WebMirror — 网页镜像工具（Web 版）应用入口。

启动：
    python run.py                 # 默认 http://127.0.0.1:8000
    python run.py --port 9000
"""
from __future__ import annotations

import os
import sys

from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routes import router

def _static_dir() -> str:
    """静态资源目录。打包后静态文件位于 _MEIPASS/app/static。"""
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    if os.path.isdir(here):
        return here
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        cand = os.path.join(meipass, "app", "static")
        if os.path.isdir(cand):
            return cand
    return here


STATIC_DIR = _static_dir()

app = FastAPI(
    title="WebMirror · 网页镜像工具",
    description="自动抓取整站并按原路径结构保存到本地，可在线浏览与打包下载。",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


WRITE_THREADS = int(os.environ.get("WM_WRITE_THREADS", "64"))


@app.on_event("startup")
async def _setup_io_executor() -> None:
    """放大 asyncio.to_thread 所用的默认线程池。

    背景（实测，勿回退）：
    - 镜像输出集中在「按 host 分目录」的大目录里，实测单目录可达 149 万文件；
    - 在该目录下写单个 7KB 页面（写 .part + os.replace）中位延迟约 1.8 秒，
      最大可超 3.7 秒（杀软/搜索索引/大目录索引在抢文件，也解释了 WinError 32）；
    - asyncio 默认线程池仅 min(32, cpu+4) 个槽位（本机 4 核 → 8 个），
      写盘长尾把槽位占满后，整站吞吐被死死压到 ~3 页/秒，
      且与 concurrency/delay 无关（拉高并发也无效）；
    - 实测把写盘槽位放大后吞吐随之线性上升：8→4.6、32→13.2、64→19.4 文件/秒。

    可用环境变量 WM_WRITE_THREADS 覆盖（默认 64）。
    """
    import asyncio

    loop = asyncio.get_running_loop()
    loop.set_default_executor(
        ThreadPoolExecutor(max_workers=WRITE_THREADS, thread_name_prefix="wm-io")
    )


@app.get("/")
async def index():
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def main() -> None:
    import uvicorn

    host = os.environ.get("WM_HOST", "127.0.0.1")
    port = int(os.environ.get("WM_PORT", "8000"))
    argv = sys.argv[1:]
    for i, a in enumerate(argv):
        if a in ("--host", "-h") and i + 1 < len(argv):
            host = argv[i + 1]
        if a in ("--port", "-p") and i + 1 < len(argv):
            port = int(argv[i + 1])

    print("=" * 62)
    print("  WebMirror · 网页镜像工具")
    print(f"  访问地址: http://{host}:{port}")
    print("  关闭本窗口即退出程序")
    print("=" * 62)

    # 双击 exe 时自动拉起浏览器；源码调试（python run.py）保持原样不弹窗。
    if getattr(sys, "frozen", False):
        import threading
        import webbrowser

        threading.Timer(1.5, lambda: webbrowser.open(f"http://{host}:{port}")).start()

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
