# -*- coding: utf-8 -*-
import subprocess, io, sys, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
venv_pip = r"G:\AI_Video\stable-diffusion-webui\venv\Scripts\pip.exe"
venv_py = r"G:\AI_Video\stable-diffusion-webui\venv\Scripts\python.exe"

r = subprocess.run([venv_pip, "install", "-q",
                    "transformers==4.36.2", "tokenizers==0.15.2", "huggingface_hub==0.23.4"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
print("rc:", r.returncode)
print((r.stdout or "")[-1500:])
print((r.stderr or "")[-2000:])

code = "import transformers, tokenizers, huggingface_hub; print('transformers', transformers.__version__, '| tokenizers', tokenizers.__version__, '| hub', huggingface_hub.__version__)"
r2 = subprocess.run([venv_py, "-c", code], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
print(r2.stdout, r2.stderr[-800:] if r2.stderr else "")
