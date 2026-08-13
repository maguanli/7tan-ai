import os

skip_dirs = {"$RECYCLE.BIN", "System Volume Information", "node_modules", ".git", "__pycache__", "venv", ".venv", "gradle_cache", "QQMusicCache"}
patterns = (".safetensors", ".ckpt")
hits = []
for dirpath, dirnames, filenames in os.walk("G:\\"):
    dirnames[:] = [d for d in dirnames if d not in skip_dirs]
    for fn in filenames:
        low = fn.lower()
        if low.endswith(patterns):
            full = os.path.join(dirpath, fn)
            try:
                sz = os.path.getsize(full) // (1024*1024)
            except OSError:
                sz = -1
            hits.append((full, sz))
            print(f"{sz}MB\t{full}")
print("TOTAL:", len(hits))
