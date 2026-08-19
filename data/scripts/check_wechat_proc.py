import subprocess

for name in ["Weixin.exe", "WeChat.exe", "WeixinApp.exe"]:
    out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {name}"],
                         capture_output=True, text=True).stdout
    print(f"=== {name} ===")
    print(out)
    print()
