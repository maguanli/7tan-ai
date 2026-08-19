import os

ud = r"C:\Users\Administrator\AppData\Local\Google\Chrome\User Data"
sess = os.path.join(ud, "Default", "Sessions")
print("Sessions 目录存在:", os.path.exists(sess))
if os.path.exists(sess):
    for f in os.listdir(sess):
        p = os.path.join(sess, f)
        print(" ", f, os.path.getsize(p), "bytes")

# 检查 Last Session / Last Tabs
for name in ["Last Session", "Last Tabs", "Current Session", "Current Tabs"]:
    p = os.path.join(ud, "Default", name)
    print(name, "->", "存在" if os.path.exists(p) else "不存在")
