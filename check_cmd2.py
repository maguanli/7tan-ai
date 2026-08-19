import subprocess, time, os

# 启动 Chrome
CHROME = None
for root, dirs, files in os.walk(r"D:\\"):
    if "chrome-win" in root and "chrome.exe" in files:
        CHROME = os.path.join(root, "chrome.exe")
        break
    if root.count(os.sep) > 6:
        dirs[:] = []
    if CHROME:
        break

p = subprocess.Popen([CHROME])
time.sleep(6)

# wmic 输出写到文件避免编码问题
r = subprocess.run(["wmic", "process", "where", "name='chrome.exe'", "get", "ProcessId,CommandLine", "/format:list"],
                   capture_output=True)
with open(r"D:\7tan\7tanAI\chrome_cmd.txt", "wb") as f:
    f.write(r.stdout)
print("已保存到 chrome_cmd.txt, 大小:", len(r.stdout))
