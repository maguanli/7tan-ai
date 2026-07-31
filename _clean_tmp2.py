import os
for f in ("_list_dist2.py", "_v.py"):
    p = os.path.join(r"D:\7tan\7tanAI", f)
    if os.path.exists(p):
        os.remove(p)
        print("DEL", f)
print("TMP-CLEANED")
