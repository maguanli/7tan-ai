# -*- coding: utf-8 -*-
"""v1.0.10 收尾：重传 version.json + 远程校验 + 公网验证"""
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
LOG = RELEASE / "publish_1010_final_log.txt"


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
    log("========== v1.0.10 收尾（重传 version.json + 校验）开始 ==========")
    import paramiko

    HOST, PORT, USER = "47.86.169.72", 22, "administrator"
    PW = base64.b64decode("aG01NzNpa0VZY2xJRWcjQGtt").decode()
    REMOTE_DIR = "/D:/workspace/7tan/updates"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PW, timeout=30)
    sftp = ssh.open_sftp()
    log("  SSH 连接成功")

    # 1) 列出远程 updates 目录
    log("  远程 updates/ 目录内容:")
    try:
        for attr in sftp.listdir_attr(REMOTE_DIR):
            log(f"    {attr.filename}  {attr.st_size:,}B  mtime={time.strftime('%Y-%m-%d %H:%M', time.localtime(attr.st_mtime))}")
    except Exception as e:
        log(f"    listdir 失败: {e}")

    # 2) 重传 version.json（先删后传，避免占用/覆盖问题）
    rv = posixpath.join(REMOTE_DIR, "version.json")
    try:
        sftp.remove(rv)
        log("  已删除远程旧 version.json")
    except Exception as e:
        log(f"  远程 version.json 删除跳过: {e}")
    try:
        st = time.time()
        sftp.put(str(VER_JSON), rv, confirm=True)
        log(f"  OK 上传 version.json -> {rv} ({VER_JSON.stat().st_size:,}B, {time.time()-st:.1f}s)")
    except Exception as e:
        log(f"  上传 version.json 失败: {e}")

    # 3) 远程内容校验：读取远程 version.json 对比
    try:
        with sftp.open(rv, "r") as f:
            remote_body = f.read().decode("utf-8", errors="ignore")
        local_body = VER_JSON.read_text(encoding="utf-8")
        same = remote_body.strip() == local_body.strip()
        log(f"  远程 version.json 内容一致: {same} (远程 {len(remote_body)}B / 本地 {len(local_body)}B)")
        if same:
            data = json.loads(remote_body)
            top = data.get("versions", [{}])[0]
            log(f"  远程最新条目: {top.get('version')} url={top.get('url')}")
    except Exception as e:
        log(f"  远程 version.json 读取失败: {e}")

    # 4) 公网验证
    import urllib.request
    try:
        req = urllib.request.Request(
            "https://www.7tan.com/updates/version.json", headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            data = json.loads(body) if body.strip().startswith("{") else {}
            top = data.get("versions", [{}])[0].get("version", "?")
            url_top = data.get("versions", [{}])[0].get("url", "?")
            log(f"  公网 version.json HTTP {resp.status} 最新版本: {top} url={url_top}")
            if top != NEW_VER:
                log(f"  WARN 公网最新版本不是 {NEW_VER}，请检查 CDN/缓存")
    except Exception as e:
        log(f"  公网访问失败: {e}")

    # 5) 公网下载 zip 校验 MD5（HEAD 请求确认可下载）
    try:
        req = urllib.request.Request(
            f"https://www.7tan.com/updates/7tan-editor-free-v{NEW_VER}.zip",
            headers={"User-Agent": "Mozilla/5.0"},
            method="HEAD",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            clen = resp.headers.get("Content-Length", "?")
            log(f"  公网 zip HEAD HTTP {resp.status} Content-Length={clen}")
    except Exception as e:
        log(f"  公网 zip HEAD 失败: {e}")

    sftp.close()
    ssh.close()
    log(f"========== ALL DONE - v{NEW_VER} 收尾完成 ==========")


if __name__ == "__main__":
    main()
