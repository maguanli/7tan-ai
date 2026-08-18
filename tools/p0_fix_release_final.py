# -*- coding: utf-8 -*-
"""P0 修复（最终版）：
1. 统一 auth_client.pyd = online_verify 修复版（262,151B）
2. 删除 auth_client_broken.pyd 误导残留
3. 重新打包 3 个 release zip
4. 校验 zip 内容
5. 生成 .sig 签名（RSA-SHA256-PKCS1v15）+ 自校验
6. 更新 version.json（1.0.3）
"""
import base64
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(r"D:\7tan\7tanAI")
RELEASE = ROOT / "dist" / "release"
PRIV = ROOT / "website" / "config" / "private_key.pem"
PUB = ROOT / "website" / "config" / "public_key.pem"
VER_JSON = ROOT / "website" / "updates" / "version.json"
VERSION = "1.0.3"
FIXED = ROOT / "backups" / "auth_client_new_onlineverify.pyd"  # 262,151B online_verify 修复版

# ---------- 1. 统一 auth_client.pyd ----------
print("=" * 60)
print("[1/6] 统一 auth_client.pyd = online_verify 修复版")
auth_targets = [
    ROOT / "src" / "security" / "auth_client.pyd",
    ROOT / "dist" / "_build" / "src" / "security" / "auth_client.pyd",
    ROOT / "dist" / "7tan-editor" / "_internal" / "src" / "security" / "auth_client.pyd",
]
for t in auth_targets:
    if t.exists():
        shutil.copy2(FIXED, t)
        print(f"  [OK] {t} -> {t.stat().st_size} B")

# 删除误导命名的 broken
for b in [
    ROOT / "src" / "security" / "auth_client_broken.pyd",
    ROOT / "dist" / "_build" / "src" / "security" / "auth_client_broken.pyd",
]:
    if b.exists():
        b.unlink()
        print(f"  [DEL] {b}")

# ---------- 2. 清理 _build 中调试残留（仅明确调试文件，不碰库） ----------
print("=" * 60)
print("[2/6] 清理 _build 调试残留")
removed = []
for p in sorted((ROOT / "dist" / "_build" / "src").rglob("*")):
    if not p.is_file():
        continue
    n = p.name.lower()
    if n.endswith((".bak", ".old")) or n.startswith(("_fix", "_check", "_tmp")) or "broken" in n:
        p.unlink()
        removed.append(str(p.relative_to(ROOT / "dist" / "_build" / "src")))
for d in list((ROOT / "dist" / "_build" / "src").rglob("__pycache__")) + list((ROOT / "dist" / "_build" / "src").rglob("_source_backup")):
    shutil.rmtree(d, ignore_errors=True)
print(f"  清理 {len(removed)} 项: {removed}")

# ---------- 3. 重新打包 ----------
print("=" * 60)
print("[3/6] 重新打包 release zip")
cmd = [
    sys.executable, str(ROOT / "templates" / "package_release.py"),
    "--uid", "", "--version", VERSION,
    "--out", str(RELEASE),
    "--free-dir", str(ROOT / "dist" / "7tan-editor"),
    "--pro-build", str(ROOT / "dist" / "_build"),
    "--pro-python", str(ROOT / "dist" / "_python"),
    "--rebuild", str(ROOT / "dist" / "rebuild.bat"),
    "--license", str(ROOT / "templates" / "LICENSE.txt"),
]
r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1200)
print(r.stdout)
if r.returncode != 0:
    print("[ERROR] 打包失败:", r.stderr)
    sys.exit(1)

# ---------- 4. 校验 zip ----------
print("=" * 60)
print("[4/6] 校验 zip 内容")
ok = True
for zname in [f"7tan-editor-free-v{VERSION}.zip", f"7tan-pro-src-v{VERSION}.zip", f"7tan-pro-update-v{VERSION}.zip"]:
    zp = RELEASE / zname
    if not zp.exists():
        print(f"  [MISS] {zname}"); ok = False; continue
    with zipfile.ZipFile(zp) as zf:
        names = zf.namelist()
        broken = [n for n in names if "broken" in n.lower()]
        baks = [n for n in names if n.endswith((".bak", ".old"))]
        auth = [n for n in names if n.endswith("security/auth_client.pyd")]
    auth_size = ""
    if auth:
        with zipfile.ZipFile(zp) as zf:
            auth_size = zf.getinfo(auth[0]).file_size
    print(f"  {zname}: {zp.stat().st_size/1048576:.1f} MB, {len(names)} 文件 | broken={len(broken)} bak={len(baks)} auth_client.pyd={auth_size}B")
    if broken or baks or not auth or auth_size != 262151:
        ok = False
if not ok:
    print("[ERROR] zip 校验未通过"); sys.exit(1)

# ---------- 5. 生成 .sig 签名 ----------
print("=" * 60)
print("[5/6] 生成 .sig RSA 签名 (SHA-256 + PKCS1v15)")
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

with open(PRIV, "rb") as f:
    priv = serialization.load_pem_private_key(f.read(), password=None)
with open(PUB, "rb") as f:
    pub = serialization.load_pem_public_key(f.read())

for zp in sorted(RELEASE.glob("*.zip")):
    h = hashlib.sha256()
    with open(zp, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    digest = h.digest()
    sig = priv.sign(digest, padding.PKCS1v15(), hashes.SHA256())
    sig_b64 = base64.b64encode(sig).decode("ascii")
    sig_path = zp.with_suffix(zp.suffix + ".sig")
    sig_path.write_text(sig_b64, encoding="ascii")
    pub.verify(sig, digest, padding.PKCS1v15(), hashes.SHA256())
    print(f"  [OK] {zp.name} sig={len(sig_b64)} chars VERIFY_OK")

# ---------- 6. 更新 version.json ----------
print("=" * 60)
print("[6/6] 更新 version.json")
with open(VER_JSON, encoding="utf-8") as f:
    manifest = json.load(f)

free_zip = RELEASE / f"7tan-editor-free-v{VERSION}.zip"
md5 = hashlib.md5()
with open(free_zip, "rb") as f:
    for c in iter(lambda: f.read(1 << 20), b""):
        md5.update(c)

new_entry = {
    "version": VERSION,
    "channel": "stable",
    "platform": "windows",
    "url": f"https://www.7tan.com/updates/7tan-editor-free-v{VERSION}.zip",
    "md5": md5.hexdigest(),
    "size": free_zip.stat().st_size,
    "notes": "1.0.3 更新：登录协议勾选默认不勾选强制同意(修复未勾选不可见)、侧边栏AI机器人图标、修复登录在线验证失效、安全加固P0-P2(设备指纹绑定/TLS证书固定/更新包RSA签名验证/源码pyd化)、更新包签名机制。",
    "release_date": "2026-08-03",
}
versions = [v for v in manifest.get("versions", []) if v.get("version") != VERSION]
versions.insert(0, new_entry)
manifest["versions"] = versions
with open(VER_JSON, "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)
print(f"  version.json 最新版本: {versions[0]['version']} | md5={md5.hexdigest()} | size={free_zip.stat().st_size}")

print("=" * 60)
print("P0 修复全部完成 ✅")
for zp in sorted(RELEASE.glob("*.zip")) + sorted(RELEASE.glob("*.sig")):
    print(f"  - {zp.name} ({zp.stat().st_size} B)")
