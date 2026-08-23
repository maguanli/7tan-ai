# -*- coding: utf-8 -*-
"""启动 DeepSeek Harness (dsh) Web 服务（后台，不阻塞）"""
import subprocess
import os

LOG_DIR = r"D:\7tan\7tanAI\logs"
os.makedirs(LOG_DIR, exist_ok=True)

cmd = [
    r"D:\nodejs\node-v22.16.0-win-x64\node.exe",
    r"node_modules\@deepseek-ai\dsh\lib\bin.js",
    "web",
]

out = open(os.path.join(LOG_DIR, "dsh_web.log"), "w", encoding="utf-8")
err = open(os.path.join(LOG_DIR, "dsh_web_err.log"), "w", encoding="utf-8")

p = subprocess.Popen(
    cmd,
    cwd=r"D:\nodejs\node-v22.16.0-win-x64",
    stdout=out,
    stderr=err,
    creationflags=subprocess.CREATE_NO_WINDOW,
)
print("DSH_PID:", p.pid)
