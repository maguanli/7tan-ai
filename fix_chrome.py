import os, json, shutil

ud = "C:\\Users\\Administrator\\AppData\\Local\\Google\\Chrome\\User Data"
default_dir = os.path.join(ud, "Default")

def fix_pref(path, backup=True):
    if not os.path.exists(path):
        print("文件不存在:", path)
        return False
    if backup:
        shutil.copy2(path, path + ".bak_fix")
    with open(path, "r", encoding="utf-8", errors="ignore") as fp:
        data = json.load(fp)
    session = data.setdefault("session", {})
    old = session.get("restore_on_startup")
    session["restore_on_startup"] = 2
    session["startup_urls"] = []
    if "startup_urls" in data:
        data["startup_urls"] = []
    # 清掉可能干扰的键
    for k in list(data.keys()):
        if "protected" in k.lower():
            data.pop(k, None)
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)
    print(f"已修复 {os.path.basename(path)}: restore_on_startup {old} -> 2")
    return True

# 1. 主 Preferences
fix_pref(os.path.join(default_dir, "Preferences"))

# 2. Secure Preferences（受保护配置，必须同步改，否则 Chrome 会用这里覆盖）
fix_pref(os.path.join(default_dir, "Secure Preferences"))

# 3. 删除可能引起冲突的 journal 文件
for name in ["Preferences-journal", "Secure Preferences-journal"]:
    p = os.path.join(default_dir, name)
    if os.path.exists(p):
        os.remove(p)
        print("已删除", name)

# 4. 验证
for name in ["Preferences", "Secure Preferences"]:
    p = os.path.join(default_dir, name)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8", errors="ignore") as fp:
            d = json.load(fp)
        print(f"验证 {name}: restore_on_startup =", d.get("session", {}).get("restore_on_startup"))

print("完成！")
