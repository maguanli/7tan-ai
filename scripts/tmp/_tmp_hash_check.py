import hashlib, pathlib, os
print("CWD:", os.getcwd())
for p in ['data/plugins/desktop_bot/tools.py', 'data/plugins/camera_vision/tools.py']:
    try:
        data = pathlib.Path(p).read_bytes()
        print(p, len(data), hashlib.sha256(data).hexdigest())
    except Exception as e:
        print(p, 'ERROR', e)
