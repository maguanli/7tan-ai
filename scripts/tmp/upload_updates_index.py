# -*- coding: utf-8 -*-
"""上传更新后的 updates/index.html 并公网验证下载页"""
import base64
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

LOCAL = Path(r"D:\7tan\7tanAI\website\updates\index.html")


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main():
    import paramiko

    HOST, PORT, USER = "47.86.169.72", 22, "administrator"
    PW = base64.b64decode("aG01NzNpa0VZY2xJRWcjQGtt").decode()

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PW, timeout=30)
    sftp = ssh.open_sftp()
    log("SSH 连接成功")

    remote = "/D:/workspace/7tan/updates/index.html"
    # 先备份服务器原文件
    bak = remote + ".bak_20260808_2315"
    try:
        sftp.stat(bak)
    except Exception:
        sftp.rename(remote, bak)
        log(f"已备份服务器原文件 -> {bak}")
    sftp.put(str(LOCAL), remote, confirm=True)
    log(f"OK 上传 index.html -> {remote} ({LOCAL.stat().st_size:,}B)")

    # 校验远程内容包含 v1.0.10
    with sftp.open(remote, "r") as f:
        body = f.read().decode("utf-8", errors="ignore")
    has_new = "v1.0.10（最新）" in body and "7tan-editor-free-v1.0.10.zip" in body
    log(f"远程文件包含 v1.0.10 新版本信息: {has_new}")

    sftp.close()
    ssh.close()

    # 公网验证
    import urllib.request
    try:
        req = urllib.request.Request(
            "https://www.7tan.com/updates/index.html", headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            ok = "v1.0.10（最新）" in html and "7tan-editor-free-v1.0.10.zip" in html
            log(f"公网下载页 HTTP {resp.status} | 含 v1.0.10 最新: {ok} | 大小 {len(html)}B")
            if ok:
                idx = html.find("v1.0.10")
                log("公网页面片段: " + html[idx:idx+120].replace("\n", " "))
    except Exception as e:
        log(f"公网访问失败: {e}")

    log("===== DONE =====")


if __name__ == "__main__":
    main()
