# -*- coding: utf-8 -*-
import io, sys, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
for f in [r"G:\AI_Video\stable-diffusion-webui\webui.bat", r"G:\AI_Video\stable-diffusion-webui\webui-user.bat"]:
    print("=" * 20, f)
    if os.path.exists(f):
        print(open(f, encoding="utf-8", errors="replace").read()[:2500])
    else:
        print("NOT FOUND")
