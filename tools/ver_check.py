# -*- coding: utf-8 -*-
"""版本号一致性自检：源码 / exe 元数据 / Web 静态页 / 说明书 / 官网清单 是否同一版本

用法: python tools/ver_check.py
退出码: 0 全通过 / 1 有失败
"""
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

fails, oks, infos = [], [], []
SELF = os.path.abspath(__file__)


def chk(name, got, want):
    if got == want:
        oks.append("[PASS] %s: %s" % (name, got))
    else:
        fails.append("[FAIL] %s: 期望 %s 实得 %s" % (name, want, got))


def read(p):
    return io.open(p, encoding="utf-8", errors="ignore").read()


# ── 1) 唯一真源
from src.config.version import APP_VERSION  # noqa: E402

want = APP_VERSION
infos.append("APP_VERSION = %s" % want)

# ── 2) exe 元数据（PyInstaller --version-file）
fv = read(os.path.join(ROOT, "file_version_info.txt"))
m = re.search(r"filevers=\((\d+), (\d+), (\d+)", fv)
chk("file_version_info filevers", ".".join(m.groups()) if m else None, want)
m = re.search(r"prodvers=\((\d+), (\d+), (\d+)", fv)
chk("file_version_info prodvers", ".".join(m.groups()) if m else None, want)
chk("FileVersion", (re.search(r"u'FileVersion', u'([\d.]+)'", fv) or [None, None])[1], want)
chk("ProductVersion", (re.search(r"u'ProductVersion', u'([\d.]+)'", fv) or [None, None])[1], want)

# ── 3) Web 界面底部硬编码（接口失败时的兜底显示）
html = read(os.path.join(ROOT, "src/web/static/index.html"))
m = re.search(r'id="webVersion"[^>]*>7tan\.com V([\d.]+)<', html)
chk("index.html sidebar-version", m.group(1) if m else None, want)

# ── 4) guide.html 示例
gd = read(os.path.join(ROOT, "src/web/static/guide.html"))
m = re.search(r"（以 v([\d.]+) 为例）", gd)
chk("guide.html 示例", m.group(1) if m else None, want)

# ── 5) 说明书两处副本（包内模板 + 线上）
for label, p in (("templates/7Tan使用说明书.html", "templates/7Tan使用说明书.html"),
                 ("website/manual.html", "website/manual.html")):
    s = read(os.path.join(ROOT, p))
    m = re.search(r"<title>7Tan 软件使用说明书 v([\d.]+)", s)
    chk(label + " 标题", m.group(1) if m else None, want)
    m = re.search(r"<span>版本 v([\d.]+)</span>", s)
    chk(label + " 正文版本", m.group(1) if m else None, want)
    chk(label + " 更新记录首行",
        (re.search(r"<tr><td><b>v([\d.]+)</b>", s) or [None, None])[1], want)
    chk(label + " 压缩包名",
        (re.search(r"7tan-editor-free-v([\d.]+)\.zip", s) or [None, None])[1], want)

# ── 6) 官网更新清单：最新条目（打包上传后才会同步，未同步只提示不判失败）
vj = json.loads(read(os.path.join(ROOT, "website/updates/version.json")))
latest = (vj.get("versions") or [{}])[0].get("version")
if latest == want:
    oks.append("[PASS] website/updates/version.json 最新条目: %s" % latest)
else:
    infos.append("[INFO] website/updates/version.json 最新条目仍是 %s"
                 "（需打包出 zip 拿到真实 md5/体积后再追加 %s 条目）" % (latest, want))

# ── 7) src/ 不应残留旧版本号（历史发布脚本、更新记录里的旧号属正常，不扫）
OLD_RE = re.compile(r"1\.0\.(1[0-9]|2[0-2])\b")
SKIP_DIRS = {".git", "__pycache__", "node_modules", "dist", "build", "downloads",
             "website", "data", "research", "7723", "logs", ".venv", "docs"}
hits = []
for root, dirs, files in os.walk(os.path.join(ROOT, "src")):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    for fn in files:
        if not fn.endswith((".py", ".html", ".js", ".txt", ".json", ".yaml")):
            continue
        p = os.path.join(root, fn)
        if os.path.abspath(p) == SELF:
            continue
        try:
            s = read(p)
        except Exception:
            continue
        if OLD_RE.search(s):
            hits.append(os.path.relpath(p, ROOT))
if hits:
    fails.append("[FAIL] 仍残留旧版本号的文件 %d 个: %s" % (len(hits), hits[:10]))
else:
    oks.append("[PASS] src/ 下已无 1.0.22 及更早版本号残留")

print("\n".join(infos))
print("\n".join(oks))
if fails:
    print("\n".join(fails))
print("\n结果: %s  (%d 项通过 / %d 项失败)" % (
    "全部通过" if not fails else "有失败", len(oks), len(fails)))
sys.exit(0 if not fails else 1)
