import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def tail(path, n):
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        print(f'===== {path} (总{len(lines)}行, 末尾{n}行) =====')
        print(''.join(lines[-n:]))
    except Exception as e:
        print(f'===== {path} 读取失败: {e} =====')

tail('logs/app_2026-08-16.log', 60)
tail('logs/cloudflared_debug.log', 40)
tail('logs/web9900.log', 20)
