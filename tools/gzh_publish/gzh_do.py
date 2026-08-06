#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gzh_do.py — 公众号发布统一入口（CLI）
整合 tools/gzh_publish 套件的全部成熟动作（坐标均为历史调试经验值，可参数化覆盖），
供插件 gzh_publish 通过 subprocess 调用。

动作:
  check-env            检查依赖库 / 微信窗口 / CDP 端口
  fill-form            填标题 + 作者（剪贴板粘贴，兼容中文）
  paste-body           粘贴正文（纯文本文件 / --text / JSON 图文序列）
  set-digest           填摘要（120 字内）
  set-cover            上传封面（点击封面区 → 上传按钮 → 文件对话框粘贴路径回车）
  toggle-original      点击原创声明开关
  save-draft           保存草稿
  publish              发表（点发表按钮 + 弹窗确认）
  full-flow            全流程（标题→正文→摘要→封面→原创→草稿[→发表]）
  ocr-read             区域OCR（复用 region_ocr.py，读阅读量/界面文字）

用法示例:
  python gzh_do.py check-env
  python gzh_do.py fill-form --title "标题" --author "作者"
  python gzh_do.py paste-body --file article.txt
  python gzh_do.py set-digest --text "摘要..."
  python gzh_do.py set-cover --cover cover_900x383.png
  python gzh_do.py toggle-original
  python gzh_do.py save-draft
  python gzh_do.py publish
  python gzh_do.py ocr-read --select
