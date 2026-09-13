# -*- coding: utf-8 -*-
"""
7Tan Editor 发布脚本（通用版，替代 scripts/tmp/auto_publish_10XX.py 系列）

用法:
    python scripts/publish_release.py 1.0.23            # 正式发布
    python scripts/publish_release.py 1.0.23 --dry-run  # 只校验不上传
    python scripts/publish_release.py                   # 版本号自动取自 src/config/version.py

凭据统一读取 config/deploy.json（可用环境变量 DEPLOY_SERVER_PASSWORD / GITHUB_TOKEN 覆盖）。
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import posixpath
import re
import shutil
import sys
import time
import urllib.request
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
RELEASE = ROOT / "dist" / "release"
PRIV = ROOT / "website" / "config" / "private_key.pem"
PUB = ROOT / "website" / "config" / "public_key.pem"
VER_JSON = ROOT / "website" / "updates" / "version.json"
IDX_HTML = ROOT / "website" / "updates" / "index.html"
MANUAL = ROOT / "website" / "manual.html"
DEPLOY_CFG = ROOT / "config" / "deploy.json"


# ------------------------------------------------------------------ 配置
def load_deploy() -> dict:
    if not DEPLOY_CFG.exists():
        raise SystemExit(f"缺少凭据配置: {DEPLOY_CFG}")
    cfg = json.loads(DEPLOY_CFG.read_text(encoding="utf-8"))
    srv = cfg.get("server") or {}
    if os.environ.get("DEPLOY_SERVER_PASSWORD"):
        srv["password"] = os.environ["DEPLOY_SERVER_PASSWORD"]
    gh = cfg.get("github") or {}
    if os.environ.get("GITHUB_TOKEN"):
        gh["token"] = os.environ["GITHUB_TOKEN"]
    cfg["server"], cfg["github"] = srv, gh
    return cfg


def detect_version() -> str:
    txt = (ROOT / "src" / "config" / "version.py").read_text(encoding="utf-8", errors="ignore")
    m = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', txt)
    if not m:
        raise SystemExit("无法从 src/config/version.py 读取版本号")
    return m.group(1)


CFG = load_deploy()
SRV = CFG["server"]
HOST, PORT, USER = SRV["host"], int(SRV["port"]), SRV["user"]
PW = SRV["password"]
REMOTE_DIR = SRV["remote_dir"]
REMOTE_MANUAL = SRV["remote_manual"]
BASE = CFG.get("website_base", "https://www.7tan.com").rstrip("/")

NEW_VER = next((a for a in sys.argv[1:] if re.fullmatch(r"\d+\.\d+\.\d+", a)), None) or detect_version()
DRY_RUN = "--dry-run" in sys.argv
TS = time.strftime("%Y%m%d_%H%M%S")
BACKUP = RELEASE / f"_server_backup_{TS}"
LOG = RELEASE / f"publish_{NEW_VER.replace('.', '')}_log.txt"


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def fail(msg: str) -> None:
    log(f"FAIL: {msg}")
    sys.exit(1)


def local_md5(p: Path) -> str:
    m = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            m.update(c)
    return m.hexdigest()


def main() -> None:
    log(f"========== v{NEW_VER} 发布开始 ==========")
    log(f"服务器 {HOST}:{PORT} user={USER} pw_len={len(PW)} dry_run={DRY_RUN}")

    zip_v = RELEASE / f"7tan-editor-v{NEW_VER}.zip"
    web_zip = RELEASE / f"7tan-web-v{NEW_VER}.zip"
    free_zip = RELEASE / f"7tan-editor-free-v{NEW_VER}.zip"
    if not zip_v.exists() or not web_zip.exists():
        fail(f"构建产物缺失: editor={zip_v.exists()} web={web_zip.exists()}")

    # ---------- 1. free 包 ----------
    log("[1/8] 生成 free 包（复制 editor zip）")
    if not free_zip.exists():
        shutil.copy2(zip_v, free_zip)
        log(f"  OK 新建 {free_zip.name}")
    else:
        log(f"  OK 已存在 {free_zip.name}")

    # ---------- 2. 签名 ----------
    log("[2/8] 生成 RSA-SHA256 签名")
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    priv = serialization.load_pem_private_key(PRIV.read_bytes(), password=None)
    h = hashlib.sha256()
    with open(free_zip, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    sig_b64 = base64.b64encode(priv.sign(h.digest(), padding.PKCS1v15(), hashes.SHA256())).decode("ascii")
    sig_path = free_zip.with_suffix(free_zip.suffix + ".sig")
    sig_path.write_text(sig_b64, encoding="ascii")
    pub = serialization.load_pem_public_key(PUB.read_bytes())
    pub.verify(base64.b64decode(sig_b64), h.digest(), padding.PKCS1v15(), hashes.SHA256())
    free_md5, web_md5 = local_md5(free_zip), local_md5(web_zip)
    log(f"  OK 验签 PASS {sig_path.name} ({len(sig_b64)}字符)")
    log(f"  free md5={free_md5} size={free_zip.stat().st_size}")
    log(f"  web  md5={web_md5} size={web_zip.stat().st_size}")

    # ---------- 3. version.json ----------
    log("[3/8] 校验 version.json")
    manifest = json.loads(VER_JSON.read_text(encoding="utf-8"))
    ent = [v for v in manifest["versions"] if v["version"] == NEW_VER]
    if not ent:
        fail(f"version.json 缺少 {NEW_VER} 条目")
    ent = ent[0]
    if ent["md5"] != free_md5:
        fail(f"version.json md5 不一致: {ent['md5']} != {free_md5}")
    if ent["size"] != free_zip.stat().st_size:
        fail(f"version.json size 不一致: {ent['size']} != {free_zip.stat().st_size}")
    log(f"  OK {NEW_VER} md5/size 一致；置顶={manifest['versions'][0]['version']}")

    # ---------- 4/5. 网页 ----------
    log("[4/8] 校验 updates/index.html")
    idx = IDX_HTML.read_text(encoding="utf-8")
    for cond, desc in [
        (f"v{NEW_VER}（最新）" in idx, f"下载表含 v{NEW_VER}（最新）"),
        (idx.count("（最新）") == 1, "（最新）唯一"),
        (f"<b>v{NEW_VER}</b>" in idx, f"更新历史含 v{NEW_VER}"),
    ]:
        log(f"  {'OK ' if cond else 'BAD'} {desc}")
    log("[5/8] 校验 manual.html")
    man = MANUAL.read_text(encoding="utf-8")
    for cond, desc in [
        (f"说明书 v{NEW_VER}" in man, f"title v{NEW_VER}"),
        (f"<span>版本 v{NEW_VER}</span>" in man, f"meta v{NEW_VER}"),
        (f"7tan-editor-free-v{NEW_VER}.zip" in man, f"zip 名 v{NEW_VER}"),
    ]:
        log(f"  {'OK ' if cond else 'BAD'} {desc}")

    plan = [
        (free_zip, posixpath.join(REMOTE_DIR, free_zip.name)),
        (sig_path, posixpath.join(REMOTE_DIR, sig_path.name)),
        (web_zip, posixpath.join(REMOTE_DIR, web_zip.name)),
        (VER_JSON, posixpath.join(REMOTE_DIR, "version.json")),
        (IDX_HTML, posixpath.join(REMOTE_DIR, "index.html")),
        (MANUAL, REMOTE_MANUAL),
    ]

    if DRY_RUN:
        log("[DRY-RUN] 跳过上传，计划：")
        for f, r in plan:
            log(f"    {f.name}  ->  {r}  ({f.stat().st_size / 1048576:.1f}MB)")
        log("========== DRY-RUN END ==========")
        return

    # ---------- 6. 上传 ----------
    log("[6/8] 远端备份 -> 上传")
    import paramiko

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PW,
                timeout=30, banner_timeout=30, auth_timeout=30)
    sftp = ssh.open_sftp()
    log("  SSH 认证成功")

    BACKUP.mkdir(parents=True, exist_ok=True)
    for rp, name in [
        (posixpath.join(REMOTE_DIR, "version.json"), "version.json"),
        (posixpath.join(REMOTE_DIR, "index.html"), "index.html"),
        (REMOTE_MANUAL, "manual.html"),
    ]:
        try:
            sftp.get(rp, str(BACKUP / name))
            log(f"  备份 {name} -> {BACKUP.name}/ ({local_md5(BACKUP / name)[:12]})")
        except FileNotFoundError:
            log(f"  备份 {name}: 远端不存在（跳过）")

    for f, remote in plan:
        st = time.time()
        sftp.put(str(f), remote, confirm=False)
        log(f"  OK {f.name} -> {remote} ({f.stat().st_size / 1048576:.1f}MB, {time.time() - st:.1f}s)")

    # ---------- 7. 远程 MD5 ----------
    log("[7/8] 远程 MD5 校验（certutil）")

    def remote_md5(remote_path: str) -> str:
        win_path = remote_path.replace("/", "\\").lstrip("\\")
        _, stdout, _ = ssh.exec_command(f'certutil -hashfile "{win_path}" MD5', timeout=900)
        out = stdout.read().decode("gbk", errors="ignore")
        for line in out.splitlines():
            line = line.strip()
            if len(line) == 32 and all(c in "0123456789abcdefABCDEF" for c in line):
                return line.lower()
        return "?"

    all_ok = True
    for f, remote in plan:
        lm, rm = local_md5(f), remote_md5(remote)
        ok = lm == rm
        all_ok = all_ok and ok
        log(f"  {f.name}: 本地={lm[:16]} 远程={rm[:16]} {'MATCH' if ok else 'DIFF!'}")
    try:
        log(f"  远端 updates 现有 {len(sftp.listdir_attr(REMOTE_DIR))} 项")
    except Exception as e:
        log(f"  列远端目录失败: {e}")

    sftp.close()
    ssh.close()

    # ---------- 8. 公网验证 ----------
    log("[8/8] 公网验证")
    time.sleep(3)
    try:
        req = urllib.request.Request(f"{BASE}/updates/version.json", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
            top = data["versions"][0]
            log(f"  version.json HTTP {resp.status} 最新={top['version']} md5={top['md5'][:16]} size={top['size']}")
            log(f"  公网校验 {'PASS' if top['version'] == NEW_VER and top['md5'] == free_md5 else 'FAIL'}")
    except Exception as e:
        log(f"  version.json 验证失败: {e}")
    try:
        url = f"{BASE}/updates/7tan-editor-free-v{NEW_VER}.zip"
        rq = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}, method="HEAD")
        with urllib.request.urlopen(rq, timeout=60) as resp:
            cl = resp.headers.get("Content-Length")
            same = cl and int(cl) == free_zip.stat().st_size
            log(f"  下载链接 HTTP {resp.status} Content-Length={cl} {'一致' if same else '不一致!'}")
    except Exception as e:
        log(f"  下载链接验证失败: {e}")

    log("========== 发布结束 ==========")
    sys.exit(0 if all_ok else 2)


if __name__ == "__main__":
    main()
