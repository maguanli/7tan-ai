import glob, os
files = sorted(glob.glob("logs/*.log"))
for f in files[-5:]:
    print(f)
