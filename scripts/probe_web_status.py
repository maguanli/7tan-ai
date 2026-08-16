import sys, io, socket, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print('========== 1. 进程探测 ==========')
try:
    import psutil
    for p in psutil.process_iter(['pid', 'name', 'create_time']):
        try:
            n = (p.info['name'] or '').lower()
            if any(k in n for k in ('python', 'cloud')):
                import datetime
                t = datetime.datetime.fromtimestamp(p.info['create_time']).strftime('%m-%d %H:%M:%S')
                print(f"  PID={p.info['pid']:<7} {p.info['name']:<18} 启动于 {t}")
        except Exception:
            pass
except Exception as e:
    print('  psutil 不可用:', e)

print('========== 2. 端口 9900 探测 ==========')
for host in ('127.0.0.1', '192.168.2.10'):
    s = socket.socket()
    s.settimeout(2)
    try:
        s.connect((host, 9900))
        print(f'  {host}:9900 -> 可连接 ✓')
    except Exception as e:
        print(f'  {host}:9900 -> 连接失败: {e}')
    finally:
        s.close()

print('========== 3. 隧道可访问性(经 cloudflare 域名) ==========')
import urllib.request
for url in ('https://nail-attribute-similarly-bind.trycloudflare.com/api/health',
            'https://copy-mouth-loose-stopped.trycloudflare.com/api/health'):
    try:
        r = urllib.request.urlopen(url, timeout=10)
        print(f'  {url} -> {r.status}')
    except Exception as e:
        print(f'  {url} -> 失败: {e}')

print('========== 4. 日志尾部 ==========')
def tail(path, n):
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        print(f'===== {path} (共{len(lines)}行) =====')
        print(''.join(lines[-n:]))
    except Exception as e:
        print(f'===== {path} 读取失败: {e} =====')

tail('logs/cloudflared.log', 15)
tail('logs/app_2026-08-16.log', 40)
