# -*- coding: utf-8 -*-
"""统一为 CRLF（与原文件一致）+ 线上核验「作者的其他文章」模块"""
import io, json, re, sys, time
import urllib.request
from pathlib import Path
import paramiko

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = Path(r'D:\7tan\7tanAI')
cfg = json.loads((ROOT / 'config' / 'deploy.json').read_text(encoding='utf-8'))
srv = cfg['server']
PHP = r'D:\php\php-8.2.35\php.exe'

text = (ROOT / '_srv' / 'view.php.new').read_text(encoding='utf-8')
lf = text.replace('\r\n', '\n')
crlf_bytes = lf.replace('\n', '\r\n').encode('utf-8')
print('[0] CRLF 版本 %d bytes，LF 数 %d' % (len(crlf_bytes), lf.count('\n')))

out = ROOT / '_srv' / 'view.php.crlf'
out.write_bytes(crlf_bytes)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(srv['host'], srv['port'], srv['user'], srv['password'],
            timeout=25, look_for_keys=False, allow_agent=False)
sftp = ssh.open_sftp()


def run(cmd, t=180):
    _, o, e = ssh.exec_command(cmd, timeout=t)
    return o.read().decode('utf-8', 'ignore'), e.read().decode('utf-8', 'ignore')


sftp.put(str(out), '/D:/workspace/ai_poster/view_crlf_check.php')
o, e = run('"%s" -l "D:\\workspace\\ai_poster\\view_crlf_check.php"' % PHP)
print('[1] php -l:', (o.strip() or e.strip())[:200])
assert 'No syntax errors' in o

sftp.put(str(out), '/D:/workspace/7tan/bbs/view.php')
st = sftp.stat('/D:/workspace/7tan/bbs/view.php')
back = sftp.open('/D:/workspace/7tan/bbs/view.php').read()
print('[2] 上传 %d / 回读 %d / 一致=%s / CR=%d' %
      (st.st_size, len(back), back == crlf_bytes, back.count(b'\r')))
assert back == crlf_bytes
ssh.exec_command(r'del /q "D:\workspace\ai_poster\view_crlf_check.php"')

# 清缓存
files = sftp.listdir('/D:/workspace/7tan/cache/topic')
for pid in [84008, 84023, 83954]:
    hit = [f for f in files if f.startswith(str(pid) + '_')]
    for f in hit:
        sftp.remove('/D:/workspace/7tan/cache/topic/' + f)
    print('[3] 清缓存 %d -> %s' % (pid, hit))

sftp.close()
ssh.close()

# ---------- 线上核验 ----------
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'}


def get(url):
    t0 = time.time()
    req = urllib.request.Request(url, headers=UA)
    html = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'ignore')
    return html, (time.time() - t0) * 1000


BAD = ['Warning:', 'Notice:', 'Fatal error', 'Deprecated:', 'Undefined ']

for pid in [84008, 84023]:
    url = 'https://www.7tan.com/bbs/%d/' % pid
    html, ms = get(url)
    print('\n===== %s  (%.0f ms, %d 字节) =====' % (url, ms, len(html.encode('utf-8'))))
    bad = [b for b in BAD if b in html]
    print('  PHP 报错串:', bad or '无')
    assert not bad, '页面出现 PHP 错误'
    has = 'class="author-more"' in html
    print('  模块存在:', has)
    assert has, '模块未出现'
    # 抽出模块块
    m = re.search(r'<section class="author-more".*?</section>', html, re.S)
    block = m.group(0) if m else ''
    titles = re.findall(r'<a class="am-link" href="([^"]+)">([^<]+)</a>', block)
    boards = re.findall(r'<span class="am-board">([^<]+)</span>', block)
    views = re.findall(r'<span class="am-views">(\d+) 次浏览</span>', block)
    dates = re.findall(r'<span class="am-date">([^<]+)</span>', block)
    head = re.search(r'<h3 class="am-title">(.*?)</h3>', block, re.S)
    print('  标题:', re.sub(r'<[^>]+>', '', head.group(1)) if head else '(无)')
    print('  条数: %d' % len(titles))
    for i, (u, t) in enumerate(titles, 1):
        print('   %d. %-34s %s  %s  %s 次' % (i, t, boards[i - 1] if i - 1 < len(boards) else '-',
                                              dates[i - 1] if i - 1 < len(dates) else '-',
                                              views[i - 1] if i - 1 < len(views) else '-'))
    assert len(titles) == 6, '条数不是 6'
    assert pid not in [int(x) for x in re.findall(r'href="/bbs/(\d+)/"', block)], '推荐里含当前帖'
    # 位置校验：必须在回复区之后、回复框之前
    i_am = html.find('class="author-more"')
    i_box = html.find('<!-- 回复框 -->')
    i_load = html.find('id="loadMoreStatus"')
    print('  位置: loadMoreStatus@%d < author-more@%d < 回复框@%d -> %s' %
          (i_load, i_am, i_box, i_load < i_am < i_box))
    assert i_load < i_am < i_box, '插入位置不对'

print('\n[OK] 线上核验通过')
