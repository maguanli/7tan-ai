# -*- coding: utf-8 -*-
"""v5: 查 D:\\nginx\\nginx-1.24.0\\conf 里 www.7tan.com 的 root，并确认各副本大小"""
import base64
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

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

    log("=== 1. nginx conf 文件列表 ===")
    o, _ = run('dir /s /b D:\\nginx\\nginx-1.24.0\\conf\\*.conf')
    log(o or "(无)")

    log("=== 2. 含 7tan 的配置行(带上下文) ===")
    o, _ = run('powershell -NoProfile -Command "Get-ChildItem -Path D:\\nginx\\nginx-1.24.0\\conf -Recurse -Filter *.conf | Select-String -Pattern \'7tan\' -Context 3,10 | ForEach-Object { $_.Path.Replace(\'D:\\\\nginx\\\\nginx-1.24.0\\\\conf\\\\\',\'\') + \':\' + $_.LineNumber + \' >> \' + $_.Line.Trim() }"', t=120)
    log(o or "(无匹配)")

    log("=== 3. 所有 root 指令 ===")
    o, _ = run('powershell -NoProfile -Command "Get-ChildItem -Path D:\\nginx\\nginx-1.24.0\\conf -Recurse -Filter *.conf | Select-String -Pattern \'^\\s*root \' | ForEach-Object { $_.Path.Replace(\'D:\\\\nginx\\\\nginx-1.24.0\\\\conf\\\\\',\'\') + \':\' + $_.LineNumber + \' >> \' + $_.Line.Trim() }"', t=120)
    log(o or "(无匹配)")

    log("=== 4. D:\\workspace\\7tan\\mobile\\robot-head-demo.html 大小 ===")
    o, _ = run('powershell -NoProfile -Command "(Get-Item \'D:\\workspace\\7tan\\mobile\\robot-head-demo.html\').Length"')
    log(o or "(无)")

    log("=== 5. 公网 root 下 mobile 目录查找 ===")
    o, _ = run('dir /s /b D:\\*robot-head-demo.html 2>nul')
    log(o or "(D: 盘仅以上)")

    ssh.close()
    log("诊断完成")

if __name__ == "__main__":
    main()
