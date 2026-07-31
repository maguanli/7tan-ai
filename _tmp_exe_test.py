# -*- coding: utf-8 -*-
"""启动 7tan-editor.exe 测试，检查是否报"找不到指定的模块"或崩溃"""
import subprocess, time, os, sys

exe = r'D:\7tan\7tanAI\dist\7tan-editor\7tan-editor.exe'
out = r'D:\7tan\7tanAI\_tmp_exe_test.txt'

result = []
result.append('EXE: %s' % exe)
result.append('SIZE: %d bytes' % os.path.getsize(exe))
result.append('')

# 清空错误日志（exe 会写 error.log）
err_log = r'D:\7tan\7tanAI\dist\7tan-editor\error.log'
if os.path.exists(err_log):
    os.remove(err_log)

# 启动 exe
try:
    proc = subprocess.Popen([exe], cwd=os.path.dirname(exe),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result.append('LAUNCHED pid=%d' % proc.pid)
except Exception as e:
    result.append('LAUNCH FAILED: %s' % e)
    open(out, 'w', encoding='utf-8').write('\n'.join(result))
    print('launch failed')
    sys.exit(1)

# 等待 20 秒观察
time.sleep(20)

# 检查进程是否存活
if proc.poll() is None:
    result.append('STATUS: RUNNING after 20s (pid=%d)' % proc.pid)
else:
    result.append('STATUS: EXITED code=%s' % proc.poll())

# 读 stderr
try:
    stderr_data = proc.stderr.read().decode('utf-8', errors='replace')[:3000]
    if stderr_data:
        result.append('')
        result.append('--- STDERR ---')
        result.append(stderr_data)
except Exception:
    pass

# 检查 error.log
if os.path.exists(err_log):
    try:
        with open(err_log, 'rb') as f:
            data = f.read()
        text = data.decode('utf-8', errors='replace')
        result.append('')
        result.append('--- error.log (%d bytes) ---' % len(data))
        result.append(text[:3000])
    except Exception as e:
        result.append('error.log read fail: %s' % e)
else:
    result.append('')
    result.append('error.log: NOT FOUND')

# 检查其他日志
for name in ('app.log', 'debug.log', 'run.log'):
    p = os.path.join(os.path.dirname(exe), name)
    if os.path.exists(p):
        try:
            with open(p, 'rb') as f:
                d = f.read()
            result.append('--- %s (%d bytes) ---' % (name, len(d)))
            result.append(d.decode('utf-8', errors='replace')[:2000])
        except Exception:
            pass

# 清理进程
if proc.poll() is None:
    proc.terminate()
    time.sleep(2)
    if proc.poll() is None:
        proc.kill()
    result.append('')
    result.append('CLEANUP: process terminated')

open(out, 'w', encoding='utf-8').write('\n'.join(result))
print('test done')
