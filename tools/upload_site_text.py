# -*- coding: utf-8 -*-
"""只上传 3 个文本文件：version.json / index.html / manual.html（修正版）

修正：SFTP 路径是 /D:/... 形式，而远端 Windows PHP 需要 D:\... ，
      两者必须分开转换，否则 php 报 Could not open input file。
"""
import hashlib
import json
import posixpath
import sys
import time
import urllib.request

import paramiko

ROOT = r"D:\7tan\7tanAI"
PHP = r"D:\php\php-8.2.27\php.exe"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

cfg = json.loads(open(ROOT + r"\config\deploy.json", encoding="utf-8").read())
srv = cfg["server"]
HOST, PORT, USER, PW = srv["host"], int(srv["port"]), srv["user"], srv["password"]
RD, RM = srv["remote_dir"], srv["remote_manual"]
BASE = cfg.get("website_base", "https://www.7tan.com").rstrip("/")

PLAN = [
    (ROOT + r"\website\updates\version.json", posixpath.join(RD, "version.json"), "version.json"),
    (ROOT + r"\website\updates\index.html", posixpath.join(RD, "index.html"), "index.html"),
    (ROOT + r"\website\manual.html", RM, "manual.html"),
]
# (url, 必须出现的词, 必须不出现的词)
FORBIDDEN = ["7723 平台", "7723 截图", "WebP 内容", "截图采集"]
HTTP_CHECK = [
    (BASE + "/updates/version.json", ["1.0.23"], FORBIDDEN),
    (BASE + "/updates/index.html", ["1.0.23"], FORBIDDEN),
    (BASE + "/manual.html", ["说明书 v1.0.23"], FORBIDDEN),
]


def to_win(p):
    """SFTP 绝对路径 /D:/x/y -> Windows D:\\x\\y"""
    q = p.lstrip("/").replace("/", "\\")
    return q


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


ok, bad = [], []


def chk(name, cond, detail=""):
    (ok if cond else bad).append(("[PASS] " if cond else "[FAIL] ") + name + ((" " + detail) if detail else ""))


print("服务器 %s:%s user=%s" % (HOST, PORT, USER))
print("remote_dir    = %s" % RD)
print("remote_manual = %s" % RM)
print("php 看到的路径 = %s" % to_win(RM))

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, PORT, USER, PW, timeout=30, look_for_keys=False, allow_agent=False)
sftp = ssh.open_sftp()
chk("SSH/SFTP 连接", True)

# ---------- 1) 远端备份 ----------
ts = time.strftime("%Y%m%d_%H%M%S")
bak = RD + "/_bak_notes_" + ts
try:
    sftp.mkdir(bak)
except Exception:
    pass
for _lp, rp, name in PLAN:
    dst = bak + "/" + name
    tmp = ROOT + "\\data\\_remote_" + name
    try:
        sftp.get(rp, tmp)
        sftp.put(tmp, dst)
        chk("备份 " + name, True, dst + "  (%d B)" % len(open(tmp, "rb").read()))
    except Exception as e:
        chk("备份 " + name, False, repr(e))

# ---------- 2) 上传 ----------
for lp, rp, name in PLAN:
    t0 = time.time()
    sftp.put(lp, rp, confirm=True)
    chk("上传 " + name, True, "%.1fs  %d B" % (time.time() - t0, len(open(lp, "rb").read())))

# ---------- 3) 远端 md5（PHP） ----------
php = (
    '<?php\n'
    'foreach ($argv as $i => $f) { if ($i == 0) continue; echo basename($f), " ",'
    ' (file_exists($f) ? md5_file($f) : "MISSING"), " ",'
    ' (file_exists($f) ? filesize($f) : 0), "\\n"; }\n'
)
local_php = ROOT + "\\tools\\_md5_remote.php"
open(local_php, "w", encoding="utf-8").write(php)
rr = RD + "/_md5_remote.php"
sftp.put(local_php, rr)
cmd = '"%s" "%s" %s' % (PHP, to_win(rr), " ".join('"%s"' % to_win(rp) for _lp, rp, _n in PLAN))
_i, o, e = ssh.exec_command(cmd, timeout=120)
out = o.read().decode("utf-8", "ignore")
err = e.read().decode("utf-8", "ignore")
try:
    sftp.remove(rr)
except Exception:
    pass
print("remote md5 ->", out.strip().replace("\n", " | "))
if err.strip():
    print("php stderr:", err.strip()[:300])

got = {}
for line in out.strip().splitlines():
    parts = line.split()
    if len(parts) >= 3 and parts[2].isdigit():
        got[parts[0]] = (parts[1], int(parts[2]))
chk("PHP 取到 3 个远端文件", len(got) == 3, "实际 %d 个" % len(got))

for lp, _rp, name in PLAN:
    lm, ls = md5f(lp), len(open(lp, "rb").read())
    gm = got.get(name, ("", -1))
    chk("远端 md5 一致 " + name, gm[0] == lm, "%s vs %s" % (gm[0][:12], lm[:12]))
    chk("远端体积一致 " + name, gm[1] == ls, "%d vs %d" % (gm[1], ls))

sftp.close()
ssh.close()

# ---------- 4) HTTP 复核 ----------
for url, required, forbidden in HTTP_CHECK:
    u = url + ("&" if "?" in url else "?") + "_t=%d" % int(time.time())
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache"})
        resp = urllib.request.urlopen(req, timeout=30)
        body = resp.read().decode("utf-8", "ignore")
    except Exception as e:
        chk("HTTP " + url, False, repr(e))
        continue
    miss = [n for n in required if n not in body]
    hit = [n for n in forbidden if n in body]
    detail = []
    if miss:
        detail.append("缺失 " + "、".join(miss))
    if hit:
        detail.append("残留 " + "、".join(hit))
    if not detail:
        detail.append("%d 字，必备项 %d 个全中，禁项 %d 个全无" % (len(body), len(required), len(forbidden)))
    chk("HTTP " + url, not miss and not hit, "；".join(detail))

print("\n".join(ok))
if bad:
    print("\n".join(bad))
print("\n结果: %s (%d 通过 / %d 失败)" % ("全部通过" if not bad else "有失败", len(ok), len(bad)))
sys.exit(0 if not bad else 1)
