# -*- coding: utf-8 -*-
"""探测本地浏览器 CDP 调试端口，用于提取公众号后台页面数据"""
import subprocess
import socket
import sys

print("=== 1. 进程命令行扫描（找 remote-debugging-port）===")
try:
    r = subprocess.run(
        ['wmic', 'process', 'get', 'CommandLine', '/format:list'],
        capture_output=True, text=True, timeout=30, encoding='gbk', errors='ignore'
    )
    for line in r.stdout.splitlines():
        low = line.lower()
        if 'remote-debugging' in low or '9222' in line or '7tan' in low:
            print(line.strip()[:300])
except Exception as e:
    print("wmic 扫描失败:", e)

print("\n=== 2. 端口探测 ===")
for port in [9222, 9223, 9224, 9225, 9333, 17890, 9515]:
    s = socket.socket()
    s.settimeout(0.6)
    try:
        s.connect(('127.0.0.1', port))
        print(f"端口 {port}: 开放")
        try:
            s.sendall(b'GET /json/version HTTP/1.1\r\nHost: localhost\r\n\r\n')
            data = s.recv(600).decode('utf-8', 'ignore')
            print("  ->", data[:200].replace('\r\n', ' | '))
        except Exception as e:
            print("  读取失败:", e)
    except Exception:
        print(f"端口 {port}: 关闭")
    finally:
        s.close()

print("\n=== 3. 浏览器相关进程 ===")
try:
    r = subprocess.run(
        ['tasklist'],
        capture_output=True, text=True, timeout=30, encoding='gbk', errors='ignore'
    )
    for line in r.stdout.splitlines():
        low = line.lower()
        if any(k in low for k in ['chrome', 'msedge', '7tan', 'python']):
            print(line.strip()[:120])
except Exception as e:
    print("tasklist 失败:", e)
