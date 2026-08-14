# -*- coding: utf-8 -*-
import os, subprocess, sys

p = r"D:\用户目录\下载\新建文件夹 123\recording_20260814_030943.mkv"

try:
    os.remove(p)
    print("DELETED_OK")
    sys.exit(0)
except Exception as e:
    print("STILL_FAIL:", e)

# 列出可疑进程
cmd = ('tasklist /fo csv /nh | findstr /i "chrome explorer dllhost wmp vlc potplayer '
       'obs ffmpeg python pythonw 7tan svchost mspaint photos video editor kdenlive"')
r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
print("=== 可疑进程 ===")
print(r.stdout if r.stdout else "(无匹配)")
print(r.stderr if r.stderr else "")
