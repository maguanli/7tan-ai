import os

desk = "C:\\Users\\Administrator\\Desktop"
print("=== 桌面 Chrome 相关文件 ===")
for f in os.listdir(desk):
    if "chrome" in f.lower() or "Chrome" in f or "chrome" in f:
        p = os.path.join(desk, f)
        print("\n[", f, "]")
        # 读取 .bat 内容
        if f.lower().endswith(".bat"):
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as fp:
                    print(fp.read()[:500])
            except Exception as e:
                print("读取失败:", e)
        # 读取 .lnk 目标
        if f.lower().endswith(".lnk"):
            try:
                import win32com.client
                shell = win32com.client.Dispatch("WScript.Shell")
                lnk = shell.CreateShortcut(p)
                print("Target:", lnk.Targetpath)
                print("Args:", lnk.Arguments)
            except Exception as e:
                print("lnk解析失败:", e)
