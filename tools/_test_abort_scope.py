"""abort_signal 作用域隔离验证。
重点验的是两个真故障：
  1) 嵌套污染：Worker 超时 set 自己的信号，不能把主 Agent 一起停掉
  2) 跨线程连坐：A 中止不影响 B
"""
import sys, threading, time, subprocess
from pathlib import Path

root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from src.utils import abort_signal as A

ok, fail = [], []


def check(name, cond, extra=""):
    (ok if cond else fail).append(name)
    print(("  PASS  " if cond else "  FAIL  ") + name + (("  " + extra) if extra else ""))


print("=" * 62)
print("① 基线：单线程注册 / set / 注销（行为必须与改造前一致）")
A.reset()
ev = threading.Event()
A.register(ev)
check("注册后未中止", A.is_aborted() is False)
ev.set()
check("set 后判中止", A.is_aborted() is True)
check("原因码默认 user_aborted", A.abort_reason() == "user_aborted")
try:
    A.check_abort()
    check("check_abort 抛异常", False)
except A.AbortedError:
    check("check_abort 抛异常", True)
A.unregister(ev)
check("注销后恢复", A.is_aborted() is False)

print("=" * 62)
print("② 嵌套污染（本次修复的核心）：主 Agent + Worker 同线程")
A.reset()
sig_main = threading.Event()
sig_worker = threading.Event()
sig_worker.reason = "timeout"

A.register(sig_main)          # 主 Agent 注册
check("外层未中止", A.is_aborted() is False)

A.register(sig_worker)        # Worker 在同一个线程里注册（栈顶）
sig_worker.set()              # Worker 超时
check("内层 set 后判中止", A.is_aborted() is True)
check("原因码取内层 timeout", A.abort_reason() == "timeout", A.abort_reason())

A.unregister(sig_worker)      # Worker 结束，注销
check("Worker 注销后，主 Agent 不受超时连累", A.is_aborted() is False)
check("原因码回到外层默认", A.abort_reason() == "user_aborted")
A.unregister(sig_main)
check("全部注销后干净", A.scope_stats() == {}, str(A.scope_stats()))

print("=" * 62)
print("③ 跨线程连坐：A 中止不影响 B")
A.reset()
result = {}
barrier = threading.Barrier(2)


def worker(name, should_abort):
    ev = threading.Event()
    A.register(ev)
    barrier.wait()                      # 两边都注册好再动手
    if should_abort:
        ev.set()
    time.sleep(0.15)
    result[name] = A.is_aborted()
    A.unregister(ev)


t1 = threading.Thread(target=worker, args=("A", True))
t2 = threading.Thread(target=worker, args=("B", False))
t1.start(); t2.start(); t1.join(); t2.join()
check("A 自己判中止", result.get("A") is True)
check("B 未受连坐", result.get("B") is False, str(result))

print("=" * 62)
print("④ 显式作用域：按会话隔离")
A.reset()
s1, s2 = threading.Event(), threading.Event()
A.register(s1, scope="session-1")
A.register(s2, scope="session-2")
s1.set()
check("session-1 中止", A.is_aborted(scope="session-1") is True)
check("session-2 不受影响", A.is_aborted(scope="session-2") is False)
A.reset()
check("reset 清空所有作用域", A.scope_stats() == {})

print("=" * 62)
print("⑤ run_with_abort：中止即杀进程树")
A.reset()
ev = threading.Event()
A.register(ev)
threading.Timer(0.6, ev.set).start()
t0 = time.time()
try:
    A.run_with_abort([sys.executable, "-c", "import time; time.sleep(30)"], timeout=25)
    check("长命令被中止", False, "没抛 AbortedError")
except A.AbortedError:
    cost = time.time() - t0
    check("长命令被中止", cost < 5.0, "%.1fs 内杀掉" % cost)
except Exception as e:
    check("长命令被中止", False, "%s: %s" % (type(e).__name__, e))
A.unregister(ev)

print("=" * 62)
print("⑥ run_with_abort：正常命令不受影响")
A.reset()
rc, out, err = A.run_with_abort([sys.executable, "-c", "print('hello')"], timeout=20)
check("正常命令返回 0", rc == 0, "rc=%s" % rc)
check("输出正确", "hello" in (out or ""), repr(out))

print("=" * 62)
print("通过 %d 项，失败 %d 项" % (len(ok), len(fail)))
if fail:
    print("失败项:", fail)
sys.exit(1 if fail else 0)
