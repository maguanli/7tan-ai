import os, sys
print("PYTHON:", sys.version)
try:
    import torch
    print("torch:", torch.__version__, "cuda_available:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("gpu:", torch.cuda.get_device_name(0))
except Exception as e:
    print("torch ERROR:", e)
for mod in ["diffusers", "transformers", "safetensors", "accelerate", "xformers", "PIL", "numpy"]:
    try:
        m = __import__(mod)
        print(f"{mod}: OK", getattr(m, "__version__", ""))
    except Exception as e:
        print(f"{mod}: MISSING ({e})")
print("G_EXISTS:", os.path.exists("G:\\"))
if os.path.exists("G:\\"):
    for entry in os.listdir("G:\\")[:50]:
        print("  G:", entry)
