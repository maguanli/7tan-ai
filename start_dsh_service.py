# -*- coding: utf-8 -*-
"""启动 DeepSeek Harness (dsh) Web 服务（后台，不阻塞）"""
import subprocess
import os

LOG_DIR = r"D:\7tan\7tanAI\logs"
os.makedirs(LOG_DIR, exist_ok=True)

# 【修复 MISSING_CREDENTIAL】从 7Tan 的 .env 读取 DEEPSEEK_API_KEY 注入子进程环境，
# 否则 dsh 独立进程读不到 Key，调用 DeepSeek 会报 no API key for provider route
env = dict(os.environ)
env_path = r"D:\7tan\7tanAI\.env"
if os.path.exists(env_path):
    for line in open(env_path, encoding="utf-8", errors="ignore"):
        line = line.strip()
        if line.startswith("DEEPSEEK_API_KEY="):
            env["DEEPSEEK_API_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")
            break

cmd = [
    r"D:\nodejs\node-v24.19.0-win-x64\node.exe",
    r"node_modules\@deepseek-ai\dsh\lib\bin.js",
    "web",
]

out = open(os.path.join(LOG_DIR, "dsh_web.log"), "w", encoding="utf-8")
err = open(os.path.join(LOG_DIR, "dsh_web_err.log"), "w", encoding="utf-8")

p = subprocess.Popen(
    cmd,
    cwd=r"D:\nodejs\node-v22.16.0-win-x64",
    env=env,
    stdout=out,
    stderr=err,
    creationflags=subprocess.CREATE_NO_WINDOW,
)
print("DSH_PID:", p.pid)
