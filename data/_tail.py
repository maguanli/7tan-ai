# -*- coding: utf-8 -*-
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
if len(sys.argv) < 2:
    print("usage: _tail.py <path> [n]")
    sys.exit(1)
p = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 40
try:
    lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
except Exception as e:
    print("ERR", e)
    sys.exit(1)
print("--- %s  (%d lines)  last %d ---" % (p, len(lines), n))
print("\n".join(lines[-n:]))
