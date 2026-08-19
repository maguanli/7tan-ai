# -*- coding: utf-8 -*-
"""进一步检查便携版Chrome与启动器"""
import os, json, glob, datetime

print("[1] chrome_launcher.pyw 内容")
p = r"D:\7tan\7tanAI\chrome_launcher.pyw"
if os.path.exists(p):
    with open(p, "r", encoding="utf-8", errors="ignore") as f:
        print(f.read()[:2000])
else:
    print("文件不存在!")

print()
print("[2] 便携版 chrome-win 目录结构")
base = r"D:\用户目录\下载\新建文件夹 123\chrome-win"
if os.path.isdir(base):
    for name in os.listdir(base):
        full = os.path.join(base, name)
        if os.path.isdir(full):
            print(f"  [目录] {name}")
        else:
            try:
                sz = os.path.getsize(full)
                print(f"  [文件] {name} ({sz} bytes)")
            except:
                print(f"  [文件] {name}")
else:
    print("便携版目录不存在:", base)

print()
print("[3] 便携版 chrome-win 内是否有 User Data")
ud = os.path.join(base, "User Data")
if os.path.isdir(ud):
    print("  找到便携版内置 User Data!")
    for name in os.listdir(ud):
        print("   ", name)
else:
    print("  便携版目录内没有 User Data，使用系统默认位置")

print()
print("[4] 系统默认 Google Chrome User Data 下的 Sessions 文件")
ud2 = r"C:\Users\Administrator\AppData\Local\Google\Chrome\User Data"
if os.path.isdir(ud2):
    for prof in ["Default", "Profile 1", "Profile 2", "Profile 3"]:
        sp = os.path.join(ud2, prof, "Sessions")
        if os.path.isdir(sp):
            print(f"  {prof}/Sessions:")
            for f in os.listdir(sp):
                fp = os.path.join(sp, f)
                mt = datetime.datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%Y-%m-%d %H:%M:%S")
                print(f"    {f}  修改时间:{mt}  {os.path.getsize(fp)}B")
        else:
            print(f"  {prof}/Sessions 不存在")

print()
print("[5] 各浏览器 User Data 下 Default 目录的 Session 文件(Last Session)")
for udp in [
    r"C:\Users\Administrator\AppData\Local\Google\Chrome\User Data",
    r"C:\Users\Administrator\AppData\Local\ChromeCore\User Data",
    r"C:\Users\Administrator\AppData\Local\360ChromeX\Chrome\User Data",
    r"C:\Users\Administrator\AppData\Local\Qingniao Chrome\User Data",
]:
    for prof in ["Default"]:
        dp = os.path.join(udp, prof)
        if os.path.isdir(dp):
            for f in ["Last Session", "Last Tabs", "Current Session", "Current Tabs", "First Run"]:
                fp = os.path.join(dp, f)
                if os.path.exists(fp):
                    mt = datetime.datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%m-%d %H:%M")
                    print(f"  {udp} \\ {prof} \\ {f}  时间:{mt}  {os.path.getsize(fp)}B")
                else:
                    print(f"  {udp} \\ {prof} \\ {f}  [无]")
