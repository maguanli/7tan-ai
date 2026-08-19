import os

# 便携版 chrome 所在目录
base = r"D:\用户目录\桌面\新建文件夹 123"
print("=== 便携版目录结构 ===")
if os.path.exists(base):
    for f in os.listdir(base):
        p = os.path.join(base, f)
        print(" ", f, "<DIR>" if os.path.isdir(p) else "")
        if os.path.isdir(p) and ("chrome" in f.lower() or "user" in f.lower() or "data" in f.lower()):
            for sub in os.listdir(p)[:20]:
                print("    ", sub)
else:
    print("目录不存在:", base)
    # 尝试搜索 chrome-win
    for root, dirs, files in os.walk(r"D:\用户目录"):
        if "chrome-win" in root:
            print("找到:", root)
            for f in os.listdir(root)[:30]:
                print("   ", f)
            break
