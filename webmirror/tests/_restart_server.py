"""重启 WebMirror 服务（8000 端口），让代码改动生效。"""
import os
import subprocess
import sys
import time
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8000
DETACHED = 0x00000008 | 0x00000200          # DETACHED_PROCESS | NEW_PROCESS_GROUP


def listening_pids(port):
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
    pids = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[3] == "LISTENING" and parts[1].endswith(f":{port}"):
            pids.add(parts[4])
    return pids


def main():
    for pid in listening_pids(PORT):
        print(f"停止旧进程 PID={pid}")
        subprocess.run(["taskkill", "/F", "/PID", pid],
                       capture_output=True, text=True)
    time.sleep(1.5)

    log = open(os.path.join(BASE, "_server.log"), "a", encoding="utf-8")
    err = open(os.path.join(BASE, "_server.err"), "a", encoding="utf-8")
    subprocess.Popen([sys.executable, "run.py", "--port", str(PORT)], cwd=BASE,
                     creationflags=DETACHED, stdout=log, stderr=err,
                     stdin=subprocess.DEVNULL)
    print("已重新启动，等待就绪…")

    for _ in range(30):
        time.sleep(1)
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/health",
                                        timeout=3) as r:
                print("就绪:", r.read().decode("utf-8", "replace"))
                return 0
        except Exception as exc:                     # noqa: BLE001
            last = exc
    print("启动失败:", last)
    return 1


if __name__ == "__main__":
    sys.exit(main())
