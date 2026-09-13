"""连续截图观察：登录框 -> 主界面渲染状态"""
import subprocess, time, sys, os
from collections import Counter
from PIL import ImageGrab, Image

EXE = r"D:\7tan\7tanAI\dist\7tan-editor\7tan-editor.exe"
OUTDIR = r"D:\7tan\7tanAI\tools"

def analyze(img, tag):
    img2 = img.convert("RGB")
    w, h = img2.size
    small = img2.resize((160, 90))
    px = list(small.getdata())
    total = len(px)
    counter = Counter(px)
    dark = sum(n for c, n in counter.items() if sum(c) < 120) / total
    light = sum(n for c, n in counter.items() if sum(c) >= 500) / total
    top = counter.most_common(3)
    tops = " ".join(f"#{c[0]:02X}{c[1]:02X}{c[2]:02X}({n/total*100:.0f}%)" for c, n in top)
    verdict = "空白!" if (light > 0.95 or dark > 0.95) else "有内容"
    print(f"[{tag}] dark={dark*100:.0f}% light={light*100:.0f}% distinct={len(counter)} top: {tops} -> {verdict}")

# 检查是否已有 exe 在跑
procs = [p for p in subprocess.check_output(["tasklist"], text=True).splitlines() if "7tan-editor" in p]
print(f"[0] existing procs: {len(procs)}")
for p in procs:
    pid = int(p.split()[1])
    print(f"    kill pid={pid}")
    subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
time.sleep(2)

# 启动 exe
proc = subprocess.Popen([EXE], cwd=r"D:\7tan\7tanAI\dist\7tan-editor")
print(f"[1] exe started pid={proc.pid}")

# 连续截图
for i in range(1, 9):
    time.sleep(6)
    try:
        img = ImageGrab.grab()
        path = os.path.join(OUTDIR, f"shot_{i:02d}.png")
        img.save(path)
        analyze(img, f"t={i*6:2d}s")
    except Exception as e:
        print(f"[t={i*6}s] FAILED: {e}")

print("[done] screenshots saved to tools/shot_*.png")
