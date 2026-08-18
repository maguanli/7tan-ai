# -*- coding: utf-8 -*-
"""插件白名单校验 — 6 组功能测试"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, r"D:\7tan\7tanAI")

from src.security.plugin_guard import verify_and_load, load_whitelist, verify_plugin_file

PLUGIN_DIR = Path(r"D:\7tan\7tanAI\data\plugins")
WHITELIST = PLUGIN_DIR / "hashes.json"
results = []

# 1. 白名单加载
wl = load_whitelist(str(WHITELIST))
results.append(("1.白名单加载", "OK(%d个插件)" % len(wl) if wl and len(wl) == 39 else "FAIL len=%d" % (len(wl) if wl else 0)))

# 2. 正常插件校验
pid = "tts_piper"
pkg = PLUGIN_DIR / pid
ok, reason = verify_plugin_file(pid, pkg / "tools.py", str(WHITELIST))
results.append(("2.正常插件校验", "OK(%s)" % reason if ok else "FAIL %s" % reason))

# 3. 篡改拒绝（副本）
tmp = Path(tempfile.mkdtemp())
shutil.copytree(pkg, tmp / "evil")
evil = tmp / "evil" / "tools.py"
content = evil.read_text(encoding="utf-8")
evil.write_text(content + "\n# tampered\n", encoding="utf-8")
ok, reason = verify_plugin_file(pid, evil, str(WHITELIST))
results.append(("3.篡改检测", "OK(拒绝: %s)" % reason if not ok else "FAIL 篡改竟然通过!"))
try:
    verify_and_load(pid, str(tmp / "evil"), str(WHITELIST))
    results.append(("3b.篡改加载", "FAIL 篡改模块被加载!"))
except PermissionError:
    results.append(("3b.篡改加载", "OK (PermissionError 拒绝)"))

# 4. 白名单外放行（远程/自定义插件兼容）
newdir = tmp / "custom_plugin"
newdir.mkdir()
(newdir / "tools.py").write_text("def hello(): return 42\n", encoding="utf-8")
ok, reason = verify_plugin_file("custom_plugin", newdir / "tools.py", str(WHITELIST))
results.append(("4.白名单外放行", "OK(%s)" % reason if ok else "FAIL %s" % reason))
m = verify_and_load("custom_plugin", str(newdir), str(WHITELIST))
results.append(("4b.白名单外加载", "OK" if m and hasattr(m, "hello") and m.hello() == 42 else "FAIL"))

# 5. 签名伪造拒绝
data = json.loads(WHITELIST.read_text(encoding="utf-8"))
data["sig"] = "0" * 64
fake = tmp / "hashes_fake.json"
fake.write_text(json.dumps(data), encoding="utf-8")
wl2 = load_whitelist(str(fake))
results.append(("5.签名伪造拒绝", "OK" if wl2 is None else "FAIL 伪造签名竟然通过!"))

# 6. manager 全流程正常加载
from src.plugins.manager import PluginManager
mgr = PluginManager()
try:
    mgr._load_plugin(pid, str(pkg))
    results.append(("6.manager全流程", "OK (loaded=%s)" % (pid in mgr._loaded_modules)))
except Exception as e:
    results.append(("6.manager全流程", "FAIL %s" % e))

for r in results:
    print(r)
shutil.rmtree(tmp, ignore_errors=True)
