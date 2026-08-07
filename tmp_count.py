import sys, os, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
p = r'D:\7tan\7tanAI\dist'
if os.path.exists(p):
    n = 0
    total = 0
    for root, dirs, files in os.walk(p):
        n += len(files)
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except Exception:
                pass
    print('DIST_FILES:', n, 'SIZE_MB:', round(total/1048576, 1))
else:
    print('DIST_NOT_EXIST')
