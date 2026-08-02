import sys
import os

base = os.path.dirname(__file__)

# Test tools pyd as package
print("=== Testing tools/_tmp_authbuild/auth_client.pyd (as package from tools/) ===")
# We need src/security/__init__.py to exist for the relative imports to work
sys.path.insert(0, os.path.join(base, 'tools', '_tmp_authbuild'))
# The pyd has relative imports, so we need to trick it
# Actually, let's copy the __init__.py
try:
    from src.security import auth_client
    print("FAIL - that shouldn't work from this path")
except Exception as e:
    print(f"Expected fail: {e}")

# Actually, let's test by replacing in-place
print()
print("=== Testing: copy tools pyd to src/security and import ===")
import shutil
src_pyd = os.path.join(base, 'src', 'security', 'auth_client.pyd')
backup_pyd = os.path.join(base, 'src', 'security', 'auth_client_broken.pyd')
# Backup broken one
if not os.path.exists(backup_pyd):
    shutil.copy2(src_pyd, backup_pyd)
# Copy tools pyd
tools_pyd = os.path.join(base, 'tools', '_tmp_authbuild', 'auth_client.pyd')
shutil.copy2(tools_pyd, src_pyd)

sys.path.insert(0, base)
try:
    from src.security import auth_client
    print("OK: imports successfully!")
    print("Dir:", [x for x in dir(auth_client) if not x.startswith('_')])
except Exception as e:
    print(f"FAIL: {e}")
