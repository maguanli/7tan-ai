import os, json, shutil

ud = r"C:\Users\Administrator\AppData\Local\Chromium\User Data"
default_dir = os.path.join(ud, "Default")

print("User Data 存在:", os.path.exists(ud))
print("Default 存在:", os.path.exists(default_dir))

if not os.path.exists(default_dir):
    print("Default 目录不存在，列出 User Data 内容:")
    if os.path.exists(ud):
        print(os.listdir(ud))
    exit(1)

def fix_pref(path):
    if not os.path.exists(path):
        print("文件不存在:", path)
        return False
    shutil.copy2(path, path + ".bak_fix")
    with open(path, "r", encoding="utf-8", errors="ignore") as fp:
        data = json.load(fp)
    session = data.setdefault("session", {})
    old = session.get("restore_on_startup")
    session["restore_on_startup"] = 2
    session["startup_urls"] = []
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)
    print(f"已修复 {os.path.basename(path)}: restore_on_startup {old} -> 2")
    return True

# 先杀掉运行中的 Chromium
import subprocess
subprocess.run(["taskkill", "/f", "/im", "chrome.exe"], capture_output=True)
import time
time.sleep(2)

fix_pref(os.path.join(default_dir, "Preferences"))
fix_pref(os.path.join(default_dir, "Secure Preferences"))

# 删除 journal
for name in ["Preferences-journal", "Secure Preferences-journal"]:
    p = os.path.join(default_dir, name)
    if os.path.exists(p):
        os.remove(p)
        print("已删除", name)

# 验证
for name in ["Preferences", "Secure Preferences"]:
    p = os.path.join(default_dir, name)
    with open(p, "r", encoding="utf-8", errors="ignore") as fp:
        d = json.load(fp)
    print(f"验证 {name}: restore_on_startup =", d.get("session", {}).get("restore_on_startup"))
    print(f"  startup_urls =", d.get("session", {}).get("startup_urls"))

print("\n=== 会话文件检查 ===")
sess_dir = os.path.join(default_dir, "Sessions")
if os.path.exists(sess_dir):
    print("Sessions:", os.listdir(sess_dir))
for name in ["Last Session", "Last Tabs", "Current Session", "Current Tabs"]:
    p = os.path.join(default_dir, name)
    print(name, "->", "存在" if os.path.exists(p) else "不存在")

print("完成！")
