# -*- coding: utf-8 -*-
import subprocess, io, sys, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
webui = r"G:\AI_Video\stable-diffusion-webui"
venv_pip = os.path.join(webui, "venv", "Scripts", "pip.exe")
venv_py = os.path.join(webui, "venv", "Scripts", "python.exe")

r = subprocess.run([venv_pip, "install", "-q", "pytorch_lightning==1.9.4"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
print("downgrade rc:", r.returncode)
print((r.stdout or "")[-1200:])
print((r.stderr or "")[-1200:])

# 验证 rank_zero_only 可导入
code = "from pytorch_lightning.utilities.distributed import rank_zero_only; import pytorch_lightning as pl; print('PL version:', pl.__version__); print('rank_zero_only OK')"
r2 = subprocess.run([venv_py, "-c", code], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
print("verify rc:", r2.returncode)
print(r2.stdout)
print(r2.stderr[-1500:] if r2.stderr else "")
