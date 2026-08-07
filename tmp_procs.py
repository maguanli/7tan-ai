import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
try:
    import psutil
    for p in psutil.process_iter(['pid','name','cmdline']):
        try:
            cl = ' '.join(p.info['cmdline'] or [])
            if any(k in cl.lower() for k in ['package_release','build','zip','pyinstaller','7tan']):
                if 'tmp_' not in cl:
                    print('PID', p.info['pid'], '|', p.info['name'], '|', cl[:250])
        except Exception:
            pass
except ImportError:
    print('NO_PSUTIL')
