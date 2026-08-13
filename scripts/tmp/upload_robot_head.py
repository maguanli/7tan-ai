# -*- coding: utf-8 -*-
"""上传修复后的 robot-head-demo.html 到服务器并公网验证"""
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

    # 备份服务器原文件
    bak = REMOTE + ".bak_20260809"
    try:
        sftp.stat(bak)
    except Exception:
        try:
            sftp.rename(REMOTE, bak)
            log(f"已备份服务器原文件 -> {bak}")
        except Exception as e:
            log(f"备份跳过（原文件可能不存在）: {e}")

    sftp.put(str(LOCAL), REMOTE, confirm=True)
    log(f"OK 上传 -> {REMOTE} ({LOCAL.stat().st_size:,}B)")

    # 校验远程内容包含新字段
    with sftp.open(REMOTE, "r") as f:
        body = f.read().decode("utf-8", errors="ignore")
    checks = {
        "visionBase 输入框": 'id="visionBase"' in body,
        "visionKey 输入框": 'id="visionKey"' in body,
        "智谱地址提示": "open.bigmodel.cn/api/paas/v4" in body,
        "vBase 逻辑": "cfg.visionBase || cfg.base" in body,
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
            ok = 'id="visionBase"' in html and "open.bigmodel.cn/api/paas/v4" in html
            log(f"公网 HTTP {resp.status} | 含 visionBase: {'OK' if ok else 'MISS'} | 大小 {len(html)}B")
    except Exception as e:
        log(f"公网访问失败: {e}")

    log("===== DONE =====")

if __name__ == "__main__":
    main()
