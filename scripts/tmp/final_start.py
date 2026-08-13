# -*- coding: utf-8 -*-
import subprocess, io, sys, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
webui = r"G:\AI_Video\stable-diffusion-webui"
venv_py = os.path.join(webui, "venv", "Scripts", "python.exe")
venv_pip = os.path.join(webui, "venv", "Scripts", "pip.exe")

r = subprocess.run([venv_pip, "install", "-q", "protobuf"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
print("protobuf install rc:", r.returncode)

logf = open(os.path.join(webui, "sd_direct_log.txt"), "w", encoding="utf-8", errors="replace")
p = subprocess.Popen([venv_py, "launch.py",
                      "--api", "--nowebui", "--skip-install", "--skip-python-version-check",
                      "--skip-torch-cuda-test", "--no-half", "--use-cpu", "all",
                      "--precision", "full", "--skip-prepare-environment"],
                     cwd=webui, stdout=logf, stderr=subprocess.STDOUT,
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
print("webui started, pid:", p.pid)
