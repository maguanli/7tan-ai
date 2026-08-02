import sys
import os

# Test source pyd
print("=== Testing src/security/auth_client.pyd ===")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'security'))
try:
    import auth_client
    print("OK: imports successfully")
    print("Dir:", [x for x in dir(auth_client) if not x.startswith('_')])
except Exception as e:
    print(f"FAIL: {e}")

# Test dist pyd
print()
print("=== Testing dist/_build/src/security/auth_client.pyd ===")
sys.path.pop(0)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'dist', '_build', 'src', 'security'))
try:
    import auth_client
    print("OK: imports successfully")
    print("Dir:", [x for x in dir(auth_client) if not x.startswith('_')])
except Exception as e:
    print(f"FAIL: {e}")

# Test tools pyd
print()
print("=== Testing tools/_tmp_authbuild/auth_client.pyd ===")
sys.path.pop(0)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools', '_tmp_authbuild'))
try:
    import auth_client
    print("OK: imports successfully")
    print("Dir:", [x for x in dir(auth_client) if not x.startswith('_')])
except Exception as e:
    print(f"FAIL: {e}")
