import os
import glob

# 常见安装路径
candidates = [
    r"C:\Program Files\Tencent\WeChat\WeChat.exe",
    r"C:\Program Files\Tencent\WeChat\Weixin.exe",
    r"C:\Program Files (x86)\Tencent\WeChat\WeChat.exe",
    r"C:\Program Files (x86)\Tencent\WeChat\Weixin.exe",
    r"C:\Program Files\Tencent\Weixin\Weixin.exe",
    r"C:\Program Files (x86)\Tencent\Weixin\Weixin.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Tencent\WeChat\WeChat.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\Tencent\WeChat\Weixin.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tencent\WeChat\WeChat.exe"),
    r"D:\Program Files\Tencent\WeChat\WeChat.exe",
    r"D:\Program Files\Tencent\WeChat\Weixin.exe",
    r"D:\Program Files (x86)\Tencent\WeChat\WeChat.exe",
    r"D:\Program Files (x86)\Tencent\WeChat\Weixin.exe",
    r"D:\Tencent\WeChat\WeChat.exe",
    r"D:\Tencent\WeChat\Weixin.exe",
    r"E:\Program Files\Tencent\WeChat\WeChat.exe",
    r"E:\Program Files\Tencent\WeChat\Weixin.exe",
    r"E:\Tencent\WeChat\WeChat.exe",
]

found = []
for c in candidates:
    if os.path.exists(c):
        found.append(c)

if found:
    print("FOUND:")
    for f in found:
        print(f)
else:
    # 尝试注册表
    import winreg
    keys = [
        (winreg.HKEY_CURRENT_USER, r"Software\Tencent\WeChat"),
        (winreg.HKEY_CURRENT_USER, r"Software\Tencent\Weixin"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Tencent\WeChat"),
    ]
    for hive, key in keys:
        try:
            k = winreg.OpenKey(hive, key)
            try:
                val, _ = winreg.QueryValueEx(k, "InstallPath")
                print("REG:", val)
            except FileNotFoundError:
                pass
            winreg.CloseKey(k)
        except FileNotFoundError:
            pass
    print("NOT_FOUND_IN_COMMON_PATHS")
