# -*- coding: utf-8 -*-
"""深度验证 exe：启动后检查 API 端口、进程状态、日志输出"""
import subprocess, time, os, socket, urllib.request

out = r'D:\7tan\7tanAI\_tmp_full_test.txt'
result = []

exe = r'D:\7tan\7tanAI\dist\7tan-editor\7tan-editor.exe'
exe_dir = os.path.dirname(exe)

# 清旧日志
for name in ('error.log', 'app.log', 'run.log', 'debug.log'):
    p = os.path.join(exe_dir, name)
    if os.path.exists(p):
        os.remove(p)

result.append('=== 启动 exe ===')
proc = subprocess.Popen([exe], cwd=exe_dir)
result.append('pid=%d, 等待 40 秒...' % proc.pid)

time.sleep(40)

if proc.poll() is None:
    result.append('STATUS: 运行中 (pid=%d)' % proc.pid)
else:
    result.append('STATUS: 已退出 code=%s' % proc.poll())

# 检查 9800 端口
result.append('')
result.append('=== 检查 API 端口 9800 ===')
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(3)
try:
    sock.connect(('127.0.0.1', 9800))
    result.append('端口 9800: 开放 ✅')
    sock.close()
except Exception as e:
    result.append('端口 9800: 关闭 ❌ (%s)' % e)

# 检查子进程（WebEngine 等）
result.append('')
result.append('=== 相关进程 ===')
import subprocess as sp
r = sp.run(['powershell', '-NoProfile', '-Command',
            "Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq %d -or $_.ProcessId -eq %d } | Select-Object ProcessId,Name | Format-Table -AutoSize | Out-String" % (proc.pid, proc.pid)],
           capture_output=True, text=True, timeout=30)
result.append(r.stdout)

# 检查日志文件
result.append('')
result.append('=== 日志文件 ===')
for name in ('error.log', 'app.log', 'run.log', 'debug.log'):
    p = os.path.join(exe_dir, name)
    if os.path.exists(p):
        try:
            with open(p, 'rb') as f:
                data = f.read()
            result.append('--- %s (%d bytes) ---' % (name, len(data)))
            result.append(data.decode('utf-8', errors='replace')[:2500])
        except Exception as e:
            result.append('%s read fail: %s' % (name, e))
    else:
        result.append('%s: 不存在' % name)

# 尝试访问 API
result.append('')
result.append('=== API 探测 ===')
for url in ('http://127.0.0.1:9800/api/health', 'http://127.0.0.1:9800/health', 'http://127.0.0.1:9800/api/status'):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'test'})
        resp = urllib.request.urlopen(req, timeout=5)
        result.append('%s -> %d' % (url, resp.status))
        break
    except Exception as e:
        result.append('%s -> %s' % (url, e))

# 清理
if proc.poll() is None:
    proc.terminate()
    time.sleep(3)
    if proc.poll() is None:
        proc.kill()
    result.append('')
    result.append('CLEANUP: 已终止')

open(out, 'w', encoding='utf-8').write('\n'.join(result))
print('done')
