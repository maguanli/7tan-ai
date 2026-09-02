import platform, os
print('CPU:', platform.processor())
print('CORES:', os.cpu_count())
try:
    import psutil
    vm = psutil.virtual_memory()
    print('RAM_GB:', round(vm.total / 1073741824, 1))
except Exception as e:
    print('psutil unavailable:', e)
try:
    import GPUtil
    gpus = GPUtil.getGPUs()
    for g in gpus:
        print('GPU:', g.name, 'VRAM_GB:', g.memoryTotal)
except Exception:
    try:
        import subprocess
        out = subprocess.run(['wmic', 'path', 'win32_videocontroller', 'get', 'name'], capture_output=True, text=True, timeout=20)
        print('GPU(wmic):', out.stdout)
    except Exception as e2:
        print('GPU check failed:', e2)
