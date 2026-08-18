#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
7Tan WEB 版跨平台启动入口（macOS / Linux / 鸿蒙等非 Windows 系统）

用法:
    python3 web_main.py [--host 0.0.0.0] [--port 9900]

说明:
    - 本入口只启动 FastAPI WEB 服务（http://127.0.0.1:9900/），不加载桌面 UI
    - 不依赖任何 Windows 专属库（无 msvcrt / win32 / PyQt6），跨平台可运行
    - Windows 系统请继续使用 main.py --web 或桌面版 exe
"""
import argparse
import os
import sys
from pathlib import Path

# 项目根目录（本文件所在目录）
ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description="7Tan WEB 版（跨平台）")
    ap.add_argument("--host", default="0.0.0.0", help="监听地址（默认 0.0.0.0）")
    ap.add_argument("--port", type=int, default=9900, help="监听端口（默认 9900）")
    args = ap.parse_args()

    # 初始化数据库
    try:
        from src.database.db import init_db
        init_db()
    except Exception as e:
        print(f"[WARN] 数据库初始化失败（可稍后重试）: {e}")

    # 启动调度器（可选，失败不阻塞）
    try:
        from src.config.loader import load_config
        from src.scheduler.scheduler import start_scheduler
        start_scheduler(load_config())
        print("[OK] 调度器已启动")
    except Exception as e:
        print(f"[WARN] 调度器启动跳过: {e}")

    # 加载插件（可选，Windows 专属插件由「平台适配」步骤处理，失败不阻塞）
    try:
        from src.plugins import get_manager
        mgr = get_manager()
        mgr.load_all_installed()
        print("[OK] 插件已加载")
    except Exception as e:
        print(f"[WARN] 插件加载跳过: {e}")

    # 启动 WEB 服务（阻塞）
    from src.web.server import start_server
    print(f"🌐 7Tan WEB 版已启动: http://127.0.0.1:{args.port}/")
    try:
        start_server(host=args.host, port=args.port)
    except KeyboardInterrupt:
        print("👋 WEB 服务已停止")
    except Exception as e:
        print(f"[ERROR] WEB 服务异常退出: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
