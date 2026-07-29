import py_compile
import sys

files = ["main.py", "src/ui/app.py", "src/ui/console_panel.py", "src/ui/pro_status_widget.py", "src/utils/logger.py"]
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print("OK: " + f)
    except py_compile.PyCompileError as e:
        print("FAIL: " + f + " - " + str(e))
        sys.exit(1)
print("All OK")
