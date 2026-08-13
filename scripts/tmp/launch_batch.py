# -*- coding: utf-8 -*-
import subprocess, io, sys, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
# 后台运行批量生成
p = subprocess.Popen([sys.executable, r"batch_gen_frames.py"],
                     cwd=os.getcwd(),
                     stdout=open(r"downloads\fanqie\video\batch_gen.log", "w", encoding="utf-8"),
                     stderr=subprocess.STDOUT,
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
print("batch gen started, pid:", p.pid)
