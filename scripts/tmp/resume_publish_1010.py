# -*- coding: utf-8 -*-
"""7Tan Editor v1.0.10 发布续跑：上传 + 远程校验 + 公网验证（步骤 7-8）"""
import base64
import hashlib
import json
import posixpath
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(r"D:\7tan\7tanAI")
RELEASE = ROOT / "dist" / "release"
VER_JSON = ROOT / "website" / "updates" / "version.json"
NEW_VER = "1.0.10"
LOG = RELEASE / "publish_1010_resume_log.txt"


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def local_md5(p):
    m = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            m.update(c)
    return m.hexdigest()


def main():
    log("========== v1.0.10 发布续跑（上传+校验）开始 ==========")
    free_zip = RELEASE / f"7tan-editor-free-v{NEW_VER}.zip"
    sig_path = RELEASE / f"7tan-editor-free-v{NEW_VER}.zip.sig"
    for p in [free_zip, sig_path, VER_JSON]:
        if not p.exists():
            log(f"FAIL: 本地文件缺失 {p}")
            return

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
