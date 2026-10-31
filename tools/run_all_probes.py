# -*- coding: utf-8 -*-
"""跑全部并发相关探针，汇总结果。"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBES = [
    ("并发/隔离/串行/单例", "tools/concurrency_probe.py", []),
    ("并行路径作用域", "tools/probe_parallel_scope.py", []),
    ("资源租约", "tools/probe_lease.py", []),
    ("工具入口接入", "tools/probe_tool_lease.py", []),
]

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

rows = []
for label, script, extra in PROBES:
    r = subprocess.run([sys.executable, str(ROOT / script)] + extra,
                       cwd=str(ROOT), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=600)
    out = (r.stdout or "") + (r.stderr or "")
    tail = ""
    for line in out.splitlines():
        s = line.strip()
        if s.startswith(("断言", "汇总")):
            tail = s
    fails = [l.strip() for l in out.splitlines()
             if l.strip().startswith("·") or l.strip().startswith("未通过：")]
    rows.append((label, script, r.returncode, tail, fails))

print("=" * 78)
print("全量回归")
print("=" * 78)
ok_all = True
for label, script, rc, tail, fails in rows:
    mark = "PASS" if rc == 0 else "FAIL"
    if rc != 0:
        ok_all = False
    print(f"  [{mark}] {label:16s} {script}")
    if tail:
        print(f"         {tail}")
    for f in fails[:8]:
        print(f"         {f}")

print("=" * 78)
print("总体：" + ("全部通过" if ok_all else "有未通过项"))
sys.exit(0 if ok_all else 1)
