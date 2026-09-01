# -*- coding: utf-8 -*-
import subprocess, os, time

chrome_candidates = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]
chrome = next((p for p in chrome_candidates if os.path.exists(p)), None)
if not chrome:
    print("NO_CHROME")
    raise SystemExit(1)

out = r"D:\7tan\7tanAI\downloads\poxi_article\render_check3.png"
if os.path.exists(out):
    os.remove(out)

url = "file:///D:/7tan/7tanAI/downloads/poxi_article/poxi_plugin.html"
cmd = [chrome, "--headless", "--disable-gpu", "--hide-scrollbars",
       "--window-size=750,5600", "--screenshot=" + out, url]
subprocess.run(cmd, capture_output=True, timeout=60)
time.sleep(2)
if os.path.exists(out):
    print("OK", os.path.getsize(out))
else:
    print("FAIL")
