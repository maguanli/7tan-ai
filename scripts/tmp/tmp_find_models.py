import os

roots = ["G:\\AI_Tools", "G:\\downloads", "G:\\tools"]
patterns = (".safetensors", ".ckpt", ".bin", ".pt")
hits = []
for root in roots:
    if not os.path.exists(root):
        print("SKIP:", root)
        continue
    for dirpath, dirnames, filenames in os.walk(root):
        # 跳过 node_modules 等大目录
        dirnames[:] = [d for d in dirnames if d not in ("node_modules", ".git", "__pycache__", "venv", ".venv")]
        for fn in filenames:
            low = fn.lower()
            if low.endswith(patterns) or "anything" in low or "seedream" in low:
                full = os.path.join(dirpath, fn)
                try:
                    sz = os.path.getsize(full) // (1024*1024)
                except OSError:
                    sz = -1
                hits.append((full, sz))
                print(f"{sz}MB\t{full}")
print("TOTAL:", len(hits))
