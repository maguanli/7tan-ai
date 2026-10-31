# -*- coding: utf-8 -*-
"""上线 profile.php 分页版：备份 → 覆盖 → 回读校验 → HTTP 烟测"""
import io, json, sys, time, hashlib, urllib.request, urllib.error
from pathlib import Path
import paramiko

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = Path(r'D:\7tan\7tanAI')
NEW = ROOT / '_srv' / 'profile.new.php'
cfg = json.loads((ROOT / 'config' / 'deploy.json').read_text(encoding='utf-8'))
srv = cfg['server']

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(srv['host'], srv['port'], srv['user'], srv['password'],
            timeout=25, look_for_keys=False, allow_agent=False)
sftp = ssh.open_sftp()

LIVE = '/D:/workspace/7tan/bbs/profile.php'
stamp = time.strftime('%Y%m%d_%H%M%S')
BAK = '/D:/workspace/7tan/bbs/profile.php.bak_paged_' + stamp

# 1) 备份
old = sftp.open(LIVE).read()
with sftp.open(BAK, 'wb') as f:
    f.write(old)
print('[1] 备份 %s  %d B  md5=%s' % (BAK.split('/')[-1], len(old), hashlib.md5(old).hexdigest()))

# 2) 覆盖
new_bytes = NEW.read_bytes()
with sftp.open(LIVE, 'wb') as f:
    f.write(new_bytes)
print('[2] 已写入 live  %d B' % len(new_bytes))

# 3) 回读校验
back = sftp.open(LIVE).read()
print('[3] 回读 %d B  md5=%s  一致=%s'
      % (len(back), hashlib.md5(back).hexdigest(), back == new_bytes))
assert back == new_bytes, '回读不一致'

# 4) 线上 php -l
_, out, err = ssh.exec_command('php -l D:\\workspace\\7tan\\bbs\\profile.php 2>&1', timeout=60)
print('[4] live php -l:', out.read().decode('utf-8', 'ignore').strip())

sftp.close()
ssh.close()

# 5) HTTP 烟测
BASE = 'https://www.7tan.com'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, msg, headers, fp)


opener = urllib.request.build_opener(NoRedirect)
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'


def get(path):
    req = urllib.request.Request(BASE + path, headers={'User-Agent': UA})
    try:
        with opener.open(req, timeout=30) as r:
            return r.status, r.read().decode('utf-8', 'ignore'), dict(r.headers)
    except urllib.error.HTTPError as ex:
        return ex.code, ex.read().decode('utf-8', 'ignore'), dict(ex.headers)


def stat(html):
    import re
    items = len(re.findall(r'<div class="topic-item">', html))
    badge = re.findall(r'class="count-badge">([^<]*)<', html)
    pager = 'class="pager"' in html
    onpg = re.findall(r'class="pg on">(\d+)<', html)
    warn = sum(html.count(k) for k in ('Warning:', 'Notice:', 'Fatal error', 'Deprecated:'))
    titles = re.findall(r'href="/bbs/(\d+)/">([^<]+)</a>', html)
    return items, badge, pager, onpg, warn, titles[:2]


print('\n[5] HTTP 烟测')
cases = [
    ('/bbs/user/1/', 200),
    ('/bbs/user/1/?page=2', 200),
    ('/bbs/user/1/?page=23', 200),
    ('/bbs/user/1/?page=24', 301),
    ('/bbs/user/1/?page=1', 301),
    ('/bbs/user/1/?page=0', 301),
    ('/bbs/user/1/?page=abc', 301),
    ('/bbs/user/20753/', 200),
]
for path, expect in cases:
    code, html, hdrs = get(path)
    loc = hdrs.get('Location', '')
    if code in (301, 302):
        print('  %-26s %s → %s' % (path, code, loc))
        print('        %s' % ('PASS' if code == expect else 'FAIL 期望 %s' % expect))
        continue
    items, badge, pager, onpg, warn, t2 = stat(html)
    print('  %-26s %s  条目=%-2d 徽章=%s 分页=%s 当前页=%s 告警=%d'
          % (path, code, items, badge, pager, onpg, warn))
    for pid, t in t2:
        print('        /%s/ %s' % (pid, t.strip()[:40]))
    print('        %s' % ('PASS' if code == expect and warn == 0 else 'FAIL'))
