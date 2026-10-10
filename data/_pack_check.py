# -*- coding: utf-8 -*-
import json, os, subprocess, sys, urllib.request
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
EXT = r"D:\7tan\dsh-workspace\oneclick-publish\ext"
KEY = r"D:\7tan\dsh-workspace\oneclick-publish\ext.pem"
CRX = r"D:\7tan\dsh-workspace\oneclick-publish\ext.crx"

print("ext.pem exists:", os.path.exists(KEY), os.path.getsize(KEY) if os.path.exists(KEY) else 0)
print("ext.crx exists:", os.path.exists(CRX), os.path.getsize(CRX) if os.path.exists(CRX) else 0)

print("\n--- pack WITH existing key (the exact fix for the dialog error) ---")
r = subprocess.run(
    [CHROME, "--pack-extension=" + EXT, "--pack-extension-key=" + KEY, "--no-message-box"],
    capture_output=True, text=True, errors="ignore", timeout=180,
)
print("rc =", r.returncode)
print("out:", (r.stdout or "").strip()[:300])
print("err:", (r.stderr or "").strip()[:300])
print("crx after:", os.path.exists(CRX), os.path.getsize(CRX) if os.path.exists(CRX) else 0)

print("\n--- bridge health ---")
try:
    h = urllib.request.urlopen("http://127.0.0.1:8899/api/health", timeout=6).read().decode()
    print(h[:400])
except Exception as e:
    print("health err:", e)

print("\n--- ledger (last 5) ---")
try:
    p = r"D:\7tan\dsh-workspace\oneclick-publish\bridge\ledger.json"
    d = json.load(open(p, encoding="utf-8"))
    rows = d if isinstance(d, list) else d.get("rows", d)
    print(json.dumps(rows[-5:], ensure_ascii=False, indent=2)[:1500])
except Exception as e:
    print("ledger err:", e)
