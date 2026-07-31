# -*- coding: utf-8 -*-
"""检查 Defender 事件日志 + 完整构建日志中间部分"""
import subprocess

# 1. Defender 事件日志（最近 24h 威胁检测）
print("=== Defender 事件日志 (最近24h) ===")
ps = r"""
$start = (Get-Date).AddHours(-24)
Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-Windows Defender/Operational'; StartTime=$start} -ErrorAction SilentlyContinue |
  Where-Object { $_.Id -in 1116,1117,1000 } |
  Select-Object -First 10 TimeCreated, Id, @{n='Msg';e={$_.Message -replace "`r`n"," "}} |
  Format-List
"""
try:
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, text=True, timeout=40, encoding="utf-8", errors="replace")
    print("stdout:", r.stdout[:4000] if r.stdout else "(无事件)")
    print("stderr:", r.stderr[:300] if r.stderr else "")
except Exception as e:
    print("无法读取事件日志:", e)

# 2. 构建日志中间部分（检查是否有错误）
print("\n=== 构建日志 60-100 行（找错误）===")
with open(r"D:\7tan\7tanAI\dist\rebuild_test_log.txt", "rb") as f:
    data = f.read()
text = data.decode("gbk", errors="replace")
lines = text.splitlines()
for l in lines[60:100]:
    if any(k in l for k in ["ERROR", "WARNING", "FAIL", "Traceback", "Exception", "Building"]):
        print(" ", l)
print("(显示 ERROR/WARNING/Building 相关行)")

# 3. 看是否真的没有 PYZ 相关文件
import os
internal = r"D:\7tan\7tanAI\dist\7tan-editor\_internal"
allf = os.listdir(internal)
print(f"\n=== _internal 共 {len(allf)} 项，是否有 PYZ/archive 相关 ===")
for f in allf:
    if "pyz" in f.lower() or "archive" in f.lower():
        print("  ", f)
print("无 PYZ/archive 相关文件" if not any("pyz" in f.lower() or "archive" in f.lower() for f in allf) else "")
