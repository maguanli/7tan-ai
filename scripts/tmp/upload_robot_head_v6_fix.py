# -*- coding: utf-8 -*-
"""v6: 用正确路径 D:\\workspace\\7tan\\mobile\\ 上传最新 robot-head-demo.html 并公网验证"""
import base64
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

LOCAL = Path(r"downloads/mobile/robot-head-demo.html")
REMOTE_DIR = "/D:/workspace/7tan/mobile/"
HOST, PORT, USER = "47.86.169.72", 22, "administrator"
PW = base64.b64decode("aG01NzNpa0VZY2xJRWcjQGtt").decode()

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def main():
    import paramiko
    # 本地文件预检
    body = LOCAL.read_text(encoding="utf-8", errors="ignore")
    pre = {
        "本地大小": LOCAL.stat().st_size,
        "persistCfg(输入即保存)": "persistCfg" in body,
        "camReady(摄像头重试)": "camReady" in body,
        "textInput(文字输入)": 'id="textInput"' in body,
        "无audio:true": "audio: true" not in body,
        "配置迁移": "兼容旧版本配置 key" in body,
    }
    for k, v in pre.items():
        log(f"本地 {k}: {v}")
    if not (pre["persistCfg(输入即保存)"] and pre["camReady(摄像头重试)"]):
        log("!! 本地文件不是最新版，中止"); return

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PW, timeout=30)
    sftp = ssh.open_sftp()

    targets = ["robot-head-demo.html", "robot_head_demo.html"]
    for name in targets:
        remote = REMOTE_DIR + name
        sftp.put(str(LOCAL), remote, confirm=True)
        size = sftp.stat(remote).st_size
        log(f"上传 {name} -> {remote} ({size:,}B)")

    # 远程内容校验（用连字符版）
    with sftp.open(REMOTE_DIR + "robot-head-demo.html", "r") as f:
        rbody = f.read().decode("utf-8", errors="ignore")
    checks = {
        "persistCfg": "persistCfg" in rbody,
        "camReady": "camReady" in rbody,
        "textInput": 'id="textInput"' in rbody,
        "无audio:true": "audio: true" not in rbody,
        "迁移": "兼容旧版本配置 key" in rbody,
        "大小正确": len(rbody.encode("utf-8")) == LOCAL.stat().st_size,
    }
    for k, v in checks.items():
        log(f"远程 {k}: {'OK' if v else 'MISS'}")

    sftp.close()
    ssh.close()

    # 公网验证
    import urllib.request
    for url in ["https://www.7tan.com/mobile/robot-head-demo.html",
                "https://www.7tan.com/mobile/robot_head_demo.html"]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                ok = ("persistCfg" in html and "camReady" in html and 'id="textInput"' in html
                      and "audio: true" not in html)
                log(f"公网 {url} HTTP {resp.status} | 修复生效: {'OK' if ok else 'MISS'} | {len(html)}B")
        except Exception as ex:
            log(f"公网 {url} 失败: {ex}")

if __name__ == "__main__":
    main()
