# -*- coding: utf-8 -*-
import subprocess, sys, os, time

CWD = r"D:\7tan\7tanAI\webmirror"
DETACHED = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

log = open(os.path.join(CWD, "_server.log"), "w", encoding="utf-8", errors="replace")
err = open(os.path.join(CWD, "_server.err"), "w", encoding="utf-8", errors="replace")

p = subprocess.Popen(
    [sys.executable, "run.py", "--port", "8000"],
    cwd=CWD,
    stdout=log,
    stderr=err,
    creationflags=DETACHED,
    close_fds=True,
)
print("launched pid:", p.pid)
time.sleep(7)

import socket
s = socket.socket()
s.settimeout(3)
try:
    s.connect(("127.0.0.1", 8000))
    print("port 8000: OPEN ✅")
except Exception as e:
    print("port 8000: FAIL", e)
finally:
    s.close()
