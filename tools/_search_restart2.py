import os

ROOT = r"D:\7tan\7tanAI"
t = "restart_web"
print(f"===== 搜索引用 restart_web 的文件 =====")
hits = []
for r, ds, fs in os.walk(ROOT):
    if any(x in r for x in ("\\.git", "node_modules", "\\dist", "\\build", "downloads", "\\data\\", "__pycache__", "\\.venv")):
        continue
    for f in fs:
        if not f.endswith((".py", ".bat", ".js", ".html", ".json", ".yaml", ".yml", ".txt", ".md")):
            continue
        p = os.path.join(r, f)
        try:
            with open(p, encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
            if t in content:
                hits.append(p)
        except Exception:
            pass
for h in hits:
    print(h)
print(f"共 {len(hits)} 个文件")
