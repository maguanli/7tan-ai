"""Emergency app.py recovery from pyc"""
import marshal
import sys
import os

pyc_path = os.path.join(os.path.dirname(__file__), "src", "ui", "__pycache__", "app.cpython-312.pyc")
out_path = os.path.join(os.path.dirname(__file__), "src", "ui", "app.py")

print(f"Reading {pyc_path}")
with open(pyc_path, "rb") as f:
    f.read(16)  # Python 3.12 header
    code = marshal.load(f)

print(f"Code loaded: {len(code.co_names)} names")

# Try to install uncompyle6
import subprocess
try:
    import uncompyle6
    print("uncompyle6 already installed")
except ImportError:
    print("Installing uncompyle6...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "uncompyle6", "-q"])

# Now decompile
import uncompyle6
from io import StringIO

buf = StringIO()
uncompyle6.decompile(3.12, code, buf)
source = buf.getvalue()

with open(out_path, "w", encoding="utf-8") as f:
    f.write(source)
print(f"Recovered {len(source)} bytes to {out_path}")
