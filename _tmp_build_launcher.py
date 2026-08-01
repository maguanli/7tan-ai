import subprocess, sys

log_path = r'D:\7tan\7tanAI\build_log.txt'
log = open(log_path, 'wb', 0)
p = subprocess.Popen(
    ['cmd', '/c', 'build_and_sync.bat', '-v', '1.0.1', '-y'],
    cwd=r'D:\7tan\7tanAI',
    stdout=log,
    stderr=subprocess.STDOUT,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
)
print(f"BUILD_LAUNCHED PID={p.pid}")
