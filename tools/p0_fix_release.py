# -*- coding: utf-8 -*-
"""P0 修复：清理调试残留 → 重打包 → 生成 .sig 签名 → 更新 version.json"""
import base64
import hashlib
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"D:\7tan\7tanAI")
RELEASE = ROOT / "dist" / "release"
BUILD_SRC = ROOT / "dist" / "_build" / "src"
PRIV = ROOT / "website" / "config" / "private_key.pem"
PUB = ROOT / "website" / "config" / "public_key.pem"
VER_JSON = ROOT / "website" / "updates" / "version.json"
VERSION = "1.0.3"

# ---------- 1. 清理 _build 调试残留 ----------
print("=" * 60)
print("[1/5] 清理 _build 调试残留")
removed = []
for p in sorted(BUILD_SRC.rglob("*")):
    if not p.is_file():
        continue
    name = p.name
    # 明确的调试/损坏文件
    if "broken" in name or name.startswith(("test_", "_fix", "_check", "_tmp")) or name.endswith((".bak", ".old")):
        p.unlink()
        removed.append(str(p.relative_to(BUILD_SRC)))
        continue
# 清理 __pycache__ / _source_backup 目录
for d in list(BUILD_SRC.rglob("__pycache__")) + list(BUILD_SRC.rglob("_source_backup")):
    shutil.rmtree(d, ignore_errors=True)
    removed.append(str(d.relative_to(BUILD_SRC)) + "/")
print(f"  已清理 {len(removed)} 项:")
for r in removed:
    print(f"    - {r}")

# ---------- 2. 重打包 3 个 release zip ----------
print("=" * 60)
print("[2/5] 重新打包 release zip (package_release.py)")
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
r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
print(r.stdout)
if r.returncode != 0:
    print("[ERROR] 打包失败:", r.stderr)
    sys.exit(1)

# ---------- 3. 校验新 zip（broken 不在 / auth_client.pyd 在） ----------
print("=" * 60)
print("[3/5] 校验新 zip 内容")
import zipfile
ok = True
for zname in ["7tan-editor-free-v1.0.3.zip", "7tan-pro-src-v1.0.3.zip", "7tan-pro-update-v1.0.3.zip"]:
    zp = RELEASE / zname
    if not zp.exists():
        print(f"  [MISS] {zname} 不存在!"); ok = False; continue
    with zipfile.ZipFile(zp) as zf:
        names = zf.namelist()
        broken = [n for n in names if "broken" in n.lower()]
        has_auth = any(n.endswith("security/auth_client.pyd") for n in names)
        has_bak = [n for n in names if n.endswith((".bak", ".old"))]
    print(f"  {zname}: {zp.stat().st_size/1048576:.1f} MB, {len(names)} 文件")
    print(f"    broken 残留: {len(broken)}  | auth_client.pyd: {'OK' if has_auth else 'MISSING!'} | .bak 残留: {len(has_bak)}")
    if broken or not has_auth or has_bak:
        ok = False
if not ok:
    print("[ERROR] zip 校验未通过"); sys.exit(1)

# ---------- 4. 生成 .sig 签名 + 自校验 ----------
print("=" * 60)
print("[4/5] 生成 .sig RSA 签名 (SHA-256 + PKCS1v15)")
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
    # 自校验
    pub.verify(sig, digest, padding.PKCS1v15(), hashes.SHA256())
    md5 = hashlib.md5()
    with open(zp, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            md5.update(c)
    print(f"  {zp.name}")
    print(f"    md5 : {md5.hexdigest()}")
    print(f"    size: {zp.stat().st_size}")
    print(f"    sig : {sig_path.name} ({len(sig_b64)} chars) VERIFY_OK")

# ---------- 5. 更新 version.json（保留远程 1.0.2/1.0.1/1.0.0，新增 1.0.3） ----------
print("=" * 60)
print("[5/5] 更新 version.json")
with open(VER_JSON, encoding="utf-8") as f:
    manifest = json.load(f)

free_zip = RELEASE / "7tan-editor-free-v1.0.3.zip"
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
versions = manifest.get("versions", [])
versions = [v for v in versions if v.get("version") != VERSION]  # 去重
versions.insert(0, new_entry)
manifest["versions"] = versions
with open(VER_JSON, "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)
print(f"  version.json 更新完成，最新版本: {versions[0]['version']}")
print("  versions:", [v["version"] for v in versions])

print("=" * 60)
print("P0 本地修复全部完成 ✅")
print("产物:")
for zp in sorted(RELEASE.glob("*.zip")) + sorted(RELEASE.glob("*.sig")):
    print(f"  - {zp.name} ({zp.stat().st_size} B)")
