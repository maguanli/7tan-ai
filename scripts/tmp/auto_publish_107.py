# -*- coding: utf-8 -*-
"""
7Tan Editor v1.0.7 一键发布脚本
===============================
修复内容：登录错误提示 bug —— 账号/密码错误时客户端只显示"服务器返回 401"，
应显示服务器返回的"账号或密码错误"。

流程：
  1. 复制新版 auth_client.pyd（已编译，含修复）到 src/security/
  2. 更新 version.py / file_version_info.txt → 1.0.7
  3. 运行 build_and_sync.bat -y -v 1.0.7（PyInstaller 构建 + 打包 zip）
  4. 生成 free 包 + RSA 签名（.sig）
  5. 更新 version.json（新增 1.0.7 条目）
  6. 上传 zip + sig + version.json 到服务器 updates/
  7. 远程 MD5 校验 + 公网验证

运行前提：7Tan 主程序已完全退出（否则 pyd/dist 被锁定，步骤 1/3 会失败）
用法：  .venv\\Scripts\\python.exe auto_publish_107.py
"""
import base64
import hashlib
import json
import os
import posixpath
import shutil
import subprocess
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(r"D:\7tan\7tanAI")
SRC_PYD = ROOT / "tools" / "_tmp_authbuild" / "auth_client.pyd"   # 新版 pyd（已编译）
DST_PYD = ROOT / "src" / "security" / "auth_client.pyd"
VERSION_PY = ROOT / "src" / "config" / "version.py"
FILE_VER = ROOT / "file_version_info.txt"
RELEASE = ROOT / "dist" / "release"
PRIV = ROOT / "website" / "config" / "private_key.pem"
VER_JSON = ROOT / "website" / "updates" / "version.json"
NEW_VER = "1.0.7"
NOTES = ("1.0.7 更新：修复登录错误提示——账号或密码错误时正确显示「账号或密码错误」，"
         "不再显示「服务器返回 401」；exe 版本信息同步更新。")
LOG = RELEASE / "publish_107_log.txt"


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def fail(msg):
    log(f"❌ FAIL: {msg}")
    sys.exit(1)


