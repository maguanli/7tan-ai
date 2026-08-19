import os

base = r"D:\用户目录\桌面\新建文件夹 123"

print("=== 便携版根目录完整列表 ===")
try:
    for f in os.listdir(base):
        p = os.path.join(base, f)
        print(" ", f, "<DIR>" if os.path.isdir(p) else "")
except Exception as e:
    print("列出失败:", e)

print("\n=== 查找 User Data / Preferences ===")
found = []
for root, dirs, files in os.walk(base):
    # 跳过 chrome-win 内部（避免巨量文件）
    if "chrome-win" in root and root != os.path.join(base, "chrome-win"):
        continue
    depth = root[len(base):].count(os.sep)
    if depth > 3:
        continue
    for d in dirs:
        dl = d.lower()
        if "user" in dl or "data" in dl or "profile" in dl or "cache" in dl:
            found.append(os.path.join(root, d))
    if "Preferences" in files:
        found.append("PREFERENCES: " + os.path.join(root, "Preferences"))

for f in found[:40]:
    print(" ", f)
