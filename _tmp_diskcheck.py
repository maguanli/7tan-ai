import shutil
for drive in ('D:/', 'C:/'):
    try:
        u = shutil.disk_usage(drive)
        print(f"{drive} free={u.free/1024**3:.1f}GB total={u.total/1024**3:.1f}GB")
    except Exception as e:
        print(f"{drive} error: {e}")
