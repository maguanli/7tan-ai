# -*- coding: utf-8 -*-
"""P0 续跑：重打包 → 重写 free zip 内 auth_client.pyd → 签名 → manifest"""
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
FIXED = ROOT / "backups" / "auth_client_new_onlineverify.pyd"  # 262,151B

# ---------- 1. 重打包 ----------
print("=" * 60)
print("[1/5] 重新打包 release zip")
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
    print("[ERROR] 打包失败:", r.stderr); sys.exit(1)

# ---------- 2. 重写 free zip：替换 auth_client.pyd 为修复版 ----------
print("=" * 60)
print("[2/5] 重写 free zip 内 auth_client.pyd -> 262,151B 修复版")
free_zip = RELEASE / f"7tan-editor-free-v{VERSION}.zip"
fixed_bytes = FIXED.read_bytes()
target_entry = "7tan-editor/_internal/src/security/auth_client.pyd"

tmp = free_zip.with_suffix(".zip.tmp")
with zipfile.ZipFile(free_zip, "r") as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as zout:
    for info in zin.infolist():
        data = zin.read(info.filename)
        if info.filename == target_entry:
            new_info = zipfile.ZipInfo(info.filename, date_time=(2026, 8, 3, 0, 0, 0))
            new_info.compress_type = zipfile.ZIP_DEFLATED
            zout.writestr(new_info, fixed_bytes)
            print(f"  [REPLACED] {target_entry} -> {len(fixed_bytes)} B")
        else:
            zout.writestr(info, data)
tmp.replace(free_zip)
print("  free zip 重写完成")

# ---------- 3. 校验 ----------
print("=" * 60)
print("[3/5] 校验 zip 内容")
ok = True
for zname in [f"7tan-editor-free-v{VERSION}.zip", f"7tan-pro-src-v{VERSION}.zip", f"7tan-pro-update-v{VERSION}.zip"]:
    zp = RELEASE / zname
    with zipfile.ZipFile(zp) as zf:
        names = zf.namelist()
        broken = [n for n in names if "broken" in n.lower()]
        baks = [n for n in names if n.endswith((".bak", ".old"))]
        auth = [n for n in names if n.endswith("security/auth_client.pyd")]
        auth_size = zf.getinfo(auth[0]).file_size if auth else 0
    print(f"  {zname}: {zp.stat().st_size/1048576:.1f} MB, {len(names)} 文件 | broken={len(broken)} bak={len(baks)} auth_client.pyd={auth_size}B")
    if broken or baks or not auth or auth_size != 262151:
        ok = False
if not ok:
    print("[ERROR] zip 校验未通过"); sys.exit(1)

# ---------- 4. 签名 ----------
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
    pub.verify(sig, digest, padding.PKCS1v15(), hashes.SHA256())
    print(f"  [OK] {zp.name} sig={len(sig_b64)} chars VERIFY_OK")

# ---------- 5. manifest ----------
print("=" * 60)
print("[5/5] 更新 version.json")
with open(VER_JSON, encoding="utf-8") as f:
    manifest = json.load(f)
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
print(f"  version.json 更新完成 | 顺序: {[v['version'] for v in manifest['versions']]}")
print(f"  free md5={md5.hexdigest()} size={free_zip.stat().st_size}")

# 生成用户替换脚本（关闭软件后执行）
bat = ROOT / "apply_auth_internal.bat"
bat.write_text(
    "@echo off\n"
    "chcp 65001 >nul\n"
    "echo 正在替换 dist\\7tan-editor\\_internal\\src\\security\\auth_client.pyd 为修复版...\n"
    f'copy /Y "{FIXED}" "D:\\7tan\\7tanAI\\dist\\7tan-editor\\_internal\\src\\security\\auth_client.pyd" >nul\n'
    "if errorlevel 1 (echo 替换失败：请确认7Tan软件已完全关闭) else (echo 替换成功！)\n"
    "pause\n",
    encoding="utf-8",
)
print(f"\n  [生成] {bat} （关闭7Tan后双击执行，更新运行中exe的pyd）")

print("=" * 60)
print("P0 本地全部完成 ✅")
for zp in sorted(RELEASE.glob("*.zip")) + sorted(RELEASE.glob("*.sig")):
    print(f"  - {zp.name} ({zp.stat().st_size} B)")
