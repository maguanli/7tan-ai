# -*- coding: utf-8 -*-
"""下载远端 profile.php，核对行尾/字节数，与本地 _srv 副本比对"""
import io, json, sys, hashlib
from pathlib import Path
import paramiko

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = Path(r'D:\7tan\7tanAI')
cfg = json.loads((ROOT / 'config' / 'deploy.json').read_text(encoding='utf-8'))
srv = cfg['server']

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(srv['host'], srv['port'], srv['user'], srv['password'],
            timeout=25, look_for_keys=False, allow_agent=False)
sftp = ssh.open_sftp()

remote = '/D:/workspace/7tan/bbs/profile.php'
raw = sftp.open(remote).read()
out = ROOT / '_srv' / 'profile.remote.php'
out.write_bytes(raw)

print('远端 profile.php  %d 字节  md5=%s' % (len(raw), hashlib.md5(raw).hexdigest()))
print('  CR 数 =', raw.count(b'\r'), '  LF 数 =', raw.count(b'\n'),
      '  CRLF 对 =', raw.count(b'\r\n'))
txt = raw.decode('utf-8')
print('  utf-8 解码 OK, 字符数 =', len(txt))

loc = ROOT / '_srv' / 'profile.php'
lb = loc.read_bytes()
print('本地副本  %d 字节  md5=%s' % (len(lb), hashlib.md5(lb).hexdigest()))
print('  与远端一致 =', lb == raw)

print('\n关键锚点:')
for k in ('LIMIT 5', 'recentTopics', '$canonicalPath', '最新帖子', '注册信息'):
    print('  %-16s 出现 %d 次' % (k, txt.count(k)))

# 目录里现有备份
baks = sorted(a.filename for a in sftp.listdir_attr('/D:/workspace/7tan/bbs')
              if a.filename.startswith('profile.php'))
print('\nbbs 目录里 profile.php* :', baks)

sftp.close()
ssh.close()
