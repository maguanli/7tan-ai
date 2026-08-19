import subprocess, sys, os

print("=== python version:", sys.version.split()[0])
# 尝试 psutil
try:
    import psutil
    has_psutil = True
except Exception:
    has_psutil = False
print("psutil available:", has_psutil)

if has_psutil:
    print("\n=== all python.exe processes ===")
    for p in psutil.process_iter(['pid', 'ppid', 'name', 'cmdline', 'create_time']):
        try:
            if 'python' in (p.info['name'] or '').lower():
                cmd = ' '.join(p.info['cmdline'] or [])[:200]
                print(f"PID={p.info['pid']} PPID={p.info['ppid']} name={p.info['name']} create={p.info['create_time']}")
                print(f"    cmd: {cmd}")
        except Exception as e:
            print("err", e)
    print("\n=== port 9800 ===")
    for c in psutil.net_connections(kind='tcp'):
        if c.laddr.port == 9800:
            try:
                proc = psutil.Process(c.pid)
                print(f"  laddr={c.laddr} state={c.status} pid={c.pid} name={proc.name()} cmd={(' '.join(proc.cmdline()) if proc.cmdline() else '')[:150]}")
            except Exception as e:
                print(f"  laddr={c.laddr} state={c.status} pid={c.pid} (proc err)")
else:
    print("no psutil, fallback to tasklist")
    out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'], capture_output=True, text=True).stdout
    print(out)
