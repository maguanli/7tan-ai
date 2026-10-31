# -*- coding: utf-8 -*-
import io, sys, hashlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import paramiko

HOST, PORT, USER, PASS = '47.86.169.72', 22, 'administrator', 'hm189ikEYclIEg#@ky'
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, PORT, USER, PASS, timeout=20)
s = c.open_sftp()
L = r'D:\7tan\7tanAI\_srv' + '\\'

for remote, local in [('D:/workspace/7tan/router.php', L + 'router.final.php'),
                      ('D:/workspace/7tan/bbs/profile.php', L + 'profile.final.php')]:
    with s.open(remote, 'rb') as f:
        blob = f.read()
    open(local, 'wb').write(blob)
    print('%-28s %6d B  md5 %s  CRLF=%d' % (local.split('\\')[-1], len(blob),
          hashlib.md5(blob).hexdigest()[:12], blob.count(b'\r\n')))
s.close()
c.close()
