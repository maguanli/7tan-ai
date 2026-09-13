"""复现登录框渲染问题：启动exe -> 截图 -> 分析"""
import subprocess, time, sys, os
from collections import Counter

EXE = r"D:\7tan\7tanAI\dist\7tan-editor\7tan-editor.exe"
OUT = r"D:\7tan\7tanAI\tools\shot_login.png"

# 1. 启动 exe
proc = subprocess.Popen([EXE], cwd=r"D:\7tan\7tanAI\dist\7tan-editor")
print(f"[1] exe started pid={proc.pid}")

# 2. 等待登录框出现
time.sleep(28)

# 3. 截屏
try:
    from PIL import ImageGrab
    img = ImageGrab.grab()
    img.save(OUT)
    print(f"[2] screenshot saved: {OUT} {img.size}")
except Exception as e:
    print(f"[2] screenshot FAILED: {e}")
    sys.exit(2)

# 4. 分析
img2 = img.convert("RGB")
w, h = img2.size
small = img2.resize((160, 90))
px = list(small.getdata())
total = len(px)
counter = Counter(px)
top = counter.most_common(6)
print(f"[3] size={w}x{h}, distinct={len(counter)}")
for color, cnt in top:
    print(f"    #{color[0]:02X}{color[1]:02X}{color[2]:02X} : {cnt/total*100:.1f}%")

dark = sum(c for c, n in counter.items() if sum(c) < 120) / total
light = sum(c for c, n in counter.items() if sum(c) >= 500) / total
print(f"[4] dark={dark*100:.1f}% light={light*100:.1f}%")

if light > 0.95:
    print("VERDICT: 几乎全白 -> 窗口空白/未渲染!")
elif dark > 0.95:
    print("VERDICT: 几乎全黑 -> 窗口空白/未渲染!")
else:
    print("VERDICT: 有内容渲染(可能正常)")

# 5. 保留进程运行，供进一步检查
print("[5] exe still running (pid=%d)" % proc.pid)
