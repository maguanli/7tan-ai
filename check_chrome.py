# -*- coding: utf-8 -*-
"""实地检查 Chrome 快捷方式与配置位置"""
import os, sys, json, glob

print("=" * 60)
print("[1] 桌面快捷方式检查")
print("=" * 60)
desktop = os.path.join(os.path.expanduser("~"), "Desktop")
if not os.path.isdir(desktop):
    # 尝试公共桌面
    desktop = os.path.join(os.environ.get("PUBLIC", "C:/Users/Public"), "Desktop")
print("桌面路径:", desktop)

try:
    import win32com.client
    shell = win32com.client.Dispatch("WScript.Shell")
    for lnk in glob.glob(os.path.join(desktop, "*.lnk")):
        try:
            sc = shell.CreateShortcut(lnk)
            target = (sc.TargetPath or "").lower()
            if "chrome" in target or "chrome" in lnk.lower():
                print(f"快捷方式: {os.path.basename(lnk)}")
                print(f"  Target : {sc.TargetPath}")
                print(f"  Args   : {sc.Arguments}")
                print(f"  WorkDir: {sc.WorkingDirectory}")
        except Exception as e:
            print(f"  读取失败 {lnk}: {e}")
except ImportError:
    print("无 pywin32，改为解析 .lnk 二进制")
    for lnk in glob.glob(os.path.join(desktop, "*.lnk")):
        if "chrome" in lnk.lower():
            with open(lnk, "rb") as f:
                data = f.read()
            # 提取可打印字符串
            strings = []
            cur = ""
            for b in data:
                if 32 <= b < 127:
                    cur += chr(b)
                else:
                    if len(cur) >= 6:
                        strings.append(cur)
                    cur = ""
            print(f"快捷方式: {os.path.basename(lnk)}")
            for s in strings:
                if "chrome" in s.lower() or ".exe" in s.lower() or "user-data" in s.lower() or "restore" in s.lower():
                    print("  ", s)

print()
print("=" * 60)
print("[2] 用户目录与 Chrome 配置位置")
print("=" * 60)
for u in os.listdir("C:/Users"):
    up = os.path.join("C:/Users", u)
    if not os.path.isdir(up):
        continue
    print(f"用户: {u}")

# 查找所有 Chrome User Data
print("\n[3] 查找所有 Chrome User Data 目录")
found = []
for root in ["C:/Users", "D:/"]:
    for dirpath, dirnames, filenames in os.walk(root):
        # 限制深度，避免太慢
        depth = dirpath[len(root):].count(os.sep)
        if depth > 6:
            dirnames[:] = []
            continue
        base = os.path.basename(dirpath)
        if base == "User Data" and "Chrome" in dirpath:
            found.append(dirpath)
            print("  ", dirpath)
        if base in ("chrome-win", "chrome-win64", "Chrome-bin", "Application") and "chrome" in dirpath.lower():
            print("  [chrome程序目录]", dirpath)
        # 剪枝
        if base in ("Windows", "Program Files (x86)", "System Volume Information", "$Recycle.Bin"):
            dirnames[:] = []

print()
print("=" * 60)
print("[4] 各 User Data 中 Preferences 的启动设置")
print("=" * 60)
for ud in found:
    for prof in ["Default", "Profile 1", "Profile 2"]:
        pref = os.path.join(ud, prof, "Preferences")
        if os.path.exists(pref):
            try:
                with open(pref, "r", encoding="utf-8", errors="ignore") as f:
                    data = json.load(f)
                session = data.get("session", {})
                print(f"  {pref}")
                print(f"    restore_on_startup = {session.get('restore_on_startup')}")
                print(f"    startup_urls       = {session.get('startup_urls')}")
                print(f"    exit_type          = {data.get('profile', {}).get('exit_type')}")
                print(f"    exited_cleanly     = {data.get('profile', {}).get('exited_cleanly')}")
            except Exception as e:
                print(f"  读取失败 {pref}: {e}")

print("\n[5] 环境变量 USERPROFILE:", os.environ.get("USERPROFILE"))
