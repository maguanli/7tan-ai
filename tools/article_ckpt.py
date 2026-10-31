#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""文章定稿快照 —— 让长任务不必每轮重读全文

问题：
    同一篇文章改五六轮，每轮都从零把五千字重读一遍。
    一是费 token，二是容易记错——改过的地方下一轮又写回去。
    （实际踩过：第三轮把"六个喂"改对了，第五轮差点又写成"四个喂"。）

做法：
    把"已经定稿的部分"落成 _checkpoint.json：段落指纹 + 结构 + 硬事实 + 改动备注。
    save 一次，之后每轮只 show 摘要，check 看这轮改了哪些段。

用法：
    python tools/article_ckpt.py save  <文章目录> --note "本轮改了什么"
    python tools/article_ckpt.py show  <文章目录>
    python tools/article_ckpt.py check <文章目录>
    python tools/article_ckpt.py sync  <文章目录>        # 查 md 与公众号版 html 是否同步
    python tools/article_ckpt.py facts <文章目录>        # 只列含数字的段落

退出码：
    check  : 0 = 正文未变；1 = 有变更
    sync   : 0 = 已同步；1 = html 缺段落
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CKPT = '_checkpoint.json'

MD_CANDIDATES = ['gzh_source.md', 'article.md', '文章正文.md', '正文.md']
TXT_CANDIDATES = ['文章正文.txt', 'gzh_source.txt']
HTML_CANDIDATES = ['公众号版.html', '排版.html']


# ---------------------------------------------------------------- 工具

def sha1(s: str) -> str:
    return hashlib.sha1(s.encode('utf-8')).hexdigest()


def cn_len(s: str) -> int:
    return len(re.findall(r'[\u4e00-\u9fff]', s))


def clean_md(s: str) -> str:
    """去掉 markdown 行内标记，只留读者看到的字。"""
    s = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', s)      # 图片
    s = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', s)  # 链接
    s = re.sub(r'^\s{0,3}#{1,6}\s*', '', s)         # 标题井号
    s = re.sub(r'^\s*>\s?', '', s)                  # 引用
    s = s.replace('**', '').replace('==', '').replace('@@', '').replace('!!', '')
    s = re.sub(r'^\s*[-*+]\s+', '', s)              # 列表符
    s = re.sub(r'^\s*\|.*\|\s*$', lambda m: m.group(0).replace('|', ' '), s)
    return re.sub(r'[ \t]+', ' ', s).strip()


def find_source(d: Path) -> Path:
    for n in MD_CANDIDATES + TXT_CANDIDATES:
        if (d / n).is_file():
            return d / n
    mds = [p for p in sorted(d.glob('*.md'))
           if not re.search(r'(说明|README|出处|清单)', p.name, re.I)]
    if mds:
        return mds[0]
    txs = sorted(d.glob('*.txt'))
    if txs:
        return txs[0]
    raise SystemExit('目录里找不到正文源文件：%s' % d)


def parse(src: Path) -> dict:
    """解析正文源，产出结构化的定稿要素。"""
    raw = src.read_text(encoding='utf-8', errors='ignore')
    lines = raw.splitlines()
    is_md = src.suffix.lower() in ('.md', '.markdown')

    title = None
    sections: list[str] = []
    paragraphs: list[str] = []
    images: list[str] = []
    captions: list[str] = []

    for ln in lines:
        s = ln.rstrip()
        if not s.strip():
            continue
        if is_md and re.match(r'^\s*#\s+\S', s) and title is None:
            title = clean_md(s)
            continue
        if is_md and re.match(r'^\s*##\s+\S', s):
            sections.append(clean_md(s))
            continue
        if re.match(r'^\s*!\[', s):
            m = re.match(r'^\s*!\[([^\]]*)\]\(([^)]*)\)', s)
            if m:
                captions.append(m.group(1).strip())
                images.append(m.group(2).strip())
            continue
        if re.match(r'^\s*(-{3,}|={3,})\s*$', s):      # 分割线
            continue
        if s.strip() in ('@@', '!!'):                  # 互动框/CTA 标记
            continue
        body = clean_md(s) if is_md else s.strip()
        if body:
            paragraphs.append(body)

    if title is None:
        title = paragraphs[0][:80] if paragraphs else src.stem

    fps = [sha1(p)[:10] for p in paragraphs]
    return {
        'title': title,
        'sections': sections,
        'paragraphs': paragraphs,
        'fingerprints': fps,
        'images': images,
        'captions': captions,
        'chars': len(raw),
        'cn_chars': cn_len(raw),
        'para_count': len(paragraphs),
        'sha256': sha1(raw),
    }


def numeric_facts(paragraphs: list[str], min_digits: int = 2, limit: int = 80) -> list[str]:
    """挑出含数字的段落——这些是文章里的硬事实，下一轮必须原样保留。"""
    out = []
    for p in paragraphs:
        n = len(re.findall(r'\d', p))
        if n >= min_digits and 8 <= len(p) <= 160:
            out.append(p)
        if len(out) >= limit:
            break
    return out


