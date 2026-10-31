# -*- coding: utf-8 -*-
"""发布后独立断言闸门（Router 层之外的第一道 Watchdog）

用法（在 publish_*.py 末尾）：

    from publish_guard import guard
    guard(pid, WS, board_name='游戏交流', expect_images=26)
    # 也可以什么都不传：guard 会从调用脚本的全局变量里自动取

行为：
  - 以子进程调用 tools/bbs_verify.py，纯 HTTP 断言，不读数据库、不碰密码
  - 返回码 0 = 全部 PASS/SKIP；非 0 = 有 FAIL，抛 SystemExit 让发布脚本停住
  - 一旦日志里出现 FAIL，说明「我口头说发好了」这条路被切断

── 2026-11-01 增加两项（此前是缺口） ────────────────────────
  1) 参数自动推导（原来一律吃默认值 uid=1 / author='老马'）
     调用脚本里通常已有 BOARD / USER_ID / NICK 这些变量，但没人把它们传进来，
     于是作者维度断言永远拿默认值 —— 换个作者发帖就会失真。
     现在 guard 从调用方 frame 的 globals 里按候选名取，取不到才用默认，
     并且【把每个参数的实际来源打印出来】，不再静默吃默认值。

  2) 幂等标记（原来每次重跑都全量验收一遍）
     验收通过后在文章目录写 _guard_<pid>.json（含指纹：图数/板块/uid/作者）。
     再次运行时指纹一致且上次 PASS → 直接 SKIP，不重复打网络请求。
     指纹变化（改了图数/板块/作者）或上次 FAIL → 照常重跑。
     force=True 可强制重验。

设计原则：
  1. 不信任调用方给的期望值，图数优先从文章目录推导
  2. 默认查 board 列表 / 首页 / 作者主页三处收录（首页缓存漏清是历史真事故）
  3. 只在 rc!=0 时抛异常，不删除已发布的帖子
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

VERIFY = Path(__file__).resolve().parent / 'bbs_verify.py'

# 从调用脚本 globals 里自动推导参数的候选名（按顺序取第一个非空的）
_KEYS_BOARD_NAME = ('BOARD_NAME', 'BOARD_TITLE')
_KEYS_BOARD_ID = ('BOARD', 'BOARD_ID', 'FID')
_KEYS_UID = ('USER_ID', 'UID', 'AUTHOR_UID', 'MY_UID')
_KEYS_AUTHOR = ('NICK', 'AUTHOR', 'AUTHOR_NAME', 'USERNAME')

DEFAULT_UID = 1
DEFAULT_AUTHOR = '老马'


def _pick(globals_dict, keys):
    """从 globals 里按候选名取第一个非空值，返回 (值, 变量名) 或 (None, None)。"""
    for k in keys:
        if k in globals_dict:
            v = globals_dict[k]
            if v not in (None, '', 0):
                return v, k
    return None, None


def _caller_globals() -> dict:
    """取 guard 调用方的模块 globals（publish_*.py 的顶层变量都在这里）。"""
    try:
        return sys._getframe(2).f_globals or {}
    except Exception:
        return {}


def _fingerprint(pid, images, board, uid, author) -> str:
    payload = json.dumps(
        {'pid': str(pid), 'images': images, 'board': str(board),
         'uid': str(uid), 'author': str(author)},
        sort_keys=True, ensure_ascii=False,
    )
    return hashlib.sha1(payload.encode('utf-8')).hexdigest()


def _marker_path(article_dir, pid):
    try:
        if article_dir and Path(article_dir).is_dir():
            return Path(article_dir) / ('_guard_%s.json' % pid)
    except Exception:
        pass
    return None


def guard(pid, article_dir=None, board_name=None, expect_images=None,
          uid=None, author=None, check_lists=True, timeout=240, quiet=False,
          force=False):
    """发布后跑 bbs_verify，失败抛 SystemExit。

    Args:
        pid: 帖子 id
        article_dir: 文章目录（用于推导标题/图数/小节数），可为空
        board_name: 期望板块名（如 '游戏交流'）或板块 id（如 18）；
                    留空则从调用脚本的 BOARD/BOARD_NAME 自动取
        expect_images: 期望图片数；为空则从 article_dir 推导
        uid: 作者 uid；留空从脚本的 USER_ID/UID 取，再不行用默认 1
        author: 作者昵称；留空从脚本的 NICK/AUTHOR 取，再不行用默认 '老马'
        check_lists: 是否检查 board 列表 / 首页 / 作者主页收录
        timeout: 子进程超时秒
        quiet: True 则只打印结论
        force: True 则忽略幂等标记，强制重验

    Returns:
        True（失败会抛异常，不会走到返回）
    """
    # ── ① 参数推导：调用方没传的，从脚本 globals 里取，取不到才用默认 ──
    g = _caller_globals()
    src = {}

    if board_name in (None, ''):
        v, k = _pick(g, _KEYS_BOARD_NAME)
        if v is None:
            v, k = _pick(g, _KEYS_BOARD_ID)
        if v is not None:
            board_name = v
            src['board'] = k
    else:
        src['board'] = '显式传入'

    if uid in (None, ''):
        v, k = _pick(g, _KEYS_UID)
        if v is not None:
            uid, src['uid'] = v, k
        else:
            uid, src['uid'] = DEFAULT_UID, '默认值'
    else:
        src['uid'] = '显式传入'

    if author in (None, ''):
        v, k = _pick(g, _KEYS_AUTHOR)
        if v is not None:
            author, src['author'] = v, k
        else:
            author, src['author'] = DEFAULT_AUTHOR, '默认值'
    else:
        src['author'] = '显式传入'

    # ── ② 幂等：指纹一致且上次 PASS → 跳过，不重复打网络请求 ──
    fp = _fingerprint(pid, expect_images, board_name, uid, author)
    marker = _marker_path(article_dir, pid)
    if marker is not None and not force and marker.exists():
        try:
            old = json.loads(marker.read_text(encoding='utf-8'))
            if old.get('status') == 'PASS' and old.get('fp') == fp:
                if not quiet:
                    print('[GUARD] SKIP 本贴本轮已验收通过（指纹 %s，%s），不重复验收。'
                          % (fp[:12], old.get('ts')))
                    print('        如需重验：guard(..., force=True) 或删掉 %s' % marker.name)
                return True
            if old.get('fp') != fp:
                if not quiet:
                    print('[GUARD] 期望值有变化（指纹 %s → %s），重新验收'
                          % (str(old.get('fp'))[:12], fp[:12]))
        except Exception:
            pass

    # ── ③ 组命令 ──
    cmd = [sys.executable, str(VERIFY), str(pid),
           '--uid', str(uid), '--author', str(author)]

    if article_dir:
        cmd += ['--from-article', str(article_dir)]
    if board_name not in (None, ''):
        cmd += ['--board', str(board_name)]
    if expect_images is not None:
        cmd += ['--images', str(expect_images)]
    if not check_lists:
        cmd.append('--no-lists')

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
    print('[GUARD] 参数来源: board=%r(%s)  uid=%r(%s)  author=%r(%s)  images=%r'
          % (board_name, src.get('board'), uid, src.get('uid'),
             author, src.get('author'), expect_images))
    if src.get('uid') == '默认值' or src.get('author') == '默认值':
        print('[GUARD] ⚠️ 有参数仍在使用默认值。若本贴作者不是老马(uid=1)，作者维度断言会失真。')
    print('[GUARD] 独立断言验收 ->', ' '.join(str(c) for c in cmd[1:]))
    print('=' * 60)

    try:
        rc = subprocess.call(cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        print('[GUARD] !! 验收超时 %ds' % timeout)
        raise SystemExit(3)

    # 汇总，便于一眼看出 FAIL 在哪
    fails = []
    if json_out is not None and json_out.exists():
        try:
            data = json.loads(json_out.read_text(encoding='utf-8'))
            items = data.get('items') or data.get('checks') or []
            fails = [i for i in items if str(i.get('status', '')).upper() == 'FAIL']
        except Exception:
            pass

    # ── ④ 落标记（无论成败，供下次幂等判断） ──
    if marker is not None:
        try:
            marker.write_text(json.dumps({
                'pid': str(pid),
                'status': 'PASS' if rc == 0 else 'FAIL',
                'fp': fp,
                'rc': rc,
                'ts': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'board': str(board_name), 'uid': str(uid), 'author': str(author),
                'images': expect_images,
                'src': src,
                'fails': [str(f.get('name')) for f in fails[:10]],
            }, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception as e:
            print('[GUARD] ⚠️ 幂等标记写入失败: %s' % e)

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
    ap.add_argument('--uid', default=None)
    ap.add_argument('--author', default=None)
    ap.add_argument('--force', action='store_true', help='忽略幂等标记，强制重验')
    ap.add_argument('--no-lists', action='store_true')
    a = ap.parse_args()
    guard(a.pid, a.article_dir, a.board, a.images, uid=a.uid, author=a.author,
          check_lists=not a.no_lists, force=a.force)
