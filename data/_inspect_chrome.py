# -*- coding: utf-8 -*-
import glob, os, sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

print("=== .bat files in oneclick-publish ===")
for f in glob.glob(r"D:\7tan\dsh-workspace\oneclick-publish\*.bat"):
    print("---", os.path.basename(f), "---")
    try:
        print(open(f, encoding="utf-8", errors="replace").read())
    except Exception as e:
        print("ERR", e)

print("=== chrome.exe candidates ===")
cands = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files\Google\Chrome Beta\Application\chrome.exe",
]
for c in cands:
    print(("FOUND " if os.path.exists(c) else "missing ") + c)

print("=== registry ===")
try:
    import winreg
    for root, key in [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
    ]:
        try:
            with winreg.OpenKey(root, key) as k:
                print("reg:", winreg.QueryValue(k, None))
        except Exception as e:
            print("reg miss:", e)
except Exception as e:
    print("winreg err", e)

print("=== running chrome processes ===")
try:
    import subprocess
    out = subprocess.run(
        ["wmic", "process", "where", "name='chrome.exe'", "get", "ExecutablePath"],
        capture_output=True, text=True, errors="ignore", timeout=30,
    ).stdout
    seen = set()
    for line in out.splitlines():
        line = line.strip()
        if line and line.lower().endswith("chrome.exe"):
            seen.add(line)
    for p in sorted(seen):
        print("proc:", p)
    if not seen:
        print("(no path from wmic)")
except Exception as e:
    print("wmic err", e)
