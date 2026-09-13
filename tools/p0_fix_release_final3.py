# -*- coding: utf-8 -*-
"""P0 收尾：删源残留 → 重写 pro zip 剔除 auth_client_broken.pyd → 重签名 → manifest"""
import base64
import hashlib
import json
import shutil
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

# ---------- 1. 删除源中的 auth_client_broken.pyd ----------
print("=" * 60)
print("[1/5] 删除 auth_client_broken.pyd 源残留")
for p in [
    ROOT / "src" / "security" / "auth_client_broken.pyd",
    ROOT / "dist" / "_build" / "src" / "security" / "auth_client_broken.pyd",
]:
    if p.exists():
        p.unlink()
        print(f"  [DEL] {p}")
    else:
        print(f"  [SKIP] {p} 不存在")

# ---------- 2. 重写 pro zip：剔除 auth_client_broken.pyd ----------
print("=" * 60)
print("[2/5] 重写 pro zip 剔除 auth_client_broken.pyd")
BANNED = ("security/auth_client_broken.pyd",)

def rewrite(zp: Path):
    tmp = zp.with_suffix(".zip.tmp")
    removed = []
    with zipfile.ZipFile(zp, "r") as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as zout:
        for info in zin.infolist():
            if any(info.filename.endswith(b) for b in BANNED):
                removed.append(info.filename)
                continue
            data = zin.read(info.filename)
            zout.writestr(info, data)
    tmp.replace(zp)
    return removed

for zname in [f"7tan-pro-src-v{VERSION}.zip", f"7tan-pro-update-v{VERSION}.zip"]:
    zp = RELEASE / zname
    removed = rewrite(zp)
    print(f"  {zname}: 剔除 {len(removed)} 个条目 {removed}")

# ---------- 3. 校验（精确规则：仅 auth_client_broken / *.bak / *.old） ----------
print("=" * 60)
print("[3/5] 校验 zip")
ok = True
for zname in [f"7tan-editor-free-v{VERSION}.zip", f"7tan-pro-src-v{VERSION}.zip", f"7tan-pro-update-v{VERSION}.zip"]:
    zp = RELEASE / zname
    with zipfile.ZipFile(zp) as zf:
        names = zf.namelist()
        bad = [n for n in names if n.endswith((".bak", ".old")) or n.endswith("auth_client_broken.pyd") or n.endswith("security/auth_client_broken.pyd")]
        auth = [n for n in names if n.endswith("security/auth_client.pyd")]
        auth_size = zf.getinfo(auth[0]).file_size if auth else 0
    print(f"  {zname}: {zp.stat().st_size/1048576:.1f} MB, {len(names)} 文件 | 真残留={len(bad)} auth_client.pyd={auth_size}B")
    if bad or not auth or auth_size != 262151:
        ok = False
if not ok:
    print("[ERROR] 校验未通过"); sys.exit(1)

# ---------- 4. 重新签名 ----------
print("=" * 60)
print("[4/5] 生成 .sig 签名 + 自校验")
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
    sig = priv.sign(h.digest(), padding.PKCS1v15(), hashes.SHA256())
    sig_b64 = base64.b64encode(sig).decode("ascii")
    zp.with_suffix(zp.suffix + ".sig").write_text(sig_b64, encoding="ascii")
    pub.verify(sig, h.digest(), padding.PKCS1v15(), hashes.SHA256())
    print(f"  [OK] {zp.name} sig VERIFY_OK")

# ---------- 5. version.json ----------
print("=" * 60)
print("[5/5] 更新 version.json")
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
manifest["versions"] = [v for v in manifest.get("versions", []) if v.get("version") != VERSION] + [new_entry]
manifest["versions"] = sorted(manifest["versions"], key=lambda v: [int(x) for x in v["version"].split(".")], reverse=True)
with open(VER_JSON, "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)
print(f"  version.json 完成 | 顺序: {[v['version'] for v in manifest['versions']]}")
print(f"  free md5={md5.hexdigest()} size={free_zip.stat().st_size}")

print("=" * 60)
print("P0 本地全部完成 ✅")
for zp in sorted(RELEASE.glob("*.zip")) + sorted(RELEASE.glob("*.sig")):
    print(f"  - {zp.name} ({zp.stat().st_size} B)")