def load_ckpt(d: Path) -> dict | None:
    f = d / CKPT
    if not f.is_file():
        return None
    try:
        return json.loads(f.read_text(encoding='utf-8'))
    except Exception as e:
        print('快照文件损坏：%r' % e, file=sys.stderr)
        return None


def brief(s: str, n: int = 46) -> str:
    s = s.replace('\n', ' ')
    return s if len(s) <= n else s[:n] + '…'


# ---------------------------------------------------------------- 命令

def cmd_save(d: Path, note: str | None, facts: list[str]):
    src = find_source(d)
    a = parse(src)
    old = load_ckpt(d) or {}
    notes = list(old.get('notes') or [])
    if note:
        notes.append('%s  %s' % (time.strftime('%m-%d %H:%M'), note))
    notes = notes[-20:]

    ck = {
        'version': 1,
        'saved_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'source': src.name,
        'sha256': a['sha256'],
        'chars': a['chars'],
        'cn_chars': a['cn_chars'],
        'paragraphs': a['para_count'],
        'images': len(a['images']),
        'captions': len(a['captions']),
        'sections': a['sections'],
        'fingerprints': a['fingerprints'],
        'previews': [x[:60] for x in a['paragraphs']],
        'facts': numeric_facts(a['paragraphs']),
        'extra_facts': (old.get('extra_facts') or []) + list(facts or []),
        'notes': notes,
        'title': a['title'],
    }
    (d / CKPT).write_text(json.dumps(ck, ensure_ascii=False, indent=1), encoding='utf-8')

    prev = old.get('paragraphs')
    delta = '' if prev is None else '（上版 %d 段，%+d）' % (prev, a['para_count'] - prev)
    print('已保存快照  %s' % (d / CKPT))
    print('  源文件  %s' % src.name)
    print('  正文    %d 字符 / %d 汉字 / %d 段%s' % (a['chars'], a['cn_chars'],
                                                a['para_count'], delta))
    print('  结构    %d 小节   图片 %d 张   图注 %d 条'
          % (len(a['sections']), len(a['images']), len(a['captions'])))
    print('  硬事实  %d 条（含数字段落）' % len(ck['facts']))
    if note:
        print('  备注    %s' % note)
    return 0


def cmd_show(d: Path, max_facts: int = 15):
    ck = load_ckpt(d)
    if not ck:
        print('还没有快照，先跑：python tools/article_ckpt.py save %s' % d)
        return 1
    src = d / ck['source']
    stale = ''
    if src.is_file():
        cur = sha1(src.read_text(encoding='utf-8', errors='ignore'))
        if cur != ck['sha256']:
            stale = '  ⚠️ 源文件已改动，快照过期（跑 check 看差异）'

    line = '═' * 66
    print(line)
    print(' 定稿摘要  %s' % d.name)
    print(line)
    print(' 标题      %s' % ck.get('title', ''))
    print(' 源文件    %s' % ck['source'])
    print(' 保存于    %s%s' % (ck['saved_at'], stale))
    print(' 正文      %d 字符 / %d 汉字 / %d 段'
          % (ck['chars'], ck['cn_chars'], ck['paragraphs']))
    print(' 图片      %d 张（图注 %d 条）' % (ck['images'], ck['captions']))
    print(' 结构      %d 小节' % len(ck['sections']))
    for s in ck['sections']:
        print('   · %s' % brief(s, 54))

    facts = ck.get('facts') or []
    if facts:
        print('\n 硬事实（含数字的段落，共 %d 条，列前 %d）' % (len(facts), min(max_facts, len(facts))))
        for f in facts[:max_facts]:
            print('   - %s' % brief(f, 66))
        if len(facts) > max_facts:
            print('   … 还有 %d 条，用 facts 子命令看全量' % (len(facts) - max_facts))

    extra = ck.get('extra_facts') or []
    if extra:
        print('\n 人工补充事实')
        for f in extra:
            print('   - %s' % f)

    notes = ck.get('notes') or []
    if notes:
        print('\n 改动记录（最近 %d 条）' % len(notes))
        for n in notes[-8:]:
            print('   · %s' % n)

    print('\n 提示：下一轮只需本摘要 + 本轮新增要求，无需重读全文。')
    print(line)
    return 0


