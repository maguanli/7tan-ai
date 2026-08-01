# -*- coding: utf-8 -*-
import paramiko, sys, os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("47.86.169.72", port=22, username="administrator", password="hm573ikEYclIEg#@km", timeout=20)
def run(cmd, t=30):
    stdin, stdout, stderr = c.exec_command(cmd, timeout=t)
    return stdout.read().decode('utf-8', 'ignore') + stderr.read().decode('utf-8', 'ignore')
print("=== down/index.php 前50行 ===")
print(run('powershell -Command "Get-Content \'D:\\workspace\\7tan\\down\\index.php\' -TotalCount 50"', 25))
print("=== 全站含 download.php / getfile 的php ===")
print(run('dir /b /s "D:\\workspace\\7tan\\*down*.php"', 20))
c.close()
