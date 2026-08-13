import sys, subprocess
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

out = subprocess.run(['wmic', 'process', 'where', "name like '%QQ%' or name like '%qq%'", 'get', 'ProcessId,Name,ExecutablePath', '/format:list'],
                     capture_output=True, text=True, timeout=30)
print('STDOUT:', out.stdout)
print('STDERR:', out.stderr[:2000])
