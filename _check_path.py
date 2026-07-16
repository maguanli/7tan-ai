import sys
print("sys.path:")
for p in sys.path:
    print(f"  {p}")
print()
# Check if src is accessible
try:
    import src.tools.registry
    print("src.tools.registry imported OK")
except Exception as e:
    print(f"Failed to import src.tools.registry: {e}")
