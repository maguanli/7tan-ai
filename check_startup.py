import py_compile
import sys

# 1. Check app.py syntax
try:
    py_compile.compile("src/ui/app.py", doraise=True)
    print("STEP1: app.py syntax OK")
except py_compile.PyCompileError as e:
    print("STEP1: app.py syntax FAIL -", str(e))
    sys.exit(1)

# 2. Check dependencies
deps = {"apscheduler": "apscheduler"}
missing = []
for name, import_name in deps.items():
    try:
        __import__(import_name)
        print(f"STEP2: {name} OK")
    except ImportError:
        missing.append(name)
        print(f"STEP2: {name} MISSING")

if missing:
    print(f"MISSING DEPS: {missing}")
    sys.exit(1)

print("ALL CHECKS PASSED")
