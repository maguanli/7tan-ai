# -*- coding: utf-8 -*-
"""GitHub Release 创建 + 流式上传资产（支持大文件）"""
import sys, os, json, urllib.request, urllib.error

TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com/repos/maguanli/7tan-ai"
UPLOAD = "https://uploads.github.com/repos/maguanli/7tan-ai/releases"
RELEASE_DIR = r"D:\7tan\7tanAI\dist\release"


def req(url, method="GET", data=None, headers=None, timeout=300):
    h = {"Authorization": "Bearer " + TOKEN, "Accept": "application/vnd.github+json"}
    if headers:
        h.update(headers)
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        h["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=body, method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def get_release(tag):
    st, body = req(API + "/releases/tags/" + tag)
    if st == 200:
        return json.loads(body)
    return None


def create_release(tag, name, body):
    st, b = req(API + "/releases", method="POST",
                data={"tag_name": tag, "name": name, "body": body,
                      "draft": False, "prerelease": False})
    if st in (200, 201):
        return json.loads(b)
    print("[CREATE FAIL] %d %s" % (st, b[:300]))
    return None


def upload_asset(rid, fname, fpath, ctype):
    url = UPLOAD + "/%s/assets?name=%s" % (rid, fname)
    size = os.path.getsize(fpath)

    def gen():
        with open(fpath, "rb") as f:
            while True:
                chunk = f.read(1 << 20)
                if not chunk:
                    break
                yield chunk

    r = urllib.request.Request(url, data=gen(), method="POST")
    r.add_header("Authorization", "Bearer " + TOKEN)
    r.add_header("Content-Type", ctype)
    r.add_header("Content-Length", str(size))
    try:
        with urllib.request.urlopen(r, timeout=7200) as resp:
            body = resp.read().decode("utf-8", "replace")
        print("[DONE] %s status=%s %s" % (fname, resp.status, body[:120]))
        return True
    except Exception as e:
        print("[FAIL] %s %s" % (fname, e))
        return False


if __name__ == "__main__":
    version = sys.argv[1]
    action = sys.argv[2] if len(sys.argv) > 2 else "create"
    tag = "v" + version
    if action == "create":
        rel = get_release(tag)
        if rel:
            print("[EXISTS] %s id=%s" % (tag, rel["id"]))
        else:
            rel = create_release(tag, "7Tan Editor v" + version,
                                 "7Tan Editor v" + version + " 发布。\n\n安装包见下方附件资产。")
            if rel:
                print("[CREATED] %s id=%s" % (tag, rel["id"]))
    elif action == "upload":
        fname = sys.argv[3]
        ctype = sys.argv[4] if len(sys.argv) > 4 else "application/octet-stream"
        rel = get_release(tag)
        if not rel:
            print("[ERR] release %s 不存在，先 create" % tag)
            sys.exit(1)
        fpath = os.path.join(RELEASE_DIR, fname)
        if not os.path.exists(fpath):
            print("[ERR] 文件不存在 %s" % fpath)
            sys.exit(1)
        upload_asset(rel["id"], fname, fpath, ctype)
    elif action == "assets":
        rel = get_release(tag)
        if not rel:
            print("[ERR] release %s 不存在" % tag)
            sys.exit(1)
        st, b = req(API + "/releases/%s/assets" % rel["id"])
        if st == 200:
            for a in json.loads(b):
                print(a["id"], a["name"], a["size"], a["browser_download_url"])
        else:
            print("[ERR] %s %s" % (st, b[:200]))
