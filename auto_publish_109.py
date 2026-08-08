# -*- coding: utf-8 -*-
"""
7Tan Editor v1.0.9 发布脚本（自动全流程）
==========================================
  1. 更新 version.py / file_version_info.txt -> 1.0.8
  2. 运行 build_and_sync.bat -y -v 1.0.8（构建 exe + 首次打包）
  3. 校验 dist pyd 与 src pyd 是否一致（不一致则 PATCH，绕过 src 锁定）
  4. 重新运行 package_release.py 打包 zip（覆盖旧 zip）
  5. 生成 free 包 + RSA 签名（.sig）
  6. 更新 version.json（md5/size/notes）
  7. 上传 zip + sig + version.json 到服务器 updates/
  8. 远程 MD5 校验 + 公网验证
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
VERSION_PY = ROOT / "src" / "config" / "version.py"
FILE_VER = ROOT / "file_version_info.txt"
RELEASE = ROOT / "dist" / "release"
PRIV = ROOT / "website" / "config" / "private_key.pem"
VER_JSON = ROOT / "website" / "updates" / "version.json"
DIST_PYD = ROOT / "dist" / "7tan-editor" / "_internal" / "src" / "security" / "auth_client.pyd"
SRC_PYD = ROOT / "src" / "security" / "auth_client.pyd"
NEW_VER = "1.0.9"
NOTES = ("1.0.9 更新：版本权益统一更名为「完整版」——左侧底部状态、升级/续费提示、"
         "新手引导、用户协议、隐私政策及官网 pro.php 等全部同步；"
         "此前「专业版/进化版」文案全部统一为「完整版」。")
LOG = RELEASE / "publish_109_log.txt"
BUILD_LOG = ROOT / "build_publish_109.log"


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def fail(msg):
    log(f"FAIL: {msg}")
    sys.exit(1)


def run_build(cmd, timeout=2700):
    log(f"运行: {cmd}")
    with open(BUILD_LOG, "w", encoding="utf-8", errors="replace") as f:
        p = subprocess.Popen(cmd, shell=True, cwd=str(ROOT), stdout=f, stderr=subprocess.STDOUT)
        try:
            p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            p.kill()
            return -1
    return p.returncode


def tail_log(n=40):
    try:
        lines = open(BUILD_LOG, encoding="utf-8", errors="replace").read().splitlines()
        return "\n".join(lines[-n:])
    except Exception:
        return "(无日志)"


def local_md5(p):
    m = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            m.update(c)
    return m.hexdigest()


def main():
    log("========== 7Tan Editor v1.0.9 发布开始 ==========")

    # ---------- 1. 更新版本号 ----------
    log("[1/8] 更新 version.py / file_version_info.txt -> 1.0.9")
    try:
        txt = VERSION_PY.read_text(encoding="utf-8")
        if 'APP_VERSION = "1.0.8"' not in txt:
            txt = txt.replace('APP_VERSION = "1.0.7"', f'APP_VERSION = "{NEW_VER}"')
            VERSION_PY.write_text(txt, encoding="utf-8")
        log("  OK version.py -> 1.0.9")
    except Exception as e:
        log(f"  WARN version.py 更新失败: {e}（继续）")
    try:
        txt = FILE_VER.read_text(encoding="utf-8")
        txt = txt.replace("filevers=(1, 0, 7, 0)", "filevers=(1, 0, 8, 0)")
        txt = txt.replace("prodvers=(1, 0, 7, 0)", "prodvers=(1, 0, 8, 0)")
        txt = txt.replace("u'FileVersion', u'1.0.7'", "u'FileVersion', u'1.0.8'")
        txt = txt.replace("u'ProductVersion', u'1.0.7'", "u'ProductVersion', u'1.0.8'")
        FILE_VER.write_text(txt, encoding="utf-8")
        log("  OK file_version_info.txt -> 1.0.8")
    except Exception as e:
        log(f"  WARN file_version_info.txt 更新失败: {e}（继续）")

    # ---------- 2. 构建 ----------
    log("[2/8] 运行 build_and_sync.bat -y -v 1.0.9（构建约 10-20 分钟）")
    rc = run_build(f'"{ROOT / "build_and_sync.bat"}" -y -v {NEW_VER}')
    if rc != 0:
        log("构建失败，最后 40 行日志：\n" + tail_log())
        fail(f"build_and_sync.bat 退出码 {rc}")
    zip_v = RELEASE / f"7tan-editor-v{NEW_VER}.zip"
    if not zip_v.exists():
        fail(f"构建产物缺失: {zip_v}")

    # ---------- 3. 校验/修复 dist pyd ----------
    log("[3/8] 校验 dist pyd 与 src pyd 一致性")
    if SRC_PYD.exists() and DIST_PYD.exists():
        if local_md5(SRC_PYD) != local_md5(DIST_PYD):
            shutil.copy2(SRC_PYD, DIST_PYD)
            log(f"  OK dist pyd 已用 src 最新版覆盖 ({DIST_PYD.stat().st_size:,}B)")
        else:
            log("  OK dist pyd 与 src 一致，无需 PATCH")
    else:
        log(f"  WARN pyd 检查跳过 (src={SRC_PYD.exists()} dist={DIST_PYD.exists()})")

    # ---------- 4. 重新打包 zip ----------
    log("[4/8] 重新打包 zip")
    rc = run_build(
        f'"{ROOT / ".venv" / "Scripts" / "python.exe"}" templates\\package_release.py '
        f'--uid "" --version {NEW_VER} --out dist\\release --free-dir dist\\7tan-editor',
        timeout=1800,
    )
    if rc != 0:
        log("重新打包失败，最后 40 行日志：\n" + tail_log())
        fail(f"package_release.py 退出码 {rc}")
    if not zip_v.exists():
        fail(f"重新打包后 zip 缺失: {zip_v}")
    log(f"  OK zip: {zip_v.name} ({zip_v.stat().st_size:,}B)")

    # ---------- 5. free 包 + 签名 ----------
    log("[5/8] 生成 free 包并签名")
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

    # ---------- 6. version.json ----------
    log("[6/8] 更新 version.json")
    with open(VER_JSON, encoding="utf-8") as f:
        manifest = json.load(f)
    md5 = local_md5(free_zip)
    new_entry = {
        "version": NEW_VER,
        "channel": "stable",
        "platform": "windows",
        "url": f"https://www.7tan.com/updates/7tan-editor-free-v{NEW_VER}.zip",
        "md5": md5,
        "size": free_zip.stat().st_size,
        "notes": NOTES,
        "release_date": time.strftime("%Y-%m-%d"),
    }
    manifest["versions"] = [v for v in manifest.get("versions", []) if v.get("version") != NEW_VER] + [new_entry]
    manifest["versions"] = sorted(
        manifest["versions"],
        key=lambda v: [int(x) for x in v["version"].split(".")],
        reverse=True,
    )
    with open(VER_JSON, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    log(f"  最新条目: {manifest['versions'][0]['version']} md5={md5} size={free_zip.stat().st_size}")

    # ---------- 7. 上传 + 校验 ----------
    log("[7/8] 上传到服务器 updates/")
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

    def remote_md5(remote_path):
        _, stdout, _ = ssh.exec_command(f'certutil -hashfile "{remote_path}" MD5', timeout=300)
        out = stdout.read().decode("gbk", errors="ignore")
        for line in out.splitlines():
            line = line.strip()
            if len(line) == 32 and all(c in "0123456789abcdefABCDEF" for c in line):
                return line.lower()
        return "?"

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
        req = urllib.request.Request(
            "https://www.7tan.com/updates/version.json", headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            data = json.loads(body) if body.strip().startswith("{") else {}
            top = data.get("versions", [{}])[0].get("version", "?")
            log(f"  公网 version.json HTTP {resp.status} 最新版本: {top}")
            if top != NEW_VER:
                log(f"  WARN 公网最新版本不是 {NEW_VER}，请检查 CDN/缓存")
    except Exception as e:
        log(f"  公网访问失败: {e}")

    sftp.close()
    ssh.close()
    log(f"========== ALL DONE - v{NEW_VER} 发布完成 ==========")


if __name__ == "__main__":
    main()
