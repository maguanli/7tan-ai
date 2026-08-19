import zipfile, re, sys

# 检查 web zip 内 index.html / guide.html / version 相关文件的版本号
zip_path = r"D:\7tan\7tanAI\dist\release\7tan-web-v1.0.13.zip"
with zipfile.ZipFile(zip_path) as z:
    hits = []
    for n in z.namelist():
        if not n.endswith(('.html', '.js', '.py', '.json', '.txt', '.md')):
            continue
        if any(k in n.lower() for k in ('version', 'index', 'guide', 'web_main', 'server')):
            try:
                data = z.read(n).decode('utf-8', errors='ignore')
            except Exception:
                continue
            vers = re.findall(r'1\.0\.1[0-9]', data)
            if vers:
                hits.append((n, sorted(set(vers))))
    for n, vs in hits[:40]:
        print(n, '->', vs)
