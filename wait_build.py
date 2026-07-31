# -*- coding: utf-8 -*-
"""轮询等待 PyInstaller 构建完成"""
import os, time, subprocess

LOG = r"D:\7tan\7tanAI\dist\build_log.txt"
PYZ = r"D:\7tan\7tanAI\dist\7tan-editor\_internal\PYZ.pyz"
MAX_WAIT = 900  # 15 分钟

def tail(path, n=6):
    with open(path, "rb") as f:
        data = f.read()
    text = data.decode("gbk", errors="replace")
    lines = [l for l in text.splitlines() if l.strip()]
    return lines[-n:]

start = time.time()
last_size = 0
stall_count = 0
while time.time() - start < MAX_WAIT:
    size = os.path.getsize(LOG) if os.path.exists(LOG) else 0
    if size != last_size:
        last_size = size
        stall_count = 0
    else:
        stall_count += 1
    if stall_count >= 12:  # 60 秒无增长
        print(f"[{int(time.time()-start)}s] 日志 60 秒无增长，可能完成或卡住")
        if os.path.exists(PYZ):
            print(">>> PYZ.pyz 已生成！构建完成")
            break
        # 再等一轮看是否真的卡死
    time.sleep(5)
    if (int(time.time() - start)) % 60 == 0 and int(time.time()-start) > 0:
        print(f"[{int(time.time()-start)}s] 等待中... 日志大小 {last_size/1024:.0f}KB")

print("\n=== build_log.txt 末尾 ===")
for line in tail(LOG):
    print(" ", line[:200])

print("\nPYZ.pyz 存在:", os.path.exists(PYZ))
if os.path.exists(PYZ):
    print("PYZ.pyz 大小:", os.path.getsize(PYZ)/1024/1024, "MB")
