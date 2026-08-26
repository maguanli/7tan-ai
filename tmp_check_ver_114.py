import win32api

path = r"D:\7tan\7tanAI\dist\7tan-editor\7tan-editor.exe"
info = win32api.GetFileVersionInfo(path, "\\")
ms, ls = info['FileVersionMS'], info['FileVersionLS']
print("FileVersion:", f"{ms>>16}.{ms&0xFFFF}.{ls>>16}.{ls&0xFFFF}")
try:
    t = win32api.GetFileVersionInfo(path, "\\VarFileInfo\\Translation")
    key = f"\\StringFileInfo\\{t[0][0]:04X}{t[0][1]:04X}\\ProductVersion"
    print("ProductVersion:", win32api.GetFileVersionInfo(path, key))
except Exception as e:
    print("ProductVersion read err:", e)
