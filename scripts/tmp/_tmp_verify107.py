# -*- coding: utf-8 -*-
"""验证 1.0.7 远程文件 MD5 + 公网下载可用性"""
import base64, hashlib, sys, urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LOCAL = r"D:\7tan\7tanAI\dist\release\7tan-editor-free-v1.0.7.zip"

def local_md5(p):
    m = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            m.update(c)
    return m.hexdigest()

print("本地 MD5:", local_md5(LOCAL), "size:", __import__("os").path.getsize(LOCAL))

import paramiko
HOST, PORT, USER = "47.86.169.72", 22, "administrator"
PW = base64.b64decode("aG01NzNpa0VZY2xJRWcjQGtt").decode()
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PW, timeout=30)

# 远程 MD5 - 用 PowerShell 更可靠
cmd = 'powershell -NoProfile -Command "(Get-FileHash -Algorithm MD5 -Path \'D:\\workspace\\7tan\\updates\\7tan-editor-free-v1.0.7.zip\').Hash.ToLower()"'
_, stdout, stderr = ssh.exec_command(cmd, timeout=300)
out = stdout.read().decode("utf-8", errors="ignore").strip()
print("远程 MD5 (PowerShell):", out)

# 远程文件大小
sftp = ssh.open_sftp()
st = sftp.stat("/D:/workspace/7tan/updates/7tan-editor-free-v1.0.7.zip")
print("远程大小:", st.st_size)

# version.json 内容（远程）
with sftp.open("/D:/workspace/7tan/updates/version.json") as f:
    content = f.read().decode("utf-8", errors="ignore")
import json
data = json.loads(content)
top = data["versions"][0]
print("远程 version.json 最新:", json.dumps(top, ensure_ascii=False, indent=2)[:500])
sftp.close()

# 公网下载验证（HEAD 请求）
try:
    req = urllib.request.Request(
        "https://www.7tan.com/updates/7tan-editor-free-v1.0.7.zip",
        method="HEAD",
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        print("公网下载 HTTP:", resp.status, "Content-Length:", resp.headers.get("Content-Length"))
except Exception as e:
    print("公网下载 HEAD 失败:", e)

ssh.close()
print("=== 验证完成 ===")
