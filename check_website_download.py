# -*- coding: utf-8 -*-
"""检查服务器 download 目录与下载页，判断是否需要更新网站下载内容"""
import base64
import posixpath
import sys
import time
from pathlib import Path

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

    for d in ["/D:/workspace/7tan/download", "/D:/workspace/7tan/updates"]:
        log(f"\n===== {d} =====")
        try:
            for attr in sftp.listdir_attr(d):
                log(f"  {attr.filename}  {attr.st_size:,}B  mtime={time.strftime('%Y-%m-%d %H:%M', time.localtime(attr.st_mtime))}")
        except Exception as e:
            log(f"  listdir 失败: {e}")

    # 读取下载页 HTML（可能 index.html 或 index.php）
    for fname in ["index.html", "index.php"]:
        p = posixpath.join("/D:/workspace/7tan/download", fname)
        try:
            with sftp.open(p, "r") as f:
                body = f.read().decode("utf-8", errors="ignore")
            log(f"\n===== download/{fname} ({len(body)}B) =====")
            # 只打印与下载链接/版本相关的行
            import re
            for line in body.splitlines():
                if re.search(r"7tan-editor|\.zip|download|版本|version|v1\.0", line, re.I):
                    log(f"  {line.strip()[:200]}")
        except Exception as e:
            log(f"  download/{fname} 读取失败: {e}")

    sftp.close()
    ssh.close()
    log("\n===== DONE =====")


if __name__ == "__main__":
    main()
