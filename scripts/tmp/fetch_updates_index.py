# -*- coding: utf-8 -*-
"""下载服务器 updates/index.html 到本地"""
import base64
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

LOCAL = Path(r"D:\7tan\7tanAI\website\updates\index.html")


def main():
    import paramiko

    HOST, PORT, USER = "47.86.169.72", 22, "administrator"
    PW = base64.b64decode("aG01NzNpa0VZY2xJRWcjQGtt").decode()

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PW, timeout=30)
    sftp = ssh.open_sftp()

    remote = "/D:/workspace/7tan/updates/index.html"
    sftp.get(remote, str(LOCAL))
    body = LOCAL.read_text(encoding="utf-8")
    print(f"已下载 {LOCAL} ({len(body)}B)")
    print("===== 前 80 行 =====")
    for i, line in enumerate(body.splitlines()[:80], 1):
        print(f"{i:3d}| {line}")

    sftp.close()
    ssh.close()


if __name__ == "__main__":
    main()
