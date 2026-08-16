# -*- coding: utf-8 -*-
import zipfile

zip_path = r"D:\7tan\7tanAI\dist\release\7tan-editor-v1.0.12.zip"
zf = zipfile.ZipFile(zip_path)
names = zf.namelist()

out = []
out.append("=== 顶层根目录文件 ===")
for n in sorted(names):
    if n.count('/') == 0:
        out.append("  " + n)

out.append("\n=== 含 web_main / start_web / 启动 条目 ===")
for n in sorted(names):
    low = n.lower()
    if 'web_main' in low or 'start_web' in low or '启动' in n or 'web_service' in low or 'server.py' in n:
        out.append("  " + n)

for n in names:
    if '启动网页版服务' in n:
        try:
            data = zf.read(n).decode('utf-8', errors='replace')
        except Exception:
            data = zf.read(n).decode('gbk', errors='replace')
        out.append("\n=== bat 内容: " + n + " ===")
        out.append(data)
        break

# README.txt
for n in names:
    if n.lower() == 'readme.txt':
        try:
            data = zf.read(n).decode('utf-8', errors='replace')
        except Exception:
            data = zf.read(n).decode('gbk', errors='replace')
        out.append("\n=== README.txt ===")
        out.append(data[:1500])
        break

with open(r"D:\7tan\7tanAI\data\zip_inspect_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("OK written", len(out), "lines")
