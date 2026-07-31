import os
root = r"D:\7tan\7tanAI"
for f in ["_final_check.py", "_build_final.bat", "build_final_log.txt", "_del_tmp.py", "_sync_rebuild.py"]:
    p = os.path.join(root, f)
    if os.path.exists(p):
        os.remove(p)
        print("DEL", f)
print("CLEAN-OK")
