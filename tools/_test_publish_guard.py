# -*- coding: utf-8 -*-
"""publish_guard 幂等 + 参数推导 自检（离线，假验收函数）"""
import contextlib
import importlib
import io
import json
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

# —— 模拟发布脚本的全局变量（guard 会从这里自动取参数）——
BOARD = 18
USER_ID = 7
NICK = '测试作者'

import publish_guard as pg  # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  ✅ " if cond else "  ❌ ") + name + (f"  [{detail}]" if detail and not cond else ""))


class FakeCall:
    """替身 subprocess.call：记录调用次数与最后一次命令，返回预设 rc。"""
    def __init__(self, rc=0):
        self.rc = rc
        self.calls = []

    def __call__(self, cmd, timeout=None):
        self.calls.append(list(cmd))
        return self.rc


tmp = Path(tempfile.mkdtemp(prefix='guardtest_'))
fake = FakeCall(0)
pg.subprocess.call = fake

print("=== 1. 参数自动推导（不再吃默认值）===")
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    pg.guard(999001, tmp, expect_images=5)
out = buf.getvalue()
cmd = fake.calls[-1]
check("1.1 自动取到板块 id", '--board' in cmd and cmd[cmd.index('--board') + 1] == '18', str(cmd))
check("1.2 自动取到 uid", cmd[cmd.index('--uid') + 1] == '7', str(cmd))
check("1.3 自动取到作者", cmd[cmd.index('--author') + 1] == '测试作者', str(cmd))
check("1.4 打印了参数来源", 'USER_ID' in out and 'NICK' in out, out[:300])
check("1.5 不再提示「仍在使用默认值」", '仍在使用默认值' not in out)

print("\n=== 2. 幂等：指纹一致且已 PASS → 跳过 ===")
n0 = len(fake.calls)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    r = pg.guard(999001, tmp, expect_images=5)
out = buf.getvalue()
check("2.1 返回 True", r is True)
check("2.2 没有再打网络请求", len(fake.calls) == n0, f"多跑了 {len(fake.calls) - n0} 次")
check("2.3 输出 SKIP", 'SKIP' in out, out[:200])

m = tmp / '_guard_999001.json'
check("2.4 标记文件已落盘", m.exists())
if m.exists():
    d = json.loads(m.read_text(encoding='utf-8'))
    check("2.5 标记内容正确", d.get('status') == 'PASS' and d.get('uid') == '7', str(d)[:200])

print("\n=== 3. force=True 强制重验 ===")
n0 = len(fake.calls)
with contextlib.redirect_stdout(io.StringIO()):
    pg.guard(999001, tmp, expect_images=5, force=True)
check("3.1 强制重验真的跑了", len(fake.calls) == n0 + 1)

print("\n=== 4. 期望值变化 → 不跳过 ===")
n0 = len(fake.calls)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    pg.guard(999001, tmp, expect_images=9)          # 图数从 5 改成 9
check("4.1 指纹变化后重验", len(fake.calls) == n0 + 1)
check("4.2 提示期望值有变化", '变化' in buf.getvalue(), buf.getvalue()[:200])

print("\n=== 5. 上次 FAIL → 不跳过 ===")
fake.rc = 1
try:
    with contextlib.redirect_stdout(io.StringIO()):
        pg.guard(999002, tmp, expect_images=3)
except SystemExit as e:
    check("5.1 FAIL 抛 SystemExit", e.code not in (0, None))
md = json.loads((tmp / '_guard_999002.json').read_text(encoding='utf-8'))
check("5.2 标记记为 FAIL", md.get('status') == 'FAIL', str(md.get('status')))
n0 = len(fake.calls)
fake.rc = 0
try:
    with contextlib.redirect_stdout(io.StringIO()):
        pg.guard(999002, tmp, expect_images=3)
except SystemExit:
    pass
check("5.3 FAIL 之后再跑会重验（不跳过）", len(fake.calls) == n0 + 1)

print("\n=== 6. 脚本里没有这些变量 → 回落默认值并告警 ===")
for k in ('BOARD', 'USER_ID', 'NICK'):
    globals().pop(k, None)
n0 = len(fake.calls)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    pg.guard(999003, tmp, expect_images=2, force=True)
out = buf.getvalue()
cmd = fake.calls[-1]
check("6.1 uid 回落默认 1", cmd[cmd.index('--uid') + 1] == '1', str(cmd))
check("6.2 author 回落默认 老马", cmd[cmd.index('--author') + 1] == '老马', str(cmd))
check("6.3 明确告警默认值", '默认值' in out, out[:300])
check("6.4 不再传 --board（取不到就交给 bbs_verify 自动判定）", '--board' not in cmd, str(cmd))

print("\n=== 7. 无文章目录时不写标记、不崩 ===")
try:
    with contextlib.redirect_stdout(io.StringIO()):
        pg.guard(999004, None, expect_images=1, force=True)
    check("7.1 article_dir=None 正常返回", True)
except Exception as e:
    check("7.1 article_dir=None 正常返回", False, f"{type(e).__name__}: {e}")

print("\n" + "=" * 54)
print(f"通过 {len(PASS)} / {len(PASS) + len(FAIL)}")
if FAIL:
    print("失败：", FAIL)
sys.exit(0 if not FAIL else 1)
