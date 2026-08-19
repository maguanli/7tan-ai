import os

# 从 os.walk 拿到真实路径（避免手动输入名称错误）
target = None
for root, dirs, files in os.walk(r"D:\用户目录"):
    if "chrome-win" in root:
        target = root
        break

print("chrome-win 真实路径:", repr(target))
if target:
    base = os.path.dirname(target)  # 便携版根目录
    print("\n=== 便携版根目录列表 ===")
    for f in os.listdir(base):
        p = os.path.join(base, f)
        print(" ", repr(f), "<DIR>" if os.path.isdir(p) else "")
    print("\n=== 查找 User Data ===")
    for root2, dirs, files in os.walk(base):
        rel = os.path.relpath(root2, base)
        if rel.count(os.sep) > 1:
            continue
        for d in dirs:
            dl = d.lower()
            if "user" in dl or "data" in dl or "profile" in dl:
                print("  DIR:", os.path.join(rel, d))
        if "Preferences" in files:
            print("  PREF:", os.path.join(rel, "Preferences"))