def cmd_check(d: Path, show_n: int = 20):
    ck = load_ckpt(d)
    if not ck:
        print('还没有快照，先跑 save')
        return 1
    src = find_source(d)
    a = parse(src)
    if a['sha256'] == ck['sha256']:
        print('✅ 正文与快照一致（%d 段 / %d 汉字），本轮无改动。'
              % (a['para_count'], a['cn_chars']))
        return 0

    print('⚠️  正文已改动  %s' % src.name)
    print('   字符 %d → %d (%+d)    汉字 %d → %d (%+d)'
          % (ck['chars'], a['chars'], a['chars'] - ck['chars'],
             ck['cn_chars'], a['cn_chars'], a['cn_chars'] - ck['cn_chars']))
    print('   段落 %d → %d (%+d)     小节 %d → %d (%+d)'
          % (ck['paragraphs'], a['para_count'], a['para_count'] - ck['paragraphs'],
             len(ck['sections']), len(a['sections']),
             len(a['sections']) - len(ck['sections'])))
    print('   图片 %d → %d (%+d)'
          % (ck['images'], len(a['images']), len(a['images']) - ck['images']))

    old_p = ck.get('fingerprints') or []
    new_p = a['fingerprints']
    sm = difflib.SequenceMatcher(a=old_p, b=new_p, autojunk=False)
    changes = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        changes.append((tag, i1, i2, j1, j2))

    if not changes:
        print('\n   指纹全等，只是行尾或格式变化。')
        return 1

    prev = ck.get('previews') or []
    if not prev:
        print('\n   （快照是旧版本，没存段落预览，重新 save 一次可看新旧对照）')

    print('\n   段落级变更 %d 处：' % len(changes))
    shown = 0
    for tag, i1, i2, j1, j2 in changes:
        if shown >= show_n:
            print('   … 还有 %d 处未显示' % (len(changes) - shown))
            break
        shown += 1
        if tag == 'replace':
            for k in range(max(i2 - i1, j2 - j1)):
                oi, nj = i1 + k, j1 + k
                print('\n   ~ 旧%d → 新%d  改写' % (oi + 1, nj + 1))
                if oi < len(prev):
                    print('      旧: %s' % brief(prev[oi], 62))
                if nj < len(a['paragraphs']):
                    print('      新: %s' % brief(a['paragraphs'][nj], 62))
        elif tag == 'delete':
            print('\n   - 旧%d-%d  删除 %d 段' % (i1 + 1, i2, i2 - i1))
            for oi in range(i1, min(i2, i1 + 3)):
                if oi < len(prev):
                    print('      删: %s' % brief(prev[oi], 62))
        elif tag == 'insert':
            print('\n   + 新%d-%d  新增 %d 段' % (j1 + 1, j2, j2 - j1))
            for nj in range(j1, min(j2, j1 + 3)):
                if nj < len(a['paragraphs']):
                    print('      加: %s' % brief(a['paragraphs'][nj], 62))

    print('\n   确认无误后跑：python tools/article_ckpt.py save %s --note "..."' % d)
    return 1


def cmd_facts(d: Path):
    src = find_source(d)
    a = parse(src)
    facts = numeric_facts(a['paragraphs'], limit=500)
    print('含数字的段落共 %d 条：\n' % len(facts))
    for i, f in enumerate(facts, 1):
        print('%3d. %s' % (i, f))
    return 0


def cmd_sync(d: Path):
    """检查 markdown 正文是否都进了公众号 html —— 防"改了源文件忘了重出 html"。"""
    src = find_source(d)
    a = parse(src)
    html = None
    for n in HTML_CANDIDATES:
        if (d / n).is_file():
            html = d / n
            break
    if html is None:
        cands = sorted(d.glob('*公众号*.html')) + sorted(d.glob('*可直接粘贴*.html'))
        if not cands:
            print('目录里没有公众号 html')
            return 1
        html = cands[0]

    raw = html.read_text(encoding='utf-8', errors='ignore')
    body = re.sub(r'<script\b.*?</script>', '', raw, flags=re.S | re.I)
    text = re.sub(r'<[^>]+>', '', body)
    text_sq = re.sub(r'\s+', '', text)
    text_sq = (text_sq.replace('&#91;', '[').replace('&#93;', ']')
                      .replace('&amp;', '&').replace('&quot;', '"'))

    miss = []
    for i, p in enumerate(a['paragraphs'], 1):
        key = re.sub(r'\s+', '', p)
        if len(key) < 8:
            continue
        if key not in text_sq:
            miss.append((i, p))

    print('源文件 %s → %s' % (src.name, html.name))
    print('正文档次 %d 段，缺失 %d 段' % (a['para_count'], len(miss)))
    if not miss:
        print('✅ 已同步')
        return 0
    print('❌ 以下段落只在 md 里，html 中找不到：')
    for i, p in miss[:30]:
        print('   第%d段  %s' % (i, brief(p, 64)))
    if len(miss) > 30:
        print('   … 还有 %d 段' % (len(miss) - 30))
    print('\n需要重出 html。')
    return 1


# ---------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description='文章定稿快照：save / show / check / sync / facts')
    ap.add_argument('cmd', choices=['save', 'show', 'check', 'sync', 'facts'])
    ap.add_argument('dir', help='文章目录')
    ap.add_argument('--note', default=None, help='save 时记录本轮改了什么')
    ap.add_argument('--fact', action='append', default=[], help='save 时追加一条人工事实')
    ap.add_argument('--max-facts', type=int, default=15, help='show 时最多列几条硬事实')
    args = ap.parse_args(argv)

    d = Path(args.dir)
    if not d.is_dir():
        print('不是目录：%s' % d, file=sys.stderr)
        return 2

    if args.cmd == 'save':
        return cmd_save(d, args.note, args.fact)
    if args.cmd == 'show':
        return cmd_show(d, args.max_facts)
    if args.cmd == 'check':
        return cmd_check(d)
    if args.cmd == 'sync':
        return cmd_sync(d)
    return cmd_facts(d)


if __name__ == '__main__':
    sys.exit(main())
