# -*- coding: utf-8 -*-
"""终极修复：关闭Chrome -> 修改配置 -> 验证 -> 查360清理"""
import os, json, subprocess, time, glob, shutil

UD = r"C:\Users\Administrator\AppData\Local\Google\Chrome\User Data"
DEFAULT = os.path.join(UD, "Default")

print("[1] 结束所有 Chrome 进程...")
r = subprocess.run(["taskkill", "/F", "/IM", "chrome.exe", "/T"],
                   capture_output=True, text=True)
print("   ", r.stdout.strip() or r.stderr.strip())
time.sleep(3)

print("[2] 检查 Chrome 进程是否完全退出")
r2 = subprocess.run(["tasklist", "/FI", "IMAGENAME eq chrome.exe"],
                    capture_output=True, text=True)
print("   ", r2.stdout.strip())

print("[3] 修改 Preferences (restore_on_startup=1)")
pref_path = os.path.join(DEFAULT, "Preferences")
if os.path.exists(pref_path):
    with open(pref_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("session", {})["restore_on_startup"] = 1
    data["session"].pop("startup_urls", None)
    data.setdefault("profile", {})["exit_type"] = "Normal"
    data["profile"]["exited_cleanly"] = True
    with open(pref_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("   Preferences 已写入")

    # 删除可能冲突的 journal
    for jf in glob.glob(pref_path + "*"):
        if jf.endswith(".journal"):
            try:
                os.remove(jf)
                print("   已删除:", os.path.basename(jf))
            except Exception as e:
                print("   删除失败:", e)

    # 验证
    with open(pref_path, "r", encoding="utf-8") as f:
        d2 = json.load(f)
    print("   验证 restore_on_startup =", d2.get("session", {}).get("restore_on_startup"))
else:
    print("   Preferences 不存在!")

print("[4] 检查/创建 Sessions 目录")
sess_dir = os.path.join(DEFAULT, "Sessions")
if not os.path.isdir(sess_dir):
    os.makedirs(sess_dir, exist_ok=True)
    print("   已创建 Sessions 目录")
else:
    files = os.listdir(sess_dir)
    print(f"   Sessions 目录有 {len(files)} 个文件:", files[:5])

print("[5] 检查 360 安全卫士 / 火绒等清理软件")
check_dirs = [
    r"C:\Program Files (x86)\360\360Safe",
    r"C:\Program Files\360\360Safe",
    r"C:\Program Files (x86)\360\360se6",
    r"C:\Program Files (x86)\360\360Chrome",
    r"C:\Program Files\Huorong",
    r"C:\Program Files (x86)\Huorong",
    r"C:\Program Files\Tencent\QQPCMgr",
    r"C:\Program Files (x86)\Tencent\QQPCMgr",
    r"C:\Program Files (x86)\Kingsoft",
]
for d in check_dirs:
    print(f"   {'存在' if os.path.isdir(d) else '无'}  {d}")

print("[6] 检查 360 相关进程")
r3 = subprocess.run(["tasklist"], capture_output=True, text=True)
lines = r3.stdout.splitlines()
for ln in lines:
    low = ln.lower()
    if any(k in low for k in ["360safe", "360tray", "360sd", "huorong", "qqpcmgr", "ksoftmgr"]):
        print("   运行中:", ln.strip())

print("[7] 给桌面所有 Chrome 快捷方式加 --restore-last-session 参数")
try:
    import win32com.client
    shell = win32com.client.Dispatch("WScript.Shell")
    desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
    for lnk in glob.glob(os.path.join(desktop, "*.lnk")):
        try:
            sc = shell.CreateShortcut(lnk)
            t = (sc.TargetPath or "").lower()
            if "chrome" in t:
                args = sc.Arguments or ""
                if "--restore-last-session" not in args:
                    sc.Arguments = (args + " --restore-last-session").strip()
                    sc.Save()
                    print(f"   已加参数: {os.path.basename(lnk)} -> {sc.Arguments}")
                else:
                    print(f"   已有参数: {os.path.basename(lnk)}")
        except Exception as e:
            print(f"   跳过 {lnk}: {e}")
except ImportError:
    print("   无 pywin32，跳过快捷方式修改")

print("\n[8] 完成！所有修复已执行")
