# -*- coding: utf-8 -*-
import subprocess, sys, io, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
webui = r"G:\AI_Video\stable-diffusion-webui"
venv_py = os.path.join(webui, "venv", "Scripts", "python.exe")

# 1) 完整日志
log = os.path.join(webui, "sd_cpu_log.txt")
print("=== sd_cpu_log.txt FULL ===")
if os.path.exists(log):
    print(open(log, encoding="utf-8", errors="replace").read()[:5000])
else:
    print("NO LOG")

# 2) 用 venv python 在 webui 目录模拟 webui 导入链
print("=== simulate import chain ===")
r = subprocess.run([venv_py, "-c",
                    "import sys; sys.path.insert(0, r'%s'); import modules.initialize; print('initialize OK')" % webui],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180, cwd=webui)
print("rc:", r.returncode)
print("stdout:", r.stdout[-1500:])
print("stderr:", r.stderr[-2500:])
