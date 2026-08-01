# -*- coding: utf-8 -*-
"""paramiko SFTP 部署脚本：
1. 上传 website/api/pro/download.php → D:\workspace\7tan\api\pro\download.php
2. 创建 D:\workspace\pro_packages 目录
3. 检查服务器现状（pro_packages 是否存在、downloads.log）
"""
import paramiko, sys, io

HOST = "47.86.169.72"
PORT = 22
USER = "administrator"
PASS = "hm573ikEYclIEg#@km"

LOCAL = r"D:\7tan\7tanAI\website\api\pro\download.php"
REMOTE = r"D:\workspace\7tan\api\pro\download.php"

def main():
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(HOST, PORT, USER, PASS, timeout=20, banner_timeout=20, auth_timeout=20)
    print("[OK] SSH 连接成功:", HOST)

    sftp = cli.open_sftp()

    # 1. 上传 download.php
    sftp.put(LOCAL, REMOTE)
    st = sftp.stat(REMOTE)
    print(f"[OK] 上传 download.php -> {REMOTE} ({st.st_size} 字节)")

    # 2. 创建 pro_packages 目录
    for d in [r"D:\workspace\pro_packages"]:
        try:
            sftp.stat(d)
            print(f"[OK] 目录已存在: {d}")
        except FileNotFoundError:
            sftp.mkdir(d)
            print(f"[OK] 已创建: {d}")

    # 3. 检查远程目录结构
    print("\n=== D:\\workspace 目录 ===")
    for f in sftp.listdir_attr(r"D:\workspace"):
        print(f"  {'DIR ' if f.st_mode & 0o170000 == 0o040000 else 'FILE'} {f.filename}  ({f.st_size})")

    print("\n=== D:\\workspace\\7tan\\api\\pro 目录 ===")
    for f in sftp.listdir_attr(r"D:\workspace\7tan\api\pro"):
        print(f"  {'DIR ' if f.st_mode & 0o170000 == 0o040000 else 'FILE'} {f.filename}  ({f.st_size})")

    sftp.close()
    cli.close()
    print("\n[完成]")

if __name__ == "__main__":
    main()
