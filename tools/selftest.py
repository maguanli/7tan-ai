#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""bbs_verify / article_ckpt 自检 —— 证明这两个工具真的会报错

为什么需要：
    一个"永远返回 PASS"的检查脚本比没有检查更糟。
    这里用故意做错的输入，验证它们确实会变红。

用法：
    python tools/selftest.py              # 全部
    python tools/selftest.py --offline    # 跳过联网项

退出码：0 全通过；1 有失败
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HERE = Path(__file__).resolve().parent
PY = sys.executable
GOOD_PID = '84149'                                  # 已发布的一篇，用作对照
GOOD_DIR = Path(r'D:\7tan\dsh-workspace\article-zcy')

results: list[tuple[bool, str, str]] = []


def run(args: list[str], timeout: int = 240):
    r = subprocess.run([PY] + args, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=timeout)
    return r.returncode, r.stdout + r.stderr


def case(ok: bool, name: str, note: str = ''):
    results.append((ok, name, note))
    print('%s  %-46s %s' % ('✅' if ok else '❌', name, note))


# ---------------------------------------------------------------- bbs_verify

def test_verify(offline: bool):
    print('\n[bbs_verify]')
    if offline:
        case(True, '联网项跳过', '--offline')
        return

    # 1. 不存在的帖子必须 FAIL
    rc, out = run([str(HERE / 'bbs_verify.py'), '99999999', '--no-lists'])
    case(rc == 1 and 'FAIL' in out, '假 pid 会判 FAIL', '退出码 %d' % rc)

    # 2. 正确帖子必须 PASS
    rc, out = run([str(HERE / 'bbs_verify.py'), GOOD_PID,
                   '--from-article', str(GOOD_DIR), '--no-lists'])
    if rc == 2 or '抓取失败' in out:
        case(False, '正常帖子判 PASS', '抓取失败，跳过')
    else:
        case(rc == 0 and 'PASS' in out, '正常帖子判 PASS',
             re.search(r'共 \d+ 项：.*', out).group(0)[:40] if re.search(r'共 \d+ 项：.*', out) else '')

    # 3. 故意写错的期望值必须 FAIL
    tmp = Path(tempfile.mkdtemp(prefix='vb_'))
    try:
        bad = tmp / 'bad.json'
        bad.write_text(json.dumps({
            'title': '这个是故意写错的标题',
            'images': 999,
            'must_contain': ['页面上绝对没有这句话'],
        }, ensure_ascii=False), encoding='utf-8')
        rc, out = run([str(HERE / 'bbs_verify.py'), GOOD_PID,
                       '--expect', str(bad), '--no-lists'])
        n_fail = len(re.findall(r'❌', out))
        case(rc == 1 and n_fail >= 3, '错误期望值会报出多处 FAIL',
             '抓到 %d 处' % n_fail)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- article_ckpt

def test_ckpt():
    print('\n[article_ckpt]')
    if not GOOD_DIR.is_dir():
        case(False, '样例文章目录存在', str(GOOD_DIR))
        return
    src_md = None
    for n in ('gzh_source.md', 'article.md'):
        if (GOOD_DIR / n).is_file():
            src_md = GOOD_DIR / n
            break
    if src_md is None:
        case(False, '样例正文源存在', str(GOOD_DIR))
        return

    tmp = Path(tempfile.mkdtemp(prefix='ck_'))
    try:
        text = src_md.read_text(encoding='utf-8')
        (tmp / 'gzh_source.md').write_text(text, encoding='utf-8')
        html = GOOD_DIR / '公众号版.html'
        if html.is_file():
            shutil.copy(html, tmp / '公众号版.html')

        # 1. save 成功
        rc, out = run([str(HERE / 'article_ckpt.py'), 'save', str(tmp),
                       '--note', 'selftest'])
        case(rc == 0 and (tmp / '_checkpoint.json').is_file(), 'save 生成快照')

        # 2. 未改动 check 返回 0
        rc, out = run([str(HERE / 'article_ckpt.py'), 'check', str(tmp)])
        case(rc == 0 and '一致' in out, '未改动时 check 返回 0')

        # 3. 改动一处 → check 返回 1，且能指出段号与原句
        paras = [p for p in text.split('\n\n')
                 if len(p.strip()) > 30
                 and not p.strip().startswith('![')
                 and not p.strip().startswith('#')]
        target = paras[len(paras) // 2].strip()[:30] if paras else None
        if target:
            mutated = text.replace(target, '这是一句自检用的替换文本', 1)
            (tmp / 'gzh_source.md').write_text(mutated, encoding='utf-8')
            rc, out = run([str(HERE / 'article_ckpt.py'), 'check', str(tmp)])
            located = ('旧' in out and '新' in out and '旧:' in out)
            case(rc == 1 and located, '改动后 check 返回 1 并定位段落',
                 '退出码 %d' % rc)

            # 4. html 还是旧的 → sync 应报缺段
            if (tmp / '公众号版.html').is_file():
                rc, out = run([str(HERE / 'article_ckpt.py'), 'sync', str(tmp)])
                case(rc == 1 and '缺失' in out, 'sync 能发现 html 未同步',
                     '退出码 %d' % rc)
            else:
                case(True, 'sync 检查', '样例无 html，跳过')
        else:
            case(False, '改动后 check 返回 1', '正文里找不到可替换的长段')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--offline', action='store_true', help='跳过联网测试')
    args = ap.parse_args()

    print('=' * 66)
    print(' 工具自检')
    print('=' * 66)
    test_verify(args.offline)
    test_ckpt()

    bad = [r for r in results if not r[0]]
    print('\n' + '=' * 66)
    print(' %d 项：%d 通过 / %d 失败  =>  %s'
          % (len(results), len(results) - len(bad), len(bad),
             'PASS' if not bad else 'FAIL'))
    print('=' * 66)
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
