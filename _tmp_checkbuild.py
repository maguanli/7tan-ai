import os, subprocess

# 1. 查看 python/cmd 进程
out = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'], capture_output=True, text=True, timeout=20).stdout
procs = [l for l in out.splitlines() if any(k in l.lower() for k in ('python', 'pyinstaller', 'cmd.exe'))]
print("=== 相关进程 ===")
for p in procs[:20]:
    print(p)
if not procs:
    print("(无 python/cmd 进程)")

# 2. 查看构建日志
log = r'D:\7tan\7tanAI\build_log.txt'
print("=== build_log.txt ===")
if os.path.exists(log):
    size = os.path.getsize(log)
    print(f"大小: {size} 字节")
    with open(log, encoding='utf-8', errors='replace') as f:
        content = f.read()
    print(content[-3000:] if content else "(空)")
else:
    print("(文件不存在)")
