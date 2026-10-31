# -*- coding: utf-8 -*-
"""cmd_scope 作用域围栏 + 命令审计 自检（正向 + 反向）

覆盖：
    A. cwd 解析与校验（严格 / 宽松 / 嵌套帧 / 越界拒绝 / 不同盘符不崩）
    B. 越界线索扫描（detect_escape）
    C. 审计落盘与检索（字段完整 / 关键词过滤 / 失败可查）
    D. 端到端：terminal_runner.run_command 在作用域内执行 / 越界被拒 / 留痕
    E. 端到端：agent_spawner 压帧-派工-弹帧后主 Agent 恢复宽松
"""
import importlib.util
import json
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.utils import cmd_scope  # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  ✅ " if cond else "  ❌ ") + name + (f"  [{detail}]" if detail and not cond else ""))


def load_plugin(plugin_id):
    p = ROOT / "data" / "plugins" / plugin_id / "tools.py"
    spec = importlib.util.spec_from_file_location(f"plug_{plugin_id}", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


print("\n=== A. cwd 解析与校验 ===")

# A1 无作用域 = 宽松：默认落到项目根
os_cwd = cmd_scope.resolve_cwd(".")
check("A1 无帧时默认项目根", os_cwd == ROOT.resolve(), str(os_cwd))

# A2 无帧时可访问任意目录（人在场）
check("A2 无帧时允许出项目根", cmd_scope.resolve_cwd(str(ROOT.parent)).is_dir())

# A3 压帧后默认 cwd = 帧根
sub = (ROOT / "data").resolve()
fr = cmd_scope.push(sub, label="t-root", strict=True)
check("A3 帧内默认 cwd = 帧根", cmd_scope.resolve_cwd(".") == sub)
check("A3b current() 返回该帧", cmd_scope.current() is fr)

# A4 帧内相对路径可解析为子目录
check("A4 帧内子目录可解析", cmd_scope.resolve_cwd("logs") == sub / "logs")

# A5 反向：帧内 ../ 越界必须抛 ScopeViolation
try:
    got = cmd_scope.resolve_cwd("..")
    check("A5 帧内 ../ 被拒", False, f"未抛异常，得到 {got}")
except cmd_scope.ScopeViolation as e:
    check("A5 帧内 ../ 被拒", True)

# A6 反向：帧内绝对路径指向外部必须被拒
try:
    got = cmd_scope.resolve_cwd(str(ROOT))
    check("A6 帧内绝对路径越界被拒", False, f"未抛异常，得到 {got}")
except cmd_scope.ScopeViolation:
    check("A6 帧内绝对路径越界被拒", True)

# A7 嵌套帧：内层按内层判，弹内层后回到外层
inner = (ROOT / "data" / "logs").resolve()
fr2 = cmd_scope.push(inner, label="t-inner", strict=True)
check("A7 嵌套：内层按内层根判", cmd_scope.resolve_cwd(".") == inner)
try:
    cmd_scope.resolve_cwd(str(sub))          # sub 在内层之外
    check("A7b 嵌套：内层拒绝外层路径", False)
except cmd_scope.ScopeViolation:
    check("A7b 嵌套：内层拒绝外层路径", True)
cmd_scope.pop(fr2)
check("A7c 弹内层后恢复外层", cmd_scope.current() is fr and cmd_scope.resolve_cwd(".") == sub)

# A8 非严格帧：越界只放行（人在场的宽松语义）
fr3 = cmd_scope.push(sub, label="t-loose", strict=False)
check("A8 非严格帧允许越界", cmd_scope.resolve_cwd(str(ROOT)) == ROOT.resolve())
cmd_scope.pop(fr3)

# A9 不同盘符不崩（Windows）
try:
    other = "Z:\\__nope__" if ROOT.drive.upper() != "Z:" else "Y:\\__nope__"
    try:
        cmd_scope.resolve_cwd(other)
        check("A9 不同盘符：拒绝且不崩", True)
    except cmd_scope.ScopeViolation:
        check("A9 不同盘符：拒绝且不崩", True)
except Exception as e:
    check("A9 不同盘符：拒绝且不崩", False, f"{type(e).__name__}: {e}")

# A10 弹掉剩下的帧，栈应为空
cmd_scope.pop(fr)
check("A10 全部弹出后无帧", cmd_scope.current() is None)

print("\n=== B. 越界线索扫描 ===")
esc = cmd_scope.detect_escape("type C:\\Windows\\win.ini", sub)
check("B1 识别作用域外绝对路径", esc["suspicious"] and any("Windows" in p for p in esc["outside_paths"]),
      str(esc))
esc2 = cmd_scope.detect_escape(f'python "{ROOT / "tools" / "x.py"}"', ROOT)
check("B2 作用域内路径不算可疑", not esc2["suspicious"], str(esc2))
esc3 = cmd_scope.detect_escape("cd .. && dir", sub)
check("B3 识别 cd ..", esc3["suspicious"] and esc3["cd_up"], str(esc3))

print("\n=== C. 审计落盘与检索 ===")
mark = f"selftest-{threading.get_ident()}"
rec = cmd_scope.audit("selftest_tool", f"echo {mark}", "data", sub,
                      rc=0, duration_ms=12.5, stdout="hi", timeout=30)
check("C1 审计写入成功", rec.get("_written") is True, str(rec.get("_write_error")))
check("C2 文件存在", cmd_scope.audit_path().exists())

rows = cmd_scope.query(limit=50, keyword=mark)
check("C3 可按关键词检索到", len(rows) == 1, f"{len(rows)} 条")
if rows:
    r = rows[0]
    need = ["ts", "scope", "cwd", "command", "rc", "duration_ms", "out_len"]
    miss = [k for k in need if k not in r]
    check("C4 记录字段完整", not miss, f"缺 {miss}")

rec_bad = cmd_scope.audit("selftest_tool", f"exit 1 {mark}", ".", ROOT.resolve(),
                          rc=1, duration_ms=3, error="boom")
rows_bad = cmd_scope.query(limit=50, keyword=f"exit 1 {mark}", only_failed=True)
check("C5 失败命令可查（only_failed）", len(rows_bad) == 1)
check("C6 错误信息保留", rows_bad and rows_bad[0].get("error") == "boom")

rows_esc = cmd_scope.query(limit=20, keyword="Windows", only_escape=False)
check("C7 无匹配时返回空列表", isinstance(cmd_scope.query(limit=5, keyword="__绝不存在的串__"), list))

print("\n=== D. 端到端：terminal_runner ===")
tr = load_plugin("terminal_runner")

# D1 无作用域：正常执行
out = tr.run_command("echo scope-free", cwd=".")
check("D1 无作用域可执行", "scope-free" in out, out[:120])

# D2 作用域内执行 + 留痕（scope 应记为 worker 标签）
fr4 = cmd_scope.push(sub, label="w-selftest", strict=True)
out2 = tr.run_command("echo inside-scope", cwd=".")
check("D2 作用域内可执行", "inside-scope" in out2, out2[:120])
rows2 = cmd_scope.query(limit=10, keyword="echo inside-scope")
check("D2b 执行留痕且标识作用域", rows2 and rows2[0].get("scope") == "w-selftest",
      str(rows2[0].get("scope") if rows2 else "无记录"))

# D3 反向：越界 cwd 必须被拒绝，且不得执行
before = len(cmd_scope.query(limit=500, keyword="echo outside-scope"))
out3 = tr.run_command("echo outside-scope", cwd=str(ROOT))
check("D3 越界 cwd 被拒绝", "已拒绝执行" in out3 and "越界" in out3, out3[:160])
check("D3b 被拒的命令没有真的执行", "outside-scope" not in out3.split("cwd")[0] or "🚫" in out3)
rows3 = cmd_scope.query(limit=10, keyword="echo outside-scope")
check("D3c 被拒绝也留痕（refused/error 有值）",
      rows3 and (rows3[0].get("error") or "").startswith("cwd 越界"),
      str(rows3[0].get("error") if rows3 else "无记录"))

# D4 反向：命令内容触碰作用域外路径 → 提示 + 审计标记
out4 = tr.run_command("type C:\\Windows\\win.ini", cwd=".")
rows4 = cmd_scope.query(limit=5, keyword="win.ini")
check("D4 越界线索记入审计", rows4 and rows4[0].get("escape") is True,
      str(rows4[0].get("escape") if rows4 else "无记录"))

# D5 护栏拦截的命令也要留痕
tr.run_command("请注意这不是命令", cwd=".")
rows5 = cmd_scope.query(limit=5, keyword="请注意这不是命令")
check("D5 护栏拦截也留痕", rows5 and rows5[0].get("refused") is True)

# D6 审计检索工具可用
txt = tr.cmd_audit_query(limit=3, keyword="echo inside-scope")
check("D6 cmd_audit_query 能查到", "inside-scope" in txt, txt[:160])

cmd_scope.pop(fr4)
check("D7 弹帧后主 Agent 恢复宽松", cmd_scope.current() is None
      and tr.run_command("echo back-to-loose", cwd=".").find("back-to-loose") >= 0)

print("\n=== E. 端到端：agent_spawner 压帧/弹帧 ===")
sp = load_plugin("agent_spawner")
frame = sp._push_scope(sub, "w-fake", "任务书")
check("E1 压帧成功", frame is not None and cmd_scope.current() is frame)
try:
    cmd_scope.resolve_cwd(str(ROOT))
    check("E2 帧内越界被拒", False)
except cmd_scope.ScopeViolation:
    check("E2 帧内越界被拒", True)
sp._pop_scope(frame)
check("E3 弹帧后恢复宽松", cmd_scope.current() is None)

# E4 cwd_root 指向不存在目录 → 明确拒绝，不启动
r = sp.spawn_worker(task="x", cwd_root=str(ROOT / "__不存在的目录__"))
check("E4 不存在的工作根目录被拒", "不存在" in r, r[:120])

print("\n" + "=" * 60)
print(f"通过 {len(PASS)} / {len(PASS) + len(FAIL)}")
if FAIL:
    print("失败：")
    for f in FAIL:
        print("  ·", f)
sys.exit(0 if not FAIL else 1)
