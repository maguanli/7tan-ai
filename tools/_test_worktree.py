# -*- coding: utf-8 -*-
"""agent_spawner 的 git worktree 隔离 自检（正向 + 反向）"""
import importlib.util
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  ✅ " if cond else "  ❌ ") + name + (f"  [{detail}]" if detail and not cond else ""))


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo)] + list(args),
                          capture_output=True, text=True, timeout=60)


spec = importlib.util.spec_from_file_location(
    "plug_sp", ROOT / "data" / "plugins" / "agent_spawner" / "tools.py")
sp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sp)

tmp = Path(tempfile.mkdtemp(prefix="wt_test_"))
repo = tmp / "repo"
repo.mkdir()
git(repo, "init")
git(repo, "config", "user.email", "t@t.t")
git(repo, "config", "user.name", "t")
(repo / "app.py").write_text("print('v1')\n", encoding="utf-8")
git(repo, "add", "-A")
git(repo, "commit", "-m", "init")

print("=== 1. 建 worktree ===")
wt, branch, err = sp._make_worktree(repo, "w-test1")
check("1.1 创建成功", wt is not None and wt.is_dir(), err)
check("1.2 返回分支名", branch == "ticket/w-test1", str(branch))
check("1.3 worktree 里有仓库文件", (wt / "app.py").exists() if wt else False)
check("1.4 分支已创建", "ticket/w-test1" in git(repo, "branch", "--list").stdout)

print("\n=== 2. 改动隔离在 worktree 内 ===")
if wt:
    (wt / "app.py").write_text("print('v2')\n", encoding="utf-8")
    (wt / "new_feature.py").write_text("x=1\n", encoding="utf-8")
    d = sp._worktree_diff(wt)
    check("2.1 diff 能看到改动", "app.py" in d["dirty"] and "new_feature.py" in d["dirty"], str(d)[:200])
    check("2.2 diffstat 有统计", "app.py" in d["stat"], str(d["stat"])[:200])
    main_status = git(repo, "status", "--short").stdout.strip()
    check("2.3 主工作区未被污染", main_status == "", f"主仓库 status: {main_status!r}")
    check("2.4 主工作区文件仍是 v1", "v1" in (repo / "app.py").read_text(encoding="utf-8"))
    check("2.5 没有往仓库里塞 .gitignore", not (repo / ".gitignore").exists())

print("\n=== 3. 无改动时如实报告 ===")
wt2, br2, e2 = sp._make_worktree(repo, "w-test2")
if wt2:
    d2 = sp._worktree_diff(wt2)
    check("3.1 无改动时 dirty 为空", d2["dirty"].strip() == "", repr(d2["dirty"]))

print("\n=== 4. 反向：非 git 目录 → 明确报错，不崩 ===")
plain = tmp / "notrepo"
plain.mkdir()
wt3, br3, err3 = sp._make_worktree(plain, "w-test3")
check("4.1 拒绝创建", wt3 is None)
check("4.2 带回了错误原因", bool(err3), "错误信息为空")
print("     错误原因：", (err3 or "")[:120].replace("\n", " "))

print("\n=== 5. 反向：同名 worktree 重复创建 → 报错而非静默覆盖 ===")
wt4, br4, err4 = sp._make_worktree(repo, "w-test1")
check("5.1 重复创建被拒", wt4 is None)
check("5.2 错误信息非空", bool(err4))

# 清理
for name in ("w-test1", "w-test2"):
    git(repo, "worktree", "remove", "--force", str(repo.parent / f"{repo.name}-worktrees" / name))
shutil.rmtree(tmp, ignore_errors=True)

print("\n" + "=" * 50)
print(f"通过 {len(PASS)} / {len(PASS) + len(FAIL)}")
if FAIL:
    print("失败：", FAIL)
sys.exit(0 if not FAIL else 1)
