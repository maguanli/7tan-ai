# -*- coding: utf-8 -*-
"""把本地仓库同步到 GitHub —— 剔除超限媒体后重建镜像再推。

为什么不能直接 push 原仓库：
    GitHub 单文件硬上限 100MB，而仓库里有 3 个超限 mp4（101~124MB），
    无论网络多好都推不上去。整个仓库 1.75GB，其中「镜像同事_小说/」占 953MB，
    代码本体仅约 20MB。所以每次同步都走 filter-repo 镜像。

同步内容：
    · 分支 backup/20261011-local（普通推送，可快进）
    · 分支 main（强制覆盖：main 原是 8 月的首发快照，与当前历史无共同祖先）
    · tag 指定版本（强制移动）

用法：
    python tools/gh_push_mirror.py                  # 只看计划（dry-run）
    python tools/gh_push_mirror.py --execute        # 真正推送
    python tools/gh_push_mirror.py --execute --main-only
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time

LOCAL = r"D:\7tan\7tanAI"
MIRROR = r"D:\7tan\repo-push.git"
MEDIA = "镜像同事_小说"
REMOTE = "https://github.com/maguanli/7tan-ai.git"
BRANCH = "backup/20261011-local"
TAG = "v1.0.23"


def run(args, cwd=None, timeout=3600):
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    t0 = time.time()
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout, env=env)
    return p.returncode, (p.stdout or "") + (p.stderr or ""), time.time() - t0


def dirsize(p):
    s = 0
    for root, _dirs, files in os.walk(p):
        for f in files:
            try:
                s += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return s


def main() -> int:
    execute = "--execute" in sys.argv
    main_only = "--main-only" in sys.argv

    rc, out, _ = run(["git", "rev-parse", "HEAD"], cwd=LOCAL)
    if rc != 0:
        print("读取本地 HEAD 失败")
        return 1
    local_head = out.strip()
    print("本地 HEAD : %s" % local_head)

    # 已是最新则不必重建
    if os.path.exists(MIRROR):
        rc, out, _ = run(["git", "config", "--get", "remote.gh.url"], cwd=MIRROR)
        if rc == 0:
            rc2, out2, _ = run(["git", "ls-remote", "gh", "refs/heads/main"], cwd=MIRROR, timeout=300)
            if rc2 == 0 and out2.split():
                remote_main = out2.split()[0]
                rc3, out3, _ = run(["git", "rev-parse", "HEAD"], cwd=MIRROR)
                if rc3 == 0 and out3.strip() == remote_main:
                    print("远端 main 已与镜像 HEAD 一致（%s）" % remote_main[:8])
                    if not main_only:
                        print("提示：镜像可能落后于本地，仍将重建。")
                print("远端 main : %s" % remote_main[:8])

    if os.path.exists(MIRROR):
        print("\n清理旧镜像 ...")
        shutil.rmtree(MIRROR, ignore_errors=True)

    print("\n== 1. clone --mirror ==")
    rc, out, dur = run(["git", "clone", "--mirror", LOCAL, MIRROR], timeout=2400)
    print("   rc=%d  %.1fs" % (rc, dur))
    if rc != 0:
        print("   " + out.strip()[:400])
        return 1
    print("   镜像 %.1f MB" % (dirsize(MIRROR) / 1048576))

    print("\n== 2. 剔除 %s ==" % MEDIA)
    rc, out, dur = run(["git", "filter-repo", "--invert-paths", "--path", MEDIA, "--force"],
                       cwd=MIRROR, timeout=3600)
    print("   rc=%d  %.1fs" % (rc, dur))
    print("   过滤后 %.1f MB" % (dirsize(MIRROR) / 1048576))

    rc, out, _ = run(["git", "rev-parse", "HEAD"], cwd=MIRROR)
    mirror_head = out.strip()
    print("   镜像 HEAD : %s" % mirror_head)
    rc, out, _ = run(["git", "log", "--oneline", "-3"], cwd=MIRROR)
    print("   最近提交 :")
    print("   " + out.strip().replace("\n", "\n   "))

    if not execute:
        print("\n[dry-run] 计划执行：")
        print("   git push gh %s" % BRANCH)
        print("   git push gh HEAD:main --force")
        print("   git push gh refs/tags/%s --force" % TAG)
        print("\n加 --execute 真正推送。")
        return 0

    rc, out, _ = run(["git", "remote", "add", "gh", REMOTE], cwd=MIRROR)
    print("\n== 3. remote add rc=%d ==" % rc)

    if not main_only:
        print("\n== 4. 推送分支 %s ==" % BRANCH)
        rc, out, dur = run(["git", "push", "gh", "HEAD:refs/heads/%s" % BRANCH],
                           cwd=MIRROR, timeout=2400)
        print("   rc=%d  %.1fs" % (rc, dur))
        print("   " + out.strip()[-400:].replace("\n", "\n   "))

    print("\n== 5. 覆盖 main ==")
    rc, out, dur = run(["git", "push", "gh", "HEAD:refs/heads/main", "--force"],
                       cwd=MIRROR, timeout=2400)
    print("   rc=%d  %.1fs" % (rc, dur))
    print("   " + out.strip()[-400:].replace("\n", "\n   "))

    if not main_only:
        print("\n== 6. 移动 tag %s ==" % TAG)
        rc, out, _ = run(["git", "tag", "-f", TAG, mirror_head], cwd=MIRROR)
        print("   tag -f rc=%d" % rc)
        rc, out, dur = run(["git", "push", "gh", "refs/tags/%s" % TAG, "--force"],
                           cwd=MIRROR, timeout=900)
        print("   push tag rc=%d  %.1fs" % (rc, dur))

    print("\n== 7. 回验 ==")
    rc, out, _ = run(["git", "ls-remote", "gh",
                      "refs/heads/main", "refs/heads/%s" % BRANCH,
                      "refs/tags/%s" % TAG], cwd=MIRROR, timeout=300)
    print(out.strip())
    print("\n镜像 HEAD : %s" % mirror_head)
    print("本地 HEAD : %s" % local_head)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
