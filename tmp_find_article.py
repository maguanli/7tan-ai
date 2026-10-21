import os, sys
roots = [r"D:\7tan", r"D:\用户目录\下载\新建文件夹 123", os.path.expanduser("~")]
hits = []
for root in roots:
    for dirpath, dirnames, filenames in os.walk(root):
        # skip heavy dirs
        low = dirpath.lower()
        if any(x in low for x in ("\\node_modules", "\\.git\\", "chrome-win", "site-packages", "\\venv")):
            dirnames[:] = []
            continue
        for f in filenames:
            fl = f.lower()
            if fl in ("article.md", "公众号版.html", "公众号版-可直接粘贴.html", "build_publish.py", "ubb_content.json") or "公众号" in f:
                hits.append(os.path.join(dirpath, f))
        if len(hits) > 200:
            break
for h in hits:
    try:
        print(os.path.getsize(h), h)
    except Exception:
        print("?", h)
