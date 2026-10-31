# -*- coding: utf-8 -*-
"""发布后独立断言闸门（Router 层之外的第一道 Watchdog）

用法（在 publish_*.py 末尾）：

    from publish_guard import guard
    guard(pid, WS, board_name='游戏交流', expect_images=26)

行为：
  - 以子进程调用 tools/bbs_verify.py，纯 HTTP 断言，不读数据库、不碰密码
  - 返回码 0 = 全部 PASS/SKIP；非 0 = 有 FAIL，抛 SystemExit 让发布脚本停住
  - 一旦日志里出现 FAIL，说明「我口头说发好了」这条路被切断

设计原则：
  1. 不信任调用方给的期望值，图数优先从文章目录推导
  2. 默认查 board 列表 / 首页 / 作者主页三处收录（首页缓存漏清是历史真事故）
  3. 只在 rc!=0 时抛异常，不删除已发布的帖子
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

VERIFY = Path(__file__).resolve().parent / 'bbs_verify.py'


def guard(pid, article_dir=None, board_name=None, expect_images=None,
          uid=1, author='老马', check_lists=True, timeout=240, quiet=False):
    """发布后跑 bbs_verify，失败抛 SystemExit。

    Args:
        pid: 帖子 id
        article_dir: 文章目录（用于推导标题/图数/小节数），可为空
        board_name: 期望板块名，如 '游戏交流'
        expect_images: 期望图片数；为空则从 article_dir 推导
        uid: 作者 uid，默认 1（老马）
        author: 作者昵称
        check_lists: 是否检查 board 列表 / 首页 / 作者主页收录
        timeout: 子进程超时秒
        quiet: True 则只打印结论

    Returns:
        True（失败会抛异常，不会走到返回）
    """
    cmd = [sys.executable, str(VERIFY), str(pid),
           '--uid', str(uid), '--author', author]

    if article_dir:
        cmd += ['--from-article', str(article_dir)]
    if board_name:
        cmd += ['--board', board_name]
    if expect_images is not None:
        cmd += ['--images', str(expect_images)]
    if not check_lists:
        cmd.append('--no-lists')

    # JSON 落在文章目录（有的话）或系统临时目录，不污染项目根
    try:
        if article_dir and Path(article_dir).is_dir():
            json_out = Path(article_dir) / ('_verify_%s.json' % pid)
        else:
            import tempfile
            json_out = Path(tempfile.gettempdir()) / ('bbs_verify_%s.json' % pid)
    except Exception:
        json_out = None
    if json_out is not None:
        cmd += ['--json', str(json_out)]

    print('\n' + '=' * 60)
    print('[GUARD] 独立断言验收 ->', ' '.join(str(c) for c in cmd[1:]))
    print('=' * 60)

    try:
        rc = subprocess.call(cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        print('[GUARD] !! 验收超时 %ds' % timeout)
        raise SystemExit(3)

    # 汇总，便于一眼看出 FAIL 在哪
    fails = []
    if json_out.exists():
        try:
            data = json.loads(json_out.read_text(encoding='utf-8'))
            items = data.get('items') or data.get('checks') or []
            fails = [i for i in items if str(i.get('status', '')).upper() == 'FAIL']
        except Exception:
            pass

    if rc != 0:
        print('[GUARD] FAIL %d 项 -> 帖子 %s 已发出但验收未过，需人工复核'
              % (len(fails) or rc, pid))
        for f in fails[:12]:
            print('         - %s: %s' % (f.get('name', '?'), f.get('detail', '')))
        raise SystemExit(rc or 1)

    print('[GUARD] PASS  (pid=%s)' % pid)
    return True


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='发布后验收闸门')
    ap.add_argument('pid')
    ap.add_argument('--article-dir', default=None)
    ap.add_argument('--board', default=None)
    ap.add_argument('--images', type=int, default=None)
    ap.add_argument('--no-lists', action='store_true')
    a = ap.parse_args()
    guard(a.pid, a.article_dir, a.board, a.images, check_lists=not a.no_lists)
