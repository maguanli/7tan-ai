# -*- coding: utf-8 -*-
"""分离式启动上传子进程（DETACHED_PROCESS，不被调用方清理）"""
import subprocess, sys, os

script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload_asset.py")
target = sys.argv[1]
flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
with open(os.devnull, "wb") as dn:
    p = subprocess.Popen([sys.executable, script, target],
                         stdout=dn, stderr=dn, stdin=dn,
                         creationflags=flags, close_fds=True)
print(f"launched pid={p.pid} target={target}")
