import socket

# 常见代理端口探测
ports = [7890, 7897, 10809, 1080, 8888, 10808, 8118, 9090]
for p in ports:
    s = socket.socket()
    s.settimeout(1)
    try:
        if s.connect_ex(('127.0.0.1', p)) == 0:
            print(f'PORT_OPEN: {p}')
    finally:
        s.close()

# 检查系统代理注册表
import subprocess
try:
    r = subprocess.run(['reg', 'query', r'HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings'],
                       capture_output=True, text=True, timeout=10)
    for line in r.stdout.splitlines():
        if 'Proxy' in line:
            print('REG:', line.strip())
except Exception as e:
    print('REG_ERR:', e)
