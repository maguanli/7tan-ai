"""Copy fixed qq_bridge plugin from source to dist directory"""
import shutil
import os

src = "D:\\7tan\\7tanAI\\data\\plugins\\qq_bridge\\tools.py"
dst = "D:\\7tan\\7tanAI\\dist\\7tan-editor\\_internal\\data\\plugins\\qq_bridge\\tools.py"

print(f"Source exists: {os.path.exists(src)}")
print(f"Source size: {os.path.getsize(src)} bytes")
print(f"Dest exists before: {os.path.exists(dst)}")
if os.path.exists(dst):
    print(f"Dest size before: {os.path.getsize(dst)} bytes")

# Make backup of old version
backup = dst + ".bak"
shutil.copy2(dst, backup)
print(f"Backup saved: {backup} (size: {os.path.getsize(backup)})")

# Copy fixed version
shutil.copy2(src, dst)
print(f"Copied {src} -> {dst}")
print(f"Dest size after: {os.path.getsize(dst)} bytes")

# Verify the new file has register_tool defined
with open(dst, 'r', encoding='utf-8') as f:
    content = f.read()

if 'def register_tool' in content:
    print("✅ New file HAS register_tool definition!")
else:
    print("❌ ERROR: New file does NOT have register_tool definition!")
    
# Also check if _internal/src/plugins/manager.py uses the right PLUGIN_DIR
mgr_path = "D:\\7tan\\7tanAI\\dist\\7tan-editor\\_internal\\src\\plugins\\manager.py"
if os.path.exists(mgr_path):
    print(f"\nManager.py exists at dist: {os.path.getsize(mgr_path)} bytes")
