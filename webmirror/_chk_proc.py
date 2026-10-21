# -*- coding: utf-8 -*-
import os, sys, io, datetime, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

print("=== 当前时间 ===")
print(datetime.datetime.now())

print("\n=== 关键文件修改时间 ===")
for f in [r"app\manager.py", r"app\static\index.html"]:
    try:
        print(f, "->", datetime.datetime.fromtimestamp(os.path.getmtime(f)))
    except Exception as e:
        print(f, "ERR", e)

print("\n=== PID 956 进程启动时间 ===")
try:
    import psutil
    p = psutil.Process(956)
    print("name:", p.name())
    print("start:", datetime.datetime.fromtimestamp(p.create_time()))
    print("cmdline:", " ".join(p.cmdline()))
    age = (datetime.datetime.now() - datetime.datetime.fromtimestamp(p.create_time()))
    print("已运行:", age)
except Exception as e:
    print("psutil 不可用:", e)
    out = subprocess.run(["wmic", "process", "where", "processid=956", "get",
                          "creationdate,commandline", "/format:list"],
                         capture_output=True, text=True).stdout
    print(out)
