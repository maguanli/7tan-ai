# -*- coding: utf-8 -*-
"""上传带文字输入功能的 robot-head-demo.html 到服务器并公网验证"""
import base64
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

LOCAL = Path(r"D:\7tan\7tanAI\mobile\robot_head_demo.html")
REMOTE = "/D:/workspace/7tan/mobile/robot-head-demo.html"

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

    sftp.put(str(LOCAL), REMOTE, confirm=True)
    log(f"OK 上传 -> {REMOTE} ({LOCAL.stat().st_size:,}B)")

    # 校验远程内容包含文字输入新字段
    with sftp.open(REMOTE, "r") as f:
        body = f.read().decode("utf-8", errors="ignore")
    checks = {
        "textInput 输入框": 'id="textInput"' in body,
        "btnSend 发送按钮": 'id="btnSend"' in body,
        "sendText 函数": "function sendText" in body,
        "回车发送": "key === 'Enter'" in body,
        "inputBar": "inputBar" in body,
    }
    for k, v in checks.items():
        log(f"远程内容 {k}: {'OK' if v else 'MISS'}")

    sftp.close()
    ssh.close()

    # 公网验证
    import urllib.request
    try:
        req = urllib.request.Request(
            "https://www.7tan.com/mobile/robot-head-demo.html",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            ok = 'id="textInput"' in html and 'id="btnSend"' in html
            log(f"公网 HTTP {resp.status} | 含文字输入: {'OK' if ok else 'MISS'} | 大小 {len(html)}B")
    except Exception as e:
        log(f"公网访问失败: {e}")

    log("===== DONE =====")

if __name__ == "__main__":
    main()
