import sys, os, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
path = r'D:\7tan\7tanAI\build_run_20260807.log'
for _ in range(12):
    try:
        data = open(path, 'r', encoding='utf-8', errors='replace').read()
    except Exception as e:
        data = f'ERR {e}'
    lines = data.splitlines()
    print(f'--- SIZE {len(data)} LINES {len(lines)} ---')
    print('\n'.join(lines[-25:]))
    # 检测结束标志
    if 'DONE!' in data or 'ERROR' in data[-2000:] or 'Press any key' in data:
        print('=== FINISHED or ERROR detected ===')
        break
    time.sleep(20)
