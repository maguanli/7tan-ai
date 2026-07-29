print("step 1")
import sys
sys.path.insert(0, ".")
print("step 2")
import traceback
try:
    print("step 3 - importing THEME")
    from src.ui.theme import THEME
    print("step 4 - THEME imported, DARK_STYLESHEET")
    exec(open("src/ui/app.py").read().split('import math')[0])
    print("step 5 - stylesheet defined OK")
except Exception as e:
    traceback.print_exc()
    print("FAILED:", e)
