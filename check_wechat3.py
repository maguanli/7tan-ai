import subprocess

# 检查是否有 WeChat.exe 主进程（不是 WeChatAppEx.exe）
result = subprocess.run(
    'tasklist | findstr /I "WeChat"',
    shell=True,
    capture_output=True, text=True, encoding='gbk', errors='replace'
)
print("--- All WeChat processes ---")
print(result.stdout)

# 也检查 Weixin (新版微信改名为 Weixin)
result2 = subprocess.run(
    'tasklist | findstr /I "Weixin"',
    shell=True,
    capture_output=True, text=True, encoding='gbk', errors='replace'
)
print("--- Weixin processes ---")
print(result2.stdout if result2.stdout else "None found")
