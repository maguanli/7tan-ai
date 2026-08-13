# -*- coding: utf-8 -*-
"""v4: 诊断 www.7tan.com 真实 web 根目录，并上传最新 robot-head-demo.html"""
import base64
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

LOCAL = Path(r"downloads/mobile/robot-head-demo.html")
HOST, PORT, USER = "47.86.169.72", 22, "administrator"
PW = base64.b64decode("aG01NzNpa0VZY2xJRWcjQGtt").decode()

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def main():
    import paramiko
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PW, timeout=30)

    def run(cmd, t=90):
        try:
            _in, out, err = ssh.exec_command(cmd, timeout=t)
            o = out.read().decode("utf-8", "ignore")
            e = err.read().decode("utf-8", "ignore")
            return o.strip(), e.strip()
        except Exception as ex:
            return "", f"EXC {ex}"

    log("=== 1. 找 nginx.exe 位置 ===")
    o, e = run('wmic process where "name=\'nginx.exe\'" get ExecutablePath /value')
    log(o or e or "(无输出)")

    log("=== 2. 找所有 robot-head-demo.html / robot_head_demo.html 副本 ===")
    o, _ = run('dir /s /b D:\\workspace\\*robot*head*demo*.html 2>nul')
    log(o or "(D:\\workspace 无)")
    o, _ = run('dir /s /b C:\\*robot*head*demo*.html 2>nul')
    log(o or "(C: 无)")

    log("=== 3. 找 nginx conf 位置 ===")
    o, _ = run('dir /s /b C:\\nginx\\conf\\*.conf 2>nul')
    log(o or "(C:\\nginx\\conf 无)")

    log("=== 4. 含 7tan 的 server/root 配置 ===")
    o, _ = run('powershell -NoProfile -Command "Get-ChildItem -Path C:\\nginx\\conf -Recurse -Filter *.conf | Select-String -Pattern \'7tan\' -Context 2,6 | ForEach-Object { $_.Path + \':\' + $_.LineNumber + \' | \' + $_.Line.Trim() }"', t=120)
    log(o or "(无匹配)")

    log("=== 5. 含 server_name 7tan 的 root 行 ===")
    o, _ = run('powershell -NoProfile -Command "Get-ChildItem -Path C:\\nginx\\conf -Recurse -Filter *.conf | Select-String -Pattern \'root \' -Context 0,0 | ForEach-Object { $_.Path + \':\' + $_.LineNumber + \' | \' + $_.Line.Trim() }"', t=120)
    log(o or "(无匹配)")

    ssh.close()
    log("诊断完成")

if __name__ == "__main__":
    main()
