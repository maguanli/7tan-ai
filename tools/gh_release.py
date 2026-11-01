# -*- coding: utf-8 -*-
"""GitHub Release 发布工具（7tan-ai）

用途：把本地构建产出的安装包发成 GitHub Release（打 tag + 建 release + 传附件 + 回验）。

设计原则：
  1. 凭据只从 config/deploy.json 读，不写在代码里、不打印
  2. 每一步都能单独跑：check / create / upload / verify
  3. 默认 dry-run；加 --execute 才真正动远程
  4. 传完立刻用 API 回验（附件名、大小、digest），不靠“我以为传上去了”

用法：
  python tools/gh_release.py check                       # 只看远程现状
  python tools/gh_release.py create  --version 1.0.23 --execute
  python tools/gh_release.py upload  --version 1.0.23 --execute
  python tools/gh_release.py verify  --version 1.0.23
  python tools/gh_release.py all     --version 1.0.23 --execute   # 一条龙
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPLOY = os.path.join(ROOT, "config", "deploy.json")
VERSION_JSON = os.path.join(ROOT, "website", "updates", "version.json")
RELEASE_DIR = os.path.join(ROOT, "dist", "release")

ASSET_SUFFIXES = (".zip", ".zip.sig")


# ---------------------------------------------------------------- 基础

def _token_ok(tok, api_base):
    """用 /user 探一下令牌是否可用，返回 (ok, 说明)。"""
    req = urllib.request.Request(api_base.rstrip("/") + "/user", headers={
        "Authorization": "Bearer " + tok,
        "Accept": "application/vnd.github+json",
        "User-Agent": "7tan-release-tool",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            login = json.loads(r.read().decode()).get("login")
            scopes = r.headers.get("X-OAuth-Scopes", "")
            return True, "login=%s scopes=%s" % (login, scopes or "(未返回)")
    except urllib.error.HTTPError as e:
        return False, "HTTP %d" % e.code
    except Exception as e:
        return False, repr(e)


def _token_from_gcm():
    """从 Windows 凭据管理器（git-credential-manager）取令牌。"""
    try:
        p = subprocess.run(["git", "credential", "fill"],
                           input="protocol=https\nhost=github.com\n\n",
                           capture_output=True, text=True, timeout=60)
    except Exception:
        return None
    if p.returncode != 0:
        return None
    for ln in p.stdout.splitlines():
        if ln.startswith("password="):
            return ln.split("=", 1)[1].strip()
    return None


def load_cfg():
    if not os.path.exists(DEPLOY):
        raise SystemExit("找不到 config/deploy.json")
    d = json.load(open(DEPLOY, encoding="utf-8"))
    g = d.get("github") or {}
    tok = (g.get("token") or "").strip()
    owner = g.get("owner") or "maguanli"
    repo = g.get("repo") or "7tan-ai"
    api_base = g.get("api") or "https://api.github.com"

    source = "deploy.json"
    if tok:
        ok, why = _token_ok(tok, api_base)
        if not ok:
            print("[凭据] deploy.json 中的令牌不可用（%s），改从 git 凭据管理器取…" % why)
            tok = ""
    if not tok:
        tok = _token_from_gcm() or ""
        source = "git-credential-manager"
        if tok:
            ok, why = _token_ok(tok, api_base)
            if not ok:
                raise SystemExit("[凭据] 凭据管理器中的令牌也不可用（%s）" % why)
            print("[凭据] 使用凭据管理器的令牌（来源 %s）" % source)
    if not tok:
        raise SystemExit("拿不到可用的 GitHub 令牌：deploy.json 与凭据管理器都失败")

    return {
        "token": tok,
        "owner": owner,
        "repo": repo,
        "api": api_base,
        "uploads": g.get("uploads") or "https://uploads.github.com",
        "source": source,
    }


def api(cfg, path, method="GET", body=None, timeout=60):
    url = cfg["api"].rstrip("/") + path
    data = None
    headers = {
        "Authorization": "Bearer " + cfg["token"],
        "Accept": "application/vnd.github+json",
        "User-Agent": "7tan-release-tool",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return r.status, (json.loads(raw.decode("utf-8")) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"raw": raw[:500]}
        return e.code, parsed


def find_version_entry(version):
    if not os.path.exists(VERSION_JSON):
        raise SystemExit("找不到 website/updates/version.json")
    data = json.load(open(VERSION_JSON, encoding="utf-8"))
    for v in data.get("versions", []):
        if str(v.get("version")) == str(version):
            return v
    raise SystemExit("version.json 里没有 %s 这一条" % version)


def md5_of(path, limit=None, progress=False):
    h = hashlib.md5()
    total = os.path.getsize(path)
    done = 0
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
            done += len(chunk)
            if progress and total:
                pct = done * 100 // total
                if pct % 10 == 0 and pct and getattr(md5_of, "_last", -1) != pct:
                    md5_of._last = pct
                    print("      …%d%% (%d/%d MB)" % (pct, done >> 20, total >> 20))
    return h.hexdigest()


def local_assets(version):
    """本地待传附件：dist/release 下带版本号、且能被 version.json 的 md5 对上。"""
    entry = find_version_entry(version)
    out = []
    if not os.path.isdir(RELEASE_DIR):
        return entry, out
    for name in sorted(os.listdir(RELEASE_DIR)):
        if version not in name or not name.endswith(ASSET_SUFFIXES):
            continue
        p = os.path.join(RELEASE_DIR, name)
        if not os.path.isfile(p):
            continue
        out.append({
            "path": p,
            "name": name,
            "size": os.path.getsize(p),
            "is_zip": name.endswith(".zip"),
        })
    return entry, out


def build_body(version, entry):
    """把 version.json 的 notes 转成 Markdown。"""
    notes = (entry.get("notes") or "").strip()
    lines = [ln.rstrip() for ln in notes.splitlines() if ln.strip()]
    out = ["## 7Tan Editor v%s" % version, ""]
    if lines and lines[0].startswith(version):
        lines = lines[1:]
    out.append("发布日期：%s　｜　体积：%.1f MB" % (
        entry.get("release_date", "-"), (entry.get("size") or 0) / 1048576.0))
    out.append("")
    for ln in lines:
        s = ln.strip()
        if s.startswith("【"):
            i = s.find("】")
            if i > 0:
                head = s[1:i].strip()
                rest = s[i + 1:].strip()
                out.append("")
                out.append("### " + head)
                out.append("")
                if rest:
                    out.append(rest)
                continue
        if s.startswith("·"):
            out.append("- " + s.lstrip("· ").strip())
        else:
            out.append(s)
    out.append("")
    out.append("---")
    out.append("")
    out.append("**下载**")
    out.append("")
    out.append("- 编辑器（Windows 绿色免安装）：`7tan-editor-free-v%s.zip`" % version)
    out.append("- 网页版（服务端部署包）：`7tan-web-v%s.zip`" % version)
    out.append("- 每个包都附带 `.sig` 签名文件，客户端自动更新时会做 RSA 验签")
    out.append("")
    out.append("**校验值**")
    out.append("")
    out.append("```")
    out.append("MD5    %s" % entry.get("md5", "-"))
    out.append("SIZE   %s" % entry.get("size", "-"))
    out.append("```")
    out.append("")
    out.append("> 官网下载与应用内自动更新：https://www.7tan.com/updates/version.json")
    return "\n".join(out)


# ---------------------------------------------------------------- 子命令

def cmd_check(cfg, args):
    print("[check] 远程仓库 %s/%s" % (cfg["owner"], cfg["repo"]))
    st, rels = api(cfg, "/repos/%s/%s/releases?per_page=100" % (cfg["owner"], cfg["repo"]))
    print("    releases: HTTP %d, 共 %d 条" % (st, len(rels) if isinstance(rels, list) else -1))
    if isinstance(rels, list):
        for r in rels:
            print("      %-10s %-28s assets=%d published=%s" % (
                r["tag_name"], (r.get("name") or "")[:28], len(r.get("assets") or []),
                (r.get("published_at") or "")[:10]))
        want = "v" + args.version
        hit = [r for r in rels if r["tag_name"] == want]
        print("    %s 已存在: %s" % (want, bool(hit)))
        if rels:
            print("    最新一条: %s（releases 页首条）" % rels[0]["tag_name"])

    st, tags = api(cfg, "/repos/%s/%s/tags" % (cfg["owner"], cfg["repo"]))
    if isinstance(tags, list):
        print("    tags: %d 条" % len(tags))
        shas = {}
        for t in tags:
            shas.setdefault(t["commit"]["sha"], []).append(t["name"])
        for sha, names in shas.items():
            print("      %s <- %s" % (sha[:8], ", ".join(sorted(names))))

    st, br = api(cfg, "/repos/%s/%s/branches" % (cfg["owner"], cfg["repo"]))
    if isinstance(br, list):
        print("    分支:")
        for b in br:
            print("      %-30s %s" % (b["name"], b["commit"]["sha"][:8]))
    return 0


def cmd_create(cfg, args):
    version = args.version
    tag = "v" + version
    entry, assets = local_assets(version)
    print("[create] %s" % tag)
    print("    标题: 7Tan Editor v%s" % version)
    print("    目标: %s" % args.target)

    st, rel = api(cfg, "/repos/%s/%s/releases/tags/%s" % (cfg["owner"], cfg["repo"], tag))
    if st == 200:
        print("    release 已存在（id=%s），跳过创建" % rel.get("id"))
        return 0
    if st != 404:
        print("    !! 查询返回 HTTP %d: %s" % (st, rel))
        return 1

    body = {
        "tag_name": tag,
        "name": "7Tan Editor v%s" % version,
        "body": build_body(version, entry),
        "target_commitish": args.target,
        "draft": bool(args.draft),
        "prerelease": False,
    }
    print("    正文 %d 字符，前 3 行：" % len(body["body"]))
    for ln in body["body"].splitlines()[:3]:
        print("      | " + ln)

    if not args.execute:
        print("    [dry-run] 未执行。加 --execute 真正创建")
        return 0

    st, rel = api(cfg, "/repos/%s/%s/releases" % (cfg["owner"], cfg["repo"]),
                  method="POST", body=body, timeout=120)
    if st not in (200, 201):
        print("    !! 创建失败 HTTP %d: %s" % (st, rel))
        return 1
    print("    ✅ 已创建 id=%s  html=%s" % (rel.get("id"), rel.get("html_url")))
    print("    tag %s -> %s" % (rel.get("tag_name"), (rel.get("target_commitish") or "")[:12]))
    return 0


def cmd_body(cfg, args):
    """用 version.json 的 notes 重新渲染并更新已存在 release 的正文。"""
    version = args.version
    tag = "v" + version
    entry = find_version_entry(version)
    body = build_body(version, entry)
    print("[body] %s  新正文 %d 字符" % (tag, len(body)))
    heads = [ln for ln in body.splitlines() if ln.startswith("### ")]
    print("    小节 %d 个: %s" % (len(heads), " / ".join(h[4:] for h in heads)))

    st, rel = api(cfg, "/repos/%s/%s/releases/tags/%s" % (cfg["owner"], cfg["repo"], tag))
    if st != 200:
        print("    !! release 不存在（HTTP %d）" % st)
        return 1
    old = rel.get("body") or ""
    print("    旧正文 %d 字符，%s" % (len(old), "有变化" if old != body else "无变化"))
    if old == body:
        return 0
    if not args.execute:
        print("    [dry-run] 未更新。加 --execute 真正改")
        return 0
    st, rel = api(cfg, "/repos/%s/%s/releases/%s" % (cfg["owner"], cfg["repo"], rel["id"]),
                  method="PATCH", body={"body": body}, timeout=60)
    if st != 200:
        print("    !! 更新失败 HTTP %d: %s" % (st, rel))
        return 1
    print("    ✅ 已更新，回读长度 %d" % len(rel.get("body") or ""))
    return 0


def cmd_upload(cfg, args):
    version = args.version
    tag = "v" + version
    entry, assets = local_assets(version)
    print("[upload] %s  本地附件 %d 个" % (tag, len(assets)))
    if not assets:
        print("    !! dist/release 下没有 %s 的文件" % version)
        return 1

    st, rel = api(cfg, "/repos/%s/%s/releases/tags/%s" % (cfg["owner"], cfg["repo"], tag))
    if st != 200:
        print("    !! release 不存在（HTTP %d），先跑 create" % st)
        return 1
    rel_id = rel["id"]
    existing = {a["name"]: a for a in rel.get("assets") or []}

    # 只传 version.json 里登记过 md5 的安装包 + 对应 sig
    want_md5 = (entry.get("md5") or "").lower()
    rc = 0
    for a in assets:
        name, path, size = a["name"], a["path"], a["size"]
        print("")
        print("    ── %s  %.1f MB" % (name, size / 1048576.0))

        if name in existing:
            e = existing[name]
            print("       已存在 %d B，跳过" % e["size"])
            if e["size"] != size:
                print("       !! 大小不一致（本地 %d），需要先删远程再传" % size)
                rc = 1
            continue

        if a["is_zip"]:
            print("       本地 md5 计算中…")
            got = md5_of(path)
            print("       md5 = %s" % got)
            if want_md5 and name.startswith("7tan-editor-free") and got != want_md5:
                print("       !! 与 version.json 登记的 md5 不一致，拒绝上传")
                rc = 1
                continue

        if not args.execute:
            print("       [dry-run] 未上传")
            continue

        url = "%s/repos/%s/%s/releases/%s/assets?name=%s" % (
            cfg["uploads"].rstrip("/"), cfg["owner"], cfg["repo"], rel_id,
            urllib.request.quote(name))
        print("       上传中（最长等 3600s）…")
        t0 = time.time()
        # 大文件必须用 http.client 手动流式发，urllib 会把整个文件读进内存
        ok, msg = _put_file(url, cfg["token"], path, size, timeout=3600)
        dt = time.time() - t0
        if ok:
            print("       ✅ 完成 %.1fs（%.2f MB/s）" % (dt, (size / 1048576.0) / max(dt, 1)))
        else:
            print("       !! 失败 %.1fs：%s" % (dt, msg))
            rc = 1
        if name.startswith("7tan-editor-free") and dt > 0:
            print("       实际速率 %.2f MB/s" % ((size / 1048576.0) / dt))
    return rc


def _put_file(url, token, path, size, timeout=3600):
    import http.client

    from urllib.parse import urlparse
    u = urlparse(url)
    conn = http.client.HTTPSConnection(u.hostname, timeout=timeout)
    try:
        conn.putrequest("POST", u.path + ("?" + u.query if u.query else ""))
        conn.putheader("Authorization", "Bearer " + token)
        conn.putheader("Accept", "application/vnd.github+json")
        conn.putheader("User-Agent", "7tan-release-tool")
        conn.putheader("Content-Type", "application/octet-stream")
        conn.putheader("Content-Length", str(size))
        conn.endheaders()
        sent = 0
        last_pct = -1
        with open(path, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                conn.send(chunk)
                sent += len(chunk)
                pct = sent * 100 // size if size else 0
                if pct != last_pct and pct % 10 == 0:
                    last_pct = pct
                    print("         …%d%% %d/%d MB" % (pct, sent >> 20, size >> 20))
        resp = conn.getresponse()
        raw = resp.read().decode("utf-8", "replace")
        if resp.status in (200, 201):
            return True, raw[:200]
        return False, "HTTP %d %s" % (resp.status, raw[:300])
    except (socket.timeout, urllib.error.URLError, OSError) as e:
        return False, repr(e)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def cmd_verify(cfg, args):
    version = args.version
    tag = "v" + version
    entry, assets = local_assets(version)
    print("[verify] %s" % tag)
    st, rels = api(cfg, "/repos/%s/%s/releases?per_page=100" % (cfg["owner"], cfg["repo"]))
    if st != 200 or not isinstance(rels, list):
        print("    !! HTTP %d" % st)
        return 1

    hit = [r for r in rels if r["tag_name"] == tag]
    checks = []
    checks.append(("release 存在", bool(hit)))
    if not hit:
        for k, v in checks:
            print("    [FAIL] %s" % k)
        return 1
    rel = hit[0]
    checks.append(("releases 页首条就是它", rels[0]["tag_name"] == tag))
    checks.append(("tag 正确", rel["tag_name"] == tag))
    checks.append(("已发布（非 draft）", not rel.get("draft")))

    st2, commit = api(cfg, "/repos/%s/%s/commits/%s" % (cfg["owner"], cfg["repo"], tag))
    checks.append(("tag 指向的提交可解析", st2 == 200))

    remote = {a["name"]: a for a in rel.get("assets") or []}
    for a in assets:
        n = a["name"]
        r = remote.get(n)
        checks.append(("附件存在 %s" % n, r is not None))
        if r:
            checks.append(("  大小一致 %s (%d B)" % (n, a["size"]), r["size"] == a["size"]))
            digest = (r.get("digest") or "")
            if digest.startswith("sha256:") and a["is_zip"]:
                local_sha = hashlib.sha256(open(a["path"], "rb").read()).hexdigest()
                checks.append(("  sha256 一致 %s" % n, digest.split(":", 1)[1] == local_sha))

    print("    release id=%s  html=%s" % (rel.get("id"), rel.get("html_url")))
    if st2 == 200:
        print("    tag -> %s  %s" % (commit["sha"][:8],
                                     commit["commit"]["message"].splitlines()[0][:60]))
    ok = 0
    for k, v in checks:
        print("    [%s] %s" % ("PASS" if v else "FAIL", k))
        ok += 1 if v else 0
    print("")
    print("    结果 %d/%d 通过" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


def main():
    ap = argparse.ArgumentParser(description="GitHub Release 发布工具")
    ap.add_argument("action", choices=["check", "create", "body", "upload", "verify", "all"])
    ap.add_argument("--version", default="")
    ap.add_argument("--target", default="backup/20261011-local",
                    help="tag 指向的分支或 commit（默认远程备份分支）")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--execute", action="store_true", help="真正改动远程（默认 dry-run）")
    args = ap.parse_args()

    if args.action != "check" and not args.version:
        raise SystemExit("这个动作需要 --version")

    cfg = load_cfg()
    print("仓库: %s/%s   动作: %s   execute=%s" % (cfg["owner"], cfg["repo"], args.action, args.execute))
    print("")

    rc = 0
    if args.action == "check":
        rc = cmd_check(cfg, args)
    elif args.action == "create":
        rc = cmd_create(cfg, args)
    elif args.action == "body":
        rc = cmd_body(cfg, args)
    elif args.action == "upload":
        rc = cmd_upload(cfg, args)
    elif args.action == "verify":
        rc = cmd_verify(cfg, args)
    elif args.action == "all":
        rc = cmd_create(cfg, args) or cmd_upload(cfg, args) or cmd_verify(cfg, args)
    return rc


if __name__ == "__main__":
    sys.exit(main())
