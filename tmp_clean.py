import sys, os, shutil, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
p = r'D:\7tan\7tanAI\dist'
if not os.path.exists(p):
    print('DIST_NOT_EXIST')
    sys.exit(0)
for attempt in range(5):
    try:
        shutil.rmtree(p)
        print('REMOVED_OK attempt', attempt)
        break
    except Exception as e:
        print('attempt', attempt, 'fail:', type(e).__name__, str(e)[:100])
        time.sleep(2)
print('EXISTS_AFTER:', os.path.exists(p))
