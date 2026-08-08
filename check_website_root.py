# -*- coding: utf-8 -*-
"""查看 updates/index.html 与网站根目录，定位下载页"""
import base64
import posixpath
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def log(msg):
    print(msg, flush=True)


def main():
    import paramiko

    HOST, PORT, USER = "47.86.169.72", 22, "administrator"
    PW = base64.b64decode("aG01NzNpa0VZY2xJRWcjQGtt").decode()

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PW, timeout=30)
    sftp = ssh.open_sftp()
    log("SSH 连接成功")

    # 1) updates/index.html 内容
    p = "/D:/workspace/7tan/updates/index.html"
    try:
        with sftp.open(p, "r") as f:
            body = f.read().decode("utf-8", errors="ignore")
        log(f"\n===== updates/index.html ({len(body)}B) =====")
        for line in body.splitlines():
            if re.search(r"7tan-editor|\.zip|download|版本|version|v1\.0|href", line, re.I):
                log(f"  {line.strip()[:250]}")
    except Exception as e:
        log(f"  updates/index.html 读取失败: {e}")

    # 2) 网站根目录结构
    for d in ["/D:/workspace/7tan", "/D:/workspace/7tan/wwwroot", "/D:/workspace/7tan/web", "/D:/workspace/wwwroot"]:
        try:
            items = sftp.listdir(d)
            log(f"\n===== {d} =====")
            for it in items[:60]:
                log(f"  {it}")
            break
        except Exception as e:
            log(f"  {d}: {e}")

    sftp.close()
    ssh.close()
    log("\n===== DONE =====")


if __name__ == "__main__":
    main()
