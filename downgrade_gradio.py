# -*- coding: utf-8 -*-
import subprocess, io, sys, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
venv_pip = r"G:\AI_Video\stable-diffusion-webui\venv\Scripts\pip.exe"
venv_py = r"G:\AI_Video\stable-diffusion-webui\venv\Scripts\python.exe"

r = subprocess.run([venv_pip, "install", "-q", "gradio==3.41.2"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
print("gradio downgrade rc:", r.returncode)
print((r.stdout or "")[-2000:])
print((r.stderr or "")[-2000:])

# 验证
code = "import gradio as gr; print('gradio', gr.__version__); print('IOComponent:', hasattr(gr.components, 'IOComponent'))"
r2 = subprocess.run([venv_py, "-c", code], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
print("verify rc:", r2.returncode)
print(r2.stdout)
print((r2.stderr or "")[-1500:])
