# -*- coding: utf-8 -*-
"""7723大事记.html -> 7坛 UBB（每条里程碑底部自动附「原帖链接」）
主站论坛(/bbs/)正文是 UBB，不是 HTML。本站支持的"精美组件"标签：
  [title] [subtitle] [caption] [divider] [quote] [note] [tip] [hl] [b] [btn=url] [img]
（依据站内 ubb_plus.css 与老马账号历史发帖实测）
"""
import re, html, sys, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SRC = Path(r'D:\7tan\7tanAI\7723\7723大事记.html')
OUT = Path(r'D:\7tan\7tanAI\7723\7723大事记_UBB.txt')
BASE = 'https://www.7tan.com/bbs/%s/'

raw = SRC.read_text(encoding='utf-8')


def clean(s):
    s = re.sub(r'<br\s*/?>', ' ', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s)
    s = re.sub(r'[ \t\u3000]+', ' ', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()


def extract_divs(s, cls):
    """按 class 提取成对的 <div class="cls">...</div>（含嵌套），返回 [(pos, html), ...]"""
    results = []
    i = 0
    open_tag = '<div class="%s">' % cls
    while True:
        j = s.find(open_tag, i)
        if j < 0:
            break
        k = j + len(open_tag)
        depth = 1
        while depth > 0:
            nxt_open = s.find('<div', k)
            nxt_close = s.find('</div>', k)
            if nxt_close < 0:
                break
            if 0 <= nxt_open < nxt_close:
                depth += 1
                k = nxt_open + 4
            else:
                depth -= 1
                k = nxt_close + 6
        results.append((j, s[j:k]))
        i = k
    return results


h1 = clean(re.search(r'<h1>(.*?)</h1>', raw, re.S).group(1))
sub = clean(re.search(r'<div class="sub">(.*?)</div>', raw, re.S).group(1))
src = clean(re.search(r'<div class="src">(.*?)</div>', raw, re.S).group(1))
stats = re.findall(r'<div class="stat"><b>(.*?)</b><span>(.*?)</span></div>', raw, re.S)

tl = raw.split('<div class="timeline">', 1)[1].split('<footer', 1)[0]

events = []
for pos, _ in extract_divs(tl, 'yr'):
    m = re.compile(r'<div class="yr"><span>(.*?)</span></div>', re.S).match(tl[pos:])
    if m:
        events.append((pos, 'year', clean(m.group(1))))
for pos, blk in extract_divs(tl, 'item'):
    events.append((pos, 'item', blk))
events.sort(key=lambda x: x[0])

out = ['[title]%s[/title]' % h1,
       '[subtitle]%s[/subtitle]' % sub,
       '[caption]%s[/caption]' % src,
       '[note]%s[/note]' % ' ｜ '.join('%s %s' % (clean(b), clean(s)) for b, s in stats),
       '']

n_items = n_reps = n_link = 0
for _, kind, val in events:
    if kind == 'year':
        out += ['[divider]', '[title]%s[/title]' % val, '']
        continue
    n_items += 1
    date = re.search(r'<span class="date">(.*?)</span>', val, re.S)
    board = re.search(r'<span class="board">(.*?)</span>', val, re.S)
    h3 = re.search(r'<h3>(.*?)</h3>', val, re.S)
    meta = re.search(r'<div class="meta">(.*?)</div>', val, re.S)
    content = extract_divs(val, 'content')
    date = clean(date.group(1)) if date else ''
    board = clean(board.group(1)) if board else ''
    h3 = clean(h3.group(1)) if h3 else ''
    meta = clean(meta.group(1)) if meta else ''
    ctext = clean(content[0][1]) if content else ''

    # 从 meta 里取原始帖号 -> 生成主站帖子链接
    pid = ''
    mp = re.search(r'帖号\s*(\d+)', meta)
    if mp:
        pid = mp.group(1)

    head = ' · '.join(x for x in [date, h3] if x)
    out.append('[b]%s[/b]' % head)
    cap = ' ｜ '.join(x for x in [board, meta] if x)
    if cap:
        out.append('[caption]%s[/caption]' % cap)
    if ctext:
        out.append(ctext)

    reps = []
    for _, rb in extract_divs(val, 'rep'):
        nm = re.search(r'<b>(.*?)</b>', rb, re.S)
        rt = re.search(r'<span class="rt">(.*?)</span>', rb, re.S)
        rx = re.search(r'<span class="rx">(.*?)</span>', rb, re.S)
        nm = clean(nm.group(1)) if nm else ''
        rt = clean(rt.group(1)) if rt else ''
        rx = clean(rx.group(1)) if rx else ''
        reps.append('%s（%s）：%s' % (nm, rt, rx))
        n_reps += 1
    if reps:
        out.append('[quote]%s[/quote]' % '\n'.join(reps))

    # ★ 每条底部附原帖链接
    if pid:
        out.append('[btn=%s]▶ 点击查看原帖[/btn]' % (BASE % pid))
        n_link += 1
    out.append('')

ubb = '\n'.join(out).strip() + '\n'
OUT.write_text(ubb, encoding='utf-8')

print('输出:', OUT)
print('字符数:', len(ubb), '| 里程碑:', n_items, '| 回复:', n_reps, '| 原帖链接:', n_link)
print('---- 前 30 行预览 ----')
print('\n'.join(ubb.splitlines()[:30]))
