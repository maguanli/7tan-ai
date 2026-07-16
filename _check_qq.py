import os
import sys

# Check for qq_bridge in dist
for root, dirs, files in os.walk("D:\\7tan\\7tanAI\\dist"):
    if "qq_bridge" in dirs:
        path = os.path.join(root, "qq_bridge")
        print(f"Found qq_bridge at: {path}")
        for f in os.listdir(path):
            print(f"  {f}")
        # Check if there's a tools.py
        tp = os.path.join(path, "tools.py")
        if os.path.exists(tp):
            with open(tp, "r", encoding="utf-8") as fp:
                content = fp.read()
            if "def register_tool" in content:
                print("  ✅ Has register_tool definition")
            else:
                print("  ❌ Does NOT have register_tool definition")
                print("  First 1000 chars:")
                print(content[:1000])
        break
