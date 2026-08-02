import sys
import os

base = os.path.dirname(__file__)

# Test source pyd as package
print("=== Testing src/security/auth_client.pyd (as package) ===")
sys.path.insert(0, base)
try:
    from src.security import auth_client
    print("OK: imports successfully")
    print("Dir:", [x for x in dir(auth_client) if not x.startswith('_')])
except Exception as e:
    print(f"FAIL: {e}")

# Test dist pyd as package
print()
print("=== Testing dist/_build/src/security/auth_client.pyd (as package) ===")
sys.path.pop(0)
sys.path.insert(0, os.path.join(base, 'dist', '_build'))
try:
    from src.security import auth_client
    print("OK: imports successfully")
    print("Dir:", [x for x in dir(auth_client) if not x.startswith('_')])
except Exception as e:
    print(f"FAIL: {e}")
