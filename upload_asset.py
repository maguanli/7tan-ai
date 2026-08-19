# -*- coding: utf-8 -*-
"""娴佸紡涓婁紶 GitHub Release 璧勪骇锛堟敮鎸佸ぇ鏂囦欢锛屾柇绾垮彲閲嶈瘯锛?""
import sys, os, time, urllib.request

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload_progress.log")


def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

TOKEN = "%GITHUB_TOKEN%"
RID = "372578963"
DIR = r"D:\7tan\7tanAI\dist\release\github"


def upload(fname):
    path = os.path.join(DIR, fname)
    url = f"https://uploads.github.com/repos/maguanli/7tan-ai/releases/{RID}/assets?name={fname}"
    size = os.path.getsize(path)
    log(f"[START] {fname} size={size}")

    def gen():
        with open(path, "rb") as f:
            while True:
                chunk = f.read(1 << 20)
                if not chunk:
                    break
                yield chunk

    req = urllib.request.Request(url, data=gen(), method="POST")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Content-Type", "application/zip")
    req.add_header("Content-Length", str(size))
    try:
        with urllib.request.urlopen(req, timeout=7200) as resp:
            body = resp.read()
        log(f"[DONE] {fname} status={resp.status} {body[:150]}")
    except Exception as e:
        log(f"[FAIL] {fname} {e}")


if __name__ == "__main__":
    upload(sys.argv[1])

