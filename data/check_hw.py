import os, platform, json
info = {}
try:
    import psutil
    vm = psutil.virtual_memory()
    info['ram_gb'] = round(vm.total / (1024**3), 1)
    info['ram_available_gb'] = round(vm.available / (1024**3), 1)
    info['cpu_cores'] = psutil.cpu_count(logical=False)
    info['cpu_threads'] = psutil.cpu_count(logical=True)
except Exception as e:
    info['psutil_err'] = str(e)
info['platform'] = platform.platform()
info['python'] = platform.python_version()
print(json.dumps(info, ensure_ascii=False, indent=2))
