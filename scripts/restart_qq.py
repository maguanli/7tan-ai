# -*- coding: utf-8 -*-
"""重新启动 QQ 并验证窗口状态"""
import subprocess, time, sys
import pygetwindow as gw

QQ_PATH = r'C:\Program Files\Tencent\QQNT\QQ.exe'

print('===== 启动 QQ =====')
proc = subprocess.Popen([QQ_PATH])
print('已启动 QQ，等待窗口出现...')

# 等待最多 30 秒
for i in range(30):
    time.sleep(1)
    wins = [w for w in gw.getAllWindows() if w.title and 'QQ' in w.title and w.visible]
    if wins:
        break

time.sleep(5)

# 检查进程
result = subprocess.run(['tasklist'], capture_output=True, text=True)
qq_lines = [l for l in result.stdout.splitlines() if 'QQ' in l]
print(f'QQ 进程数: {len(qq_lines)}')
for l in qq_lines[:12]:
    print(' ', l.strip())

# 检查窗口
print('\n===== QQ 窗口状态 =====')
wins = [w for w in gw.getAllWindows() if w.title and 'QQ' in w.title]
for w in wins:
    print(f"标题: {w.title!r} | 可见: {w.visible} | 最小化: {w.isMinimized} | 位置: ({w.left},{w.top}) 尺寸: {w.width}x{w.height}")

if not wins:
    print('!! 未找到 QQ 窗口，可能需要登录')
    sys.exit(2)

# 截图确认
import mss
from PIL import Image
with mss.mss() as sct:
    monitor = sct.monitors[0]
    img = sct.grab(monitor)
    pil_img = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
    pil_img.save(r"scripts\qq_after_restart.png")
    print('\n已保存截图: scripts/qq_after_restart.png')
print('DONE')
