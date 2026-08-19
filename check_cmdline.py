import subprocess, time, os

# 先启动一个 Chrome 实例（不带参数，用桌面快捷方式相同方式）
CHROME = None
for root, dirs, files in os.walk(r"D:\\"):
    if "chrome-win" in root and "chrome.exe" in files:
        CHROME = os.path.join(root, "chrome.exe")
        break
    if root.count(os.sep) > 6:
        dirs[:] = []
    if CHROME:
        break

print("CHROME:", repr(CHROME))
p = subprocess.Popen([CHROME])
time.sleep(6)

# 用 wmic 查所有 chrome 进程命令行（含父进程参数）
r = subprocess.run(["wmic", "process", "where", "name='chrome.exe'", "get", "ProcessId,CommandLine", "/format:list"],
                   capture_output=True, text=True, encoding="utf-8", errors="ignore")
out = r.stdout
print("=== chrome 进程命令行 ===")
print(out[:3000])
