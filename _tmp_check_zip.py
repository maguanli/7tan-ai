# -*- coding: utf-8 -*-
import paramiko

host="47.86.169.72"; port=22; user="administrator"; pw="hm573ikEYclIEg#@km"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, port=port, username=user, password=pw, timeout=15)
sftp = ssh.open_sftp()

paths = [
    r"D:\workspace\7tan\updates\7tan-pro-src-v1.0.0.zip",
    r"D:\workspace\7tan\7tan-pro-src-v1.0.0.zip",
    r"D:\workspace\7tan\updates\7tan-editor-free-v1.0.0.zip",
    r"D:\workspace\7tan\updates\7tan-pro-update-v1.0.0.zip",
]
for p in paths:
    try:
        st = sftp.stat(p.replace("\\","/"))
        print("%12d bytes  %s" % (st.st_size, p))
    except FileNotFoundError:
        print("%12s  %s" % ("不存在", p))
    except Exception as e:
        print("%12s  %s  -> %s" % ("ERR", p, e))

print("\n=== updates 目录内容 ===")
try:
    for f in sftp.listdir_attr(r"D:\workspace\7tan\updates".replace("\\","/")):
        print("%12d bytes  %s" % (f.st_size, f.filename))
except Exception as e:
    print("listdir failed:", e)

sftp.close(); ssh.close()
print("\nDONE")
