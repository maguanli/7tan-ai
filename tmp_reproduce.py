# -*- coding: utf-8 -*-
"""复现用户场景：解压 web zip 到临时目录，检查启动脚本 + 试运行 web_main.py"""
import os, sys, zipfile, subprocess, shutil
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

TMP = r'D:\7tan\7tanAI\tmp_webtest'
zp = r'D:\7tan\7tanAI\dist\release\7tan-web-v1.0.15.zip'

if os.path.exists(TMP):
    shutil.rmtree(TMP, ignore_errors=True)
os.makedirs(TMP)

print("[1] 解压 web zip 到临时目录...")
with zipfile.ZipFile(zp) as zf:
    zf.extractall(TMP)
print("    解压完成")

print()
print("[2] 根目录内容（用户会看到什么）")
for x in sorted(os.listdir(TMP)):
    full = os.path.join(TMP, x)
    kind = 'DIR ' if os.path.isdir(full) else 'FILE'
    print(f"    [{kind}] {x}")

print()
print("[3] 是否有 Windows 启动脚本？")
has_win = [x for x in os.listdir(TMP) if 'Windows' in x or x.lower().endswith('.bat')]
print("    Windows 启动脚本:", has_win if has_win else "❌ 无！")

print()
print("[4] 尝试用本机 .venv python 启动 web_main.py（观察报错）")
cmd = [r'D:\7tan\7tanAI\.venv\Scripts\python.exe', 'web_main.py', '--port', '9933']
try:
    r = subprocess.run(cmd, cwd=TMP, capture_output=True, text=True, timeout=25)
    print("    returncode:", r.returncode)
    print("    --- stdout ---")
    print(r.stdout[-2000:])
    print("    --- stderr ---")
    print(r.stderr[-3000:])
except subprocess.TimeoutExpired as e:
    print("    ⚠️ 25秒超时（服务可能已启动在跑，属正常，说明启动成功）")
    print("    stdout tail:", (e.stdout or b'')[-1500:].decode('utf-8', 'ignore') if isinstance(e.stdout, bytes) else '')
except Exception as e:
    print("    启动异常:", e)

print()
print("[5] 检查 data/plugins 解压后结构（web 包插件路径是否正常）")
pdir = os.path.join(TMP, 'data', 'plugins')
if os.path.isdir(pdir):
    subs = [x for x in os.listdir(pdir) if os.path.isdir(os.path.join(pdir, x))]
    print(f"    插件目录数: {len(subs)}")
    # 检查 web_search 是否 tools.py 直接存在
    ws = os.path.join(pdir, 'web_search')
    if os.path.isdir(ws):
        print("    web_search 内容:", os.listdir(ws))
else:
    print("    data/plugins 不存在")
print("DONE")
