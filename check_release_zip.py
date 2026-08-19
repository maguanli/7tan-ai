# -*- coding: utf-8 -*-
"""检查安装包 zip 是否包含敏感文件"""
import zipfile, sys, os

def scan_zip(path, label):
    print(f"===== {label}: {os.path.basename(path)} =====")
    if not os.path.exists(path):
        print("  [不存在]")
        return
    size = os.path.getsize(path)
    print(f"  文件大小: {size/1024/1024:.1f} MB")
    z = zipfile.ZipFile(path)
    names = z.namelist()
    print(f"  总条目: {len(names)}")
    # 敏感关键词
    sensitive = []
    for n in names:
        nl = n.lower()
        if any(k in nl for k in [
            '.env', '.db', 'config.yaml', 'secret', 'token', 'password',
            'contract', '身份证', 'phone', 'backups', 'downloads/', 'data/',
            'logs/', 'recordings', '.pem', '.key'
        ]):
            sensitive.append(n)
    if sensitive:
        print(f"  [警告] 发现 {len(sensitive)} 个敏感条目:")
        for s in sensitive[:40]:
            print(f"    - {s}")
    else:
        print("  [安全] 未发现敏感文件")
    # 打印顶层结构
    tops = set()
    for n in names:
        parts = n.split('/')
        if parts and parts[0]:
            tops.add(parts[0])
    print(f"  顶层结构: {sorted(tops)[:20]}")
    z.close()
    print()

if __name__ == '__main__':
    base = r'D:\7tan\7tanAI\dist\release\github'
    for f in ['7tan-web-v1.0.13.zip', '7tan-editor-free-v1.0.13.zip', '7tan-editor-v1.0.13.zip']:
        scan_zip(os.path.join(base, f), f)
