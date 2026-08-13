# -*- coding: utf-8 -*-
import subprocess, sys
# 后台启动 stable-diffusion-webui（CPU + API 模式）
bat = r"G:\AI_Video\stable-diffusion-webui\start_cpu.bat"
try:
    p = subprocess.Popen(
        ["cmd", "/c", bat],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    print("webui starting, pid:", p.pid)
except Exception as e:
    print("ERROR:", e)
