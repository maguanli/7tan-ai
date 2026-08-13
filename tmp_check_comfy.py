import sys
sys.path.insert(0, r"G:\ai_video_tools\comfyui\ComfyUI_windows_portable\python_embeded\Lib\site-packages")
try:
    import torch
    print("comfy torch:", torch.__version__, "cuda:", torch.cuda.is_available())
except Exception as e:
    print("comfy torch ERROR:", e)
for mod in ["diffusers", "transformers", "safetensors", "numpy", "PIL", "comfy"]:
    try:
        m = __import__(mod)
        print(mod, "OK", getattr(m, "__version__", ""))
    except Exception as e:
        print(mod, "MISSING:", e)
