# -*- coding: utf-8 -*-
import os, sys

def list_dirs(root):
    try:
        items = os.listdir(root)
    except Exception as e:
        print(f"ERROR list {root}: {e}")
        return
    for d in sorted(items):
        p = os.path.join(root, d)
        if os.path.isdir(p):
            print(d)

print("=== C:/ ===")
list_dirs('C:/')
print("=== D:/ ===")
list_dirs('D:/')