"""
import argparse
import ctypes
import io
import json
import os
import subprocess
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))          # 7tanAI 根目录
COVER = os.path.join(HERE, 'cover_900x383.png')
ARTICLE = os.path.join(HERE, 'article_7tan_games.txt')
REGION_OCR = os.path.join(HERE, 'region_ocr.py')

# 历史调试校准的默认坐标（基于 1920x1080 + 100% 缩放的公众号编辑页布局）
DEFAULTS = {
    'title_pos': '460,420',        # 标题输入框
    'author_pos': '410,462',       # 作者输入框
    'body_pos': '500,560',         # 正文编辑区
    'digest_pos': '550,478',       # 摘要输入框
    'cover_pos': '490,512',        # 封面区
    'upload_pos': '800,528',       # 封面弹窗「上传」按钮
    'original_pos': '750,518',     # 原创声明开关
    'draft_pos': '760,931',        # 「保存草稿」按钮
    'publish_confirm_pos': '458,456',  # 发表弹窗「发表」确认按钮
}


def parse_pos(s, default):
    s = s or default
    try:
        x, y = s.split(',')
        return int(x.strip()), int(y.strip())
    except Exception:
        return tuple(int(v) for v in default.split(','))


def ensure_deps():
    """非 check-env 动作前调用，确保依赖库可用"""
    try:
        import pyautogui  # noqa: F401
        import pyperclip  # noqa: F401
    except ImportError as e:
        print(f'❌ 缺少依赖: {e}')
        print('   请安装: pip install pyautogui pyperclip')
        sys.exit(2)
    import pyautogui
    import pyperclip
    return pyautogui, pyperclip


def front_window():
    """尝试把微信窗口前置（找不到则忽略，点击作用于当前前台窗口）"""
    try:
        import pygetwindow as gw
        wins = [w for w in gw.getAllWindows()
                if w.title and ('微信' in w.title or 'WeChat' in w.title)]
        if wins:
            try:
                wins[0].activate()
            except Exception:
                pass
            time.sleep(0.8)
            print('  ↪ 已尝试前置微信窗口')
            return True
    except Exception:
        pass
    return False


def click_paste(pg, pc, pos, text, pause=0.5):
    """双击定位 + 剪贴板粘贴（兼容中文）"""
    pg.click(pos[0], pos[1])
    time.sleep(pause)
    pg.click(pos[0], pos[1])
    time.sleep(pause * 0.5)
    pc.copy(text)
    time.sleep(0.3)
    pg.hotkey('ctrl', 'v')
    time.sleep(0.8)


# ---------------- 各动作实现 ----------------

def cmd_check_env(args):
    print('===== 公众号发布环境检查 =====')
    for m in ('pyautogui', 'pyperclip', 'mss', 'PIL', 'winrt', 'pygetwindow'):
        try:
            __import__(m)
            print(f'  ✅ {m} 已安装')
        except Exception:
            print(f'  ❌ {m} 缺失（pip install {m}）')
    try:
        import pygetwindow as gw
        titles = [w.title for w in gw.getAllWindows()
                  if w.title and ('微信' in w.title or 'WeChat' in w.title)]
        print(f'  💬 微信窗口: {titles if titles else "未找到（请先登录微信PC版）"}')
    except Exception:
        print('  ⚠️ pygetwindow 不可用，跳过窗口检测')
    import urllib.request
    for port in (9222, 9223, 9333, 9515, 17889):
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/json', timeout=2) as r:
                tabs = len(json.loads(r.read().decode('utf-8', 'replace')))
                print(f'  🌐 CDP 端口 {port} 开放（{tabs} 个页面）')
        except Exception:
            pass
    print('===== END =====')


def cmd_fill_form(args, pg, pc):
    tp = parse_pos(args.title_pos, DEFAULTS['title_pos'])
    ap = parse_pos(args.author_pos, DEFAULTS['author_pos'])
    if args.title:
        click_paste(pg, pc, tp, args.title)
        print(f'  ✅ 标题已填入 {tp}: {args.title[:30]}…')
    if args.author:
        click_paste(pg, pc, ap, args.author)
        print(f'  ✅ 作者已填入 {ap}: {args.author}')
    if not args.title and not args.author:
        print('  ⚠️ 未提供 --title / --author')


def cmd_paste_body(args, pg, pc):
    bp = parse_pos(args.body_pos, DEFAULTS['body_pos'])
    if args.sequence:
        try:
            seq = json.load(open(args.sequence, encoding='utf-8'))
        except Exception as e:
            print(f'  ❌ 序列文件解析失败: {e}')
            return
    elif args.text:
        seq = [{'type': 'text', 'content': args.text}]
    elif args.file:
        try:
            seq = [{'type': 'text', 'content': open(args.file, encoding='utf-8').read()}]
        except Exception as e:
            print(f'  ❌ 正文文件读取失败: {e}')
            return
    else:
        try:
            seq = [{'type': 'text', 'content': open(ARTICLE, encoding='utf-8').read()}]
        except Exception as e:
            print(f'  ❌ 默认正文读取失败: {e}')
            return
    pg.click(bp[0], bp[1])
    time.sleep(0.8)
    pg.click(bp[0], bp[1])
    time.sleep(0.5)
    print(f'  ↪ 已点击正文区 {bp}')
    img_dir = args.img_dir or os.path.join(ROOT, 'downloads', 'article4_shots')
    for item in seq:
        if item.get('type') == 'text':
            click_paste(pg, pc, bp, item['content'], pause=0.3)
            print(f'  ✅ 粘贴文本 {len(item["content"])} 字')
        elif item.get('type') == 'img':
            path = item.get('file', '')
            if not os.path.isabs(path):
                path = os.path.join(img_dir, path)
            if not os.path.exists(path):
                print(f'  ⚠️ 图片不存在，跳过: {path}')
                continue
            try:
                cmd = ['powershell', '-NoProfile', '-Command', f"Set-Clipboard -Path '{path}'"]
                subprocess.run(cmd, capture_output=True, timeout=30, shell=True)
            except Exception as e:
                print(f'  ⚠️ 图片放入剪贴板失败: {e}')
                continue
            time.sleep(0.8)
            pg.hotkey('ctrl', 'v')
            time.sleep(1.5)
            print(f'  ✅ 粘贴图片: {os.path.basename(path)}')
    print('  ✅ 正文粘贴完成')


def cmd_set_digest(args, pg, pc):
    dp = parse_pos(args.digest_pos, DEFAULTS['digest_pos'])
    if not args.text:
        print('  ⚠️ 请用 --text 提供摘要（120 字内）')
        return
    click_paste(pg, pc, dp, args.text)
    print(f'  ✅ 摘要已填入 {dp}: {args.text[:40]}…')


def cmd_set_cover(args, pg, pc):
    cp = parse_pos(args.cover_pos, DEFAULTS['cover_pos'])
    up = parse_pos(args.upload_pos, DEFAULTS['upload_pos'])
    cover = args.cover or COVER
    if not os.path.exists(cover):
        print(f'  ❌ 封面不存在: {cover}')
        return
    pg.click(cp[0], cp[1])
    time.sleep(2.0)
    print(f'  ↪ 已点击封面区 {cp}')
    pg.click(up[0], up[1])
    time.sleep(2.0)
    print(f'  ↪ 已点击上传按钮 {up}')
    pc.copy(os.path.abspath(cover))
    time.sleep(0.5)
    pg.hotkey('ctrl', 'v')
    time.sleep(0.8)
    pg.press('enter')
    time.sleep(3.0)
    print(f'  ✅ 封面路径已提交: {cover}')


def cmd_toggle_original(args, pg, pc):
    op = parse_pos(args.original_pos, DEFAULTS['original_pos'])
    pg.click(op[0], op[1])
    time.sleep(1.5)
    print(f'  ✅ 已点击原创开关 {op}（{"目标：开启" if args.on else "点击即切换状态"}）')


def cmd_save_draft(args, pg, pc):
    dp = parse_pos(args.draft_pos, DEFAULTS['draft_pos'])
    pg.click(dp[0], dp[1])
    time.sleep(3.0)
    print(f'  ✅ 已点击保存草稿 {dp}')


def cmd_publish(args, pg, pc):
    dp = parse_pos(args.draft_pos, DEFAULTS['draft_pos'])
    # 发表按钮位于保存草稿右侧第3个按钮（README 实测经验）
    px, py = dp[0] + 260, dp[1]
    pg.click(px, py)
    time.sleep(2.0)
    pg.click(px, py)
    time.sleep(2.5)
    print(f'  ↪ 已点击发表按钮 ({px},{py})')
    cp = parse_pos(args.confirm_pos, DEFAULTS['publish_confirm_pos'])
    pg.click(cp[0], cp[1])
    time.sleep(5.0)
    print(f'  ✅ 已点击发表弹窗确认 ({cp})')


def cmd_full_flow(args, pg, pc):
    print('===== 公众号发布全流程开始 =====')
    cmd_fill_form(args, pg, pc)
    cmd_paste_body(args, pg, pc)
    if args.digest:
        old_text = args.text
        args.text = args.digest
        cmd_set_digest(args, pg, pc)
        args.text = old_text
    if not args.skip_cover:
        cmd_set_cover(args, pg, pc)
    if not args.skip_original:
        cmd_toggle_original(args, pg, pc)
    cmd_save_draft(args, pg, pc)
    if args.publish:
        cmd_publish(args, pg, pc)
    print('===== 全流程执行完毕 =====')


def cmd_ocr_read(args):
    cmd = [sys.executable, REGION_OCR]
    if args.select:
        cmd.append('--select')
    elif args.region:
        cmd += ['--region', args.region]
    if args.scale:
        cmd += ['--scale', str(args.scale)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=120)
        print(r.stdout or '')
        if r.returncode != 0:
            print('[stderr]', (r.stderr or '')[-1500:])
    except Exception as e:
        print(f'❌ OCR 执行失败: {e}')


def main():
    p = argparse.ArgumentParser(description='公众号发布统一入口')
    p.add_argument('action', choices=[
        'check-env', 'fill-form', 'paste-body', 'set-digest', 'set-cover',
        'toggle-original', 'save-draft', 'publish', 'full-flow', 'ocr-read'])
    p.add_argument('--title', default='', help='文章标题')
    p.add_argument('--author', default='', help='作者')
    p.add_argument('--text', default='', help='正文/摘要文本')
    p.add_argument('--file', default='', help='正文文本文件路径')
    p.add_argument('--sequence', default='', help='图文序列 JSON 文件路径')
    p.add_argument('--img-dir', default='', help='图片目录（sequence 用）')
    p.add_argument('--digest', default='', help='摘要（full-flow 用）')
    p.add_argument('--cover', default='', help='封面图片路径')
    p.add_argument('--on', action='store_true', help='toggle-original 目标为开启')
    p.add_argument('--publish', action='store_true', help='full-flow 末尾追加发表')
    p.add_argument('--skip-cover', action='store_true', help='full-flow 跳过封面')
    p.add_argument('--skip-original', action='store_true', help='full-flow 跳过原创')
    p.add_argument('--select', action='store_true', help='ocr-read 框选模式')
    p.add_argument('--region', default='', help='ocr-read 区域 x,y,w,h')
    p.add_argument('--scale', type=float, default=0, help='ocr-read 缩放')
    p.add_argument('--confirm-pos', default='', help='发表弹窗确认坐标')
    for key, val in DEFAULTS.items():
        p.add_argument(f'--{key}', default=val, help=f'坐标（默认 {val}）')
    args = p.parse_args()

    if args.action == 'check-env':
        cmd_check_env(args)
        return
    if args.action == 'ocr-read':
        cmd_ocr_read(args)
        return

    pg, pc = ensure_deps()
    front_window()
    if args.action == 'fill-form':
        cmd_fill_form(args, pg, pc)
    elif args.action == 'paste-body':
        cmd_paste_body(args, pg, pc)
    elif args.action == 'set-digest':
        cmd_set_digest(args, pg, pc)
    elif args.action == 'set-cover':
        cmd_set_cover(args, pg, pc)
    elif args.action == 'toggle-original':
        cmd_toggle_original(args, pg, pc)
    elif args.action == 'save-draft':
        cmd_save_draft(args, pg, pc)
    elif args.action == 'publish':
        cmd_publish(args, pg, pc)
    elif args.action == 'full-flow':
        cmd_full_flow(args, pg, pc)
    else:
        p.print_help()


if __name__ == '__main__':
    main()
