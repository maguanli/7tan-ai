# -*- coding: utf-8 -*-
import os, time
p = r"D:\7tan\7tanAI\dist\build_verify_log.txt"
if os.path.exists(p):
    data = open(p, "rb").read()
    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines()
    print("lines:", len(lines), "size:", len(data))
    print("--- last 10 ---")
    for l in lines[-10:]:
        print(l[:150])
else:
    print("日志不存在，构建可能未启动")
