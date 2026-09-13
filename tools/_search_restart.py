import os

ROOT = r"D:\7tan\7tanAI"
targets = ["[restart]", "3080"]
for t in targets:
    print(f"===== 搜索: {t} =====")
    hits = []
    for r, ds, fs in os.walk(ROOT):
        # 跳过无关注目录
        if any(x in r for x in ("\\.git", "node_modules", "\\dist", "\\build", "downloads", "\\data\\", "__pycache__", "\\.venv")):
            continue
        for f in fs:
            if not f.endswith((".py", ".bat", ".js", ".html", ".md", ".json", ".yaml", ".yml", ".txt")):
                continue
            p = os.path.join(r, f)
            try:
                with open(p, encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
                if t in content:
                    hits.append(p)
            except Exception:
                pass
    for h in hits[:30]:
        print(h)
    print(f"共 {len(hits)} 个文件")
    print()
