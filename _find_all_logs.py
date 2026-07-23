import glob, os

# Find all log files
for pattern in ["logs/*.log", "*.log", "logs/*.txt"]:
    files = glob.glob(pattern)
    for f in sorted(files):
        mtime = os.path.getmtime(f)
        size = os.path.getsize(f)
        print(f"{f}  ({size}B, modified: {mtime})")