def main():
    log("========== 7Tan Editor v1.0.7 自动发布开始 ==========")

    # ---------- 1. 复制新版 pyd ----------
    log("[1/7] 复制新版 auth_client.pyd -> src/security/")
    if not SRC_PYD.exists():
        fail(f"新版 pyd 不存在: {SRC_PYD}")
    try:
        shutil.copy2(SRC_PYD, DST_PYD)
        log(f"  OK 已替换 {DST_PYD} ({DST_PYD.stat().st_size:,}B)")
    except PermissionError:
        fail("src/security/auth_client.pyd 被占用！请先完全退出 7Tan 程序再运行本脚本")

    # ---------- 2. 更新版本号 ----------
    log("[2/7] 更新版本号 -> 1.0.7")
    try:
        txt = VERSION_PY.read_text(encoding="utf-8")
        txt = txt.replace('APP_VERSION = "1.0.6"', f'APP_VERSION = "{NEW_VER}"')
        VERSION_PY.write_text(txt, encoding="utf-8")
        log(f"  OK version.py -> {NEW_VER}")
    except Exception as e:
        fail(f"更新 version.py 失败: {e}")

    try:
        txt = FILE_VER.read_text(encoding="utf-8")
        txt = txt.replace("filevers=(1, 0, 6, 0)", "filevers=(1, 0, 7, 0)")
        txt = txt.replace("prodvers=(1, 0, 6, 0)", "prodvers=(1, 0, 7, 0)")
        txt = txt.replace("u'FileVersion', u'1.0.6'", "u'FileVersion', u'1.0.7'")
        txt = txt.replace("u'ProductVersion', u'1.0.6'", "u'ProductVersion', u'1.0.7'")
        FILE_VER.write_text(txt, encoding="utf-8")
        log("  OK file_version_info.txt -> 1.0.7")
    except Exception as e:
        log(f"  WARN file_version_info.txt 更新失败: {e}（继续）")

    # ---------- 3. 构建 ----------
    log("[3/7] 运行 build_and_sync.bat -y -v 1.0.7（构建约 10-20 分钟）")
    bat = ROOT / "build_and_sync.bat"
    r = subprocess.run(
        [str(bat), "-y", "-v", NEW_VER],
        cwd=str(ROOT), shell=True,
        timeout=2700,
    )
    if r.returncode != 0:
        fail(f"build_and_sync.bat 退出码 {r.returncode}")
    log("  构建完成")

    zip_v = RELEASE / f"7tan-editor-v{NEW_VER}.zip"
    if not zip_v.exists():
        fail(f"构建产物缺失: {zip_v}")

    # ---------- 4. free 包 + 签名 ----------
    log("[4/7] 生成 free 包并签名")
    free_zip = RELEASE / f"7tan-editor-free-v{NEW_VER}.zip"
    if free_zip.exists():
        free_zip.unlink()
    shutil.copy2(zip_v, free_zip)
    log(f"  OK free 包: {free_zip.name} ({free_zip.stat().st_size:,}B)")

    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    with open(PRIV, "rb") as f:
        priv = serialization.load_pem_private_key(f.read(), password=None)
    h = hashlib.sha256()
    with open(free_zip, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    sig = priv.sign(h.digest(), padding.PKCS1v15(), hashes.SHA256())
    sig_b64 = base64.b64encode(sig).decode("ascii")
    sig_path = free_zip.with_suffix(free_zip.suffix + ".sig")
    sig_path.write_text(sig_b64, encoding="ascii")
    log(f"  OK 签名完成 SHA256={h.hexdigest()} sig={sig_path.name}")

    # ---------- 5. version.json ----------
    log("[5/7] 更新 version.json")
    with open(VER_JSON, encoding="utf-8") as f:
        manifest = json.load(f)
    md5 = hashlib.md5()
    with open(free_zip, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            md5.update(c)
    new_entry = {
        "version": NEW_VER,
        "channel": "stable",
        "platform": "windows",
        "url": f"https://www.7tan.com/updates/7tan-editor-free-v{NEW_VER}.zip",
        "md5": md5.hexdigest(),
        "size": free_zip.stat().st_size,
        "notes": NOTES,
        "release_date": time.strftime("%Y-%m-%d"),
    }
    manifest["versions"] = [v for v in manifest.get("versions", []) if v.get("version") != NEW_VER] + [new_entry]
    manifest["versions"] = sorted(manifest["versions"], key=lambda v: [int(x) for x in v["version"].split(".")], reverse=True)
    with open(VER_JSON, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    log(f"  最新条目: {manifest['versions'][0]['version']} md5={md5.hexdigest()} size={free_zip.stat().st_size}")

    # ---------- 6. 上传 ----------
    log("[6/7] 上传到服务器 updates/")
    import paramiko
    HOST, PORT, USER = "47.86.169.72", 22, "administrator"
    PW = base64.b64decode("aG01NzNpa0VZY2xJRWcjQGtt").decode()
    REMOTE_DIR = "/D:/workspace/7tan/updates"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PW, timeout=30)
    sftp = ssh.open_sftp()
    log("  SSH 连接成功")

    for f in [free_zip, sig_path, VER_JSON]:
        remote = posixpath.join(REMOTE_DIR, f.name)
        st = time.time()
        sftp.put(str(f), remote, confirm=False)
        log(f"  OK {f.name} -> {remote} ({f.stat().st_size/1048576:.1f}MB, {time.time()-st:.1f}s)")

    # ---------- 7. 远程校验 ----------
    log("[7/7] 远程 MD5 校验 + 公网验证")
    def remote_md5(remote_path):
        _, stdout, _ = ssh.exec_command(f'certutil -hashfile "{remote_path}" MD5', timeout=300)
        out = stdout.read().decode("gbk", errors="ignore")
        for line in out.splitlines():
            line = line.strip()
            if len(line) == 32 and all(c in "0123456789abcdefABCDEF" for c in line):
                return line.lower()
        return "?"

    def local_md5(p):
        m = hashlib.md5()
        with open(p, "rb") as f:
            for c in iter(lambda: f.read(1 << 20), b""):
                m.update(c)
        return m.hexdigest()

    for f in [free_zip, sig_path, VER_JSON]:
        rp = posixpath.join(REMOTE_DIR, f.name)
        try:
            st = sftp.stat(rp)
            lm = local_md5(f)
            rm = remote_md5(rp)
            match = "MATCH" if lm == rm else "DIFF!"
            log(f"  {f.name}: 远程 {st.st_size:,}B | 本地MD5={lm} | 远程MD5={rm} | {match}")
        except Exception as e:
            log(f"  {f.name}: 远程缺失! {e}")

    import urllib.request
    try:
        req = urllib.request.Request("https://www.7tan.com/updates/version.json", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            data = json.loads(body) if body.strip().startswith("{") else {}
            top = data.get("versions", [{}])[0].get("version", "?")
            log(f"  公网 version.json HTTP {resp.status} 最新版本: {top}")
            if top != NEW_VER:
                log("  ⚠️ 公网最新版本不是 1.0.7，请检查 CDN/缓存")
    except Exception as e:
        log(f"  公网访问失败: {e}")

    sftp.close()
    ssh.close()
    log("✅✅✅ ALL DONE — v1.0.7 发布完成！可重新打开 7Tan")


if __name__ == "__main__":
    main()
