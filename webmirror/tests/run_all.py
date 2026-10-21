"""跑一遍全部测试脚本，汇总结果。"""
import subprocess
import sys
import os

try:                      # 控制台可能是 GBK，避免打印失败
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:         # noqa: BLE001
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

TESTS = [
    "test_paths.py",
    "test_encoding.py",
    "test_minimal_html.py",
    "test_asset_scope.py",
    "test_css_relative.py",
    "test_resume.py",
    "repro_encoding.py",
    "verify_no_inject.py",
    "api_e2e.py",
]

ok, bad = [], []
for t in TESTS:
    p = os.path.join(HERE, t)
    if not os.path.isfile(p):
        print("SKIP", t)
        continue
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, p], cwd=ROOT, env=env,
                       capture_output=True, text=True, errors="replace",
                       encoding="utf-8", timeout=900)
    tail = (r.stdout or "").strip().splitlines()[-3:]
    passed = r.returncode == 0
    print(f"[{'PASS' if passed else 'FAIL'}] {t}  rc={r.returncode}")
    for line in tail:
        print("        ", line)
    (ok if passed else bad).append(t)

print()
print(f"通过 {len(ok)} / 失败 {len(bad)}")
if bad:
    print("失败列表:", bad)
sys.exit(1 if bad else 0)
