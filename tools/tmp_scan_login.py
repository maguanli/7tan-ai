# -*- coding: utf-8 -*-
"""扫描 login_dialog.py 的关闭路径与初始化网络逻辑"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

src = Path("src/ui/login_dialog.py").read_text(encoding="utf-8")
lines = src.splitlines()
for i, ln in enumerate(lines, 1):
    if any(k in ln for k in (".done(", ".close()", "NetworkError", "ServerError",
                             "LoginFailed", "def __init__", "preflight", "检测", "网络",
                             "服务器", "连接")):
        print(f"{i:4d}: {ln.rstrip()[:180]}")
