import sys, platform, subprocess
print("Python:", sys.version.split()[0])
print("Platform:", platform.platform())
try:
    import torch
    print("torch:", torch.__version__, "| cuda:", torch.cuda.is_available())
except Exception as e:
    print("torch: NOT INSTALLED ->", e)
for pkg in ["diffusers", "transformers", "accelerate", "safetensors", "PIL", "requests"]:
    try:
        m = __import__(pkg)
        print(pkg, ":", getattr(m, "__version__", "?"))
    except Exception:
        print(pkg, ": NOT INSTALLED")
try:
    import psutil
    print("RAM total GB:", round(psutil.virtual_memory().total/1024**3, 1))
    print("RAM avail GB:", round(psutil.virtual_memory().available/1024**3, 1))
except Exception as e:
    print("psutil:", e)
