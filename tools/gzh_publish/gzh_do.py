#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gzh_do.py — 公众号发布统一入口（CLI）【动态定位版 v2.1】
====================================================================
v2.1 核心改进：解决「硬编码坐标随窗口/分辨率变动而失效」的问题。

定位策略（三级 fallback 链）：
  ① OCR 文字定位（默认开启）：全屏截图(1次,缓存3s) → Windows OCR
     找到「保存草稿/发表/原创/标题/正文/摘要/封面」等文字 → 点文字中心
     —— 窗口移动、分辨率变化、浏览器缩放都不怕，只认文字在哪
  ② 显式坐标：用户传入且 ≠ 默认值时优先（最高优先级）
  ③ 默认坐标：OCR 找不到时回退历史经验值（1920x1080 布局）

规则：
  --dynamic on （默认）：OCR 优先 → 显式坐标 → 默认坐标
  --dynamic off        ：纯坐标模式（显式 → 默认），不做 OCR

性能控制（避免 CPU 100%）：
  - OCR 引擎只初始化一次，全流程复用
  - 全屏截图缩放 0.75 再识别（计算量减半）
  - 识别结果缓存 3 秒，同屏多动作不重复 OCR
  - 每步点击带 sleep 冷却

用法示例:
  python gzh_do.py check-env
  python gzh_do.py fill-form --title "标题" --author "作者"
  python gzh_do.py paste-body --file article.txt
  python gzh_do.py set-digest --text "摘要..."
  python gzh_do.py set-cover --cover cover_900x383.png
  python gzh_do.py toggle-original --on
  python gzh_do.py save-draft
  python gzh_do.py publish
  python gzh_do.py full-flow --title ... --file ... --digest ... --publish
  python gzh_do.py ocr-read --select
  python gzh_do.py save-draft --dynamic off   # 纯坐标模式
"""
import argparse
import io
import json
import os
import subprocess
import sys
import time

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))          # 7tanAI 根目录
COVER = os.path.join(HERE, 'cover_900x383.png')
ARTICLE = os.path.join(HERE, 'article_7tan_games.txt')
REGION_OCR = os.path.join(HERE, 'region_ocr.py')

# 历史调试校准的默认坐标（1920x1080 + 100% 缩放的公众号编辑页布局，仅作最终兜底）
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

# 各操作对应的 OCR 关键词（微信公众平台编辑页上的可见文字/占位符）
KEYWORDS = {
    'title':    ['请在这里输入标题', '标题'],
    'author':   ['作者'],
    'body':     ['从这里开始写正文', '正文'],
    'digest':   ['摘要'],
    'cover':    ['封面'],
    'upload':   ['上传'],
    'original': ['原创'],
    'draft':    ['保存草稿', '存草稿'],
    'publish':  ['发表'],
    'confirm':  ['确定', '发表'],
}

# ---------------------------------------------------------------
# OCR 文字定位（mss 截图 + Windows OCR，引擎复用 + 结果缓存）
# ---------------------------------------------------------------
_ocr_engine = None
_ocr_cache = {'ts': 0.0, 'lines': []}
_OCR_CACHE_TTL = 3.0          # 同屏结果缓存 3 秒
_OCR_SCALE = 0.75             # 截图缩放比，减半计算量


def _get_ocr_engine():
    """懒加载 Windows OCR 引擎（winrt / winsdk 兼容），只初始化一次。"""
    global _ocr_engine
    if _ocr_engine is not None:
        return _ocr_engine
    try:
        from winrt.windows.media.ocr import OcrEngine as _OE
        from winrt.windows.globalization import Language as _Lang
        from winrt.windows.graphics.imaging import BitmapDecoder as _BD
        from winrt.windows.storage.streams import (
            InMemoryRandomAccessStream as _Stream, DataWriter as _Writer)
    except ImportError:
        try:
            from winsdk.windows.media.ocr import OcrEngine as _OE
            from winsdk.windows.globalization import Language as _Lang
            from winsdk.windows.graphics.imaging import BitmapDecoder as _BD
            from winsdk.windows.storage.streams import (
                InMemoryRandomAccessStream as _Stream, DataWriter as _Writer)
        except ImportError:
            print('  ⚠️ OCR 定位不可用（缺 winrt/winsdk），将回退默认坐标')
            return None
    engine = None
    try:
        engine = _OE.try_create_from_language(_Lang('zh-Hans-CN'))
    except Exception:
        engine = None
    if engine is None:
        try:
            engine = _OE.try_create_from_user_profile_languages()
        except Exception:
            engine = None
    if engine is None:
        print('  ⚠️ Windows OCR 引擎创建失败，将回退默认坐标')
        return None
    _ocr_engine = (engine, _BD, _Stream, _Writer)
    return _ocr_engine


def _ocr_screen():
    """全屏截图+OCR，返回 [{text, cx, cy}]（屏幕坐标）。带 3 秒缓存。"""
    now = time.time()
    if now - _ocr_cache['ts'] < _OCR_CACHE_TTL and _ocr_cache['lines']:
        return _ocr_cache['lines']
    eng = _get_ocr_engine()
    if eng is None:
        return []
    engine, BD, Stream, Writer = eng
    try:
        import mss
        from PIL import Image
    except ImportError:
        print('  ⚠️ 缺 mss/PIL，OCR 定位不可用')
        return []
    try:
        with mss.mss() as sct:
            shot = sct.grab(sct.monitors[0])
        img = Image.frombytes('RGB', shot.size, shot.rgb)
        sw, sh = shot.size
        if _OCR_SCALE and _OCR_SCALE != 1.0:
            img = img.resize((max(1, int(sw * _OCR_SCALE)),
                              max(1, int(sh * _OCR_SCALE))), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        data = buf.getvalue()

        stream = Stream()
        writer = Writer(stream)
        writer.write_bytes(data)
        if hasattr(writer, 'store'):
            writer.store()
        else:
            writer.store_async().get()
        stream.seek(0)

        decoder = BD.create_async(stream).get()
        bitmap = decoder.get_software_bitmap_async().get()
        result = engine.recognize_async(bitmap).get()

        lines = []
        for line in result.lines:
            words = list(line.words)
            if not words:
                continue
            text = ''.join(w.text for w in words)
            text = text.replace(' ', '').replace('\u3000', '').strip()
            if not text:
                continue
            xs = [w.bounding_rect.x for w in words]
            ys = [w.bounding_rect.y for w in words]
            x2 = max(w.bounding_rect.x + w.bounding_rect.width for w in words)
            y2 = max(w.bounding_rect.y + w.bounding_rect.height for w in words)
            cx = (min(xs) + x2) / 2 / _OCR_SCALE
            cy = (min(ys) + y2) / 2 / _OCR_SCALE
            lines.append({'text': text, 'cx': cx, 'cy': cy})
        _ocr_cache['ts'] = time.time()
        _ocr_cache['lines'] = lines
        return lines
    except Exception as e:
        print(f'  ⚠️ OCR 定位出错: {e}')
        return []


def _find_text(keywords, lines=None):
    """在 OCR 结果中找关键词，返回 (cx, cy, 命中文本) 或 None。
    匹配规则：关键词与识别文本互为子串（长度>=2），避免误匹配。"""
    if lines is None:
        lines = _ocr_screen()
    if not lines:
        return None
    for kw in keywords:
        k = kw.replace(' ', '')
        if len(k) < 2:
            continue
        for ln in lines:
            t = ln['text']
            if k in t or t in k:
                return (ln['cx'], ln['cy'], t)
    return None


# ---------------------------------------------------------------
# 三级定位：OCR 文字定位 > 显式坐标 > 默认坐标
# ---------------------------------------------------------------
def parse_pos(s, default):
    s = s or default
    try:
        x, y = s.split(',')
        return int(x.strip()), int(y.strip())
    except Exception:
        return tuple(int(v) for v in default.split(','))


def resolve(args, key, kw=None):
    """解析某操作的最终坐标。key=DEFAULTS键名，kw=KEYWORDS键名（默认同key）。
    返回 (pos, source)：source ∈ {ocr[文本], explicit, default}"""
    kw = kw or key
    val = getattr(args, key + '_pos', '') or ''
    default = DEFAULTS.get(key + '_pos', '0,0')
    explicit = val if val and val != default else None   # 用户显式传了非默认坐标

    if args.dynamic != 'off' and not explicit:
        hit = _find_text(KEYWORDS.get(kw, []))
        if hit:
            return (int(hit[0]), int(hit[1])), f'ocr[{hit[2]}]'

    pos = parse_pos(explicit or val, default)
    return pos, ('explicit' if explicit else 'default')


def ensure_deps():
    """非 check-env 动作前调用，确保依赖库可用"""
    try:
        import pyautogui  # noqa: F401
        import pyperclip  # noqa: F401
    except ImportError as e:
        print(f'❌ 缺少依赖: {e}')
        print('   请安装: pip install pyautogui pyperclip mss pillow winrt')
        sys.exit(2)
    import pyautogui
    import pyperclip
    return pyautogui, pyperclip


def front_window():
    """尝试把微信/浏览器窗口前置（找不到则忽略）"""
    try:
        import pygetwindow as gw
        wins = [w for w in gw.getAllWindows()
                if w.title and ('微信' in w.title or 'WeChat' in w.title
                                or '公众平台' in w.title or 'mp.weixin' in w.title)]
        if wins:
            try:
                wins[0].activate()
            except Exception:
                pass
            time.sleep(0.8)
            print('  ↪ 已尝试前置目标窗口')
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
                  if w.title and ('微信' in w.title or 'WeChat' in w.title
                                  or '公众平台' in w.title)]
        print(f'  💬 目标窗口: {titles if titles else "未找到（请先打开微信公众平台编辑页）"}')
    except Exception:
        print('  ⚠️ pygetwindow 不可用，跳过窗口检测')
    print('  📐 OCR 定位: ' +
          ('✅ 可用' if _get_ocr_engine() else '❌ 不可用（将回退默认坐标）'))
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
    if args.title:
        pos, src = resolve(args, 'title')
        click_paste(pg, pc, pos, args.title)
        print(f'  ✅ 标题已填入 {pos} [{src}]: {args.title[:30]}…')
    if args.author:
        pos, src = resolve(args, 'author')
        click_paste(pg, pc, pos, args.author)
        print(f'  ✅ 作者已填入 {pos} [{src}]: {args.author}')
    if not args.title and not args.author:
        print('  ⚠️ 未提供 --title / --author')


def cmd_paste_body(args, pg, pc):
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
    bp, src = resolve(args, 'body')
    pg.click(bp[0], bp[1])
    time.sleep(0.8)
    pg.click(bp[0], bp[1])
    time.sleep(0.5)
    print(f'  ↪ 已点击正文区 {bp} [{src}]')
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
    if not args.text:
        print('  ⚠️ 请用 --text 提供摘要（120 字内）')
        return
    dp, src = resolve(args, 'digest')
    click_paste(pg, pc, dp, args.text)
    print(f'  ✅ 摘要已填入 {dp} [{src}]: {args.text[:40]}…')


def cmd_set_cover(args, pg, pc):
    cover = args.cover or COVER
    if not os.path.exists(cover):
        print(f'  ❌ 封面不存在: {cover}')
        return
    cp, src = resolve(args, 'cover')
    pg.click(cp[0], cp[1])
    time.sleep(2.0)
    print(f'  ↪ 已点击封面区 {cp} [{src}]')
    up, usrc = resolve(args, 'upload')
    pg.click(up[0], up[1])
    time.sleep(2.0)
    print(f'  ↪ 已点击上传按钮 {up} [{usrc}]')
    pc.copy(os.path.abspath(cover))
    time.sleep(0.5)
    pg.hotkey('ctrl', 'v')
    time.sleep(0.8)
    pg.press('enter')
    time.sleep(3.0)
    print(f'  ✅ 封面路径已提交: {cover}')


def cmd_toggle_original(args, pg, pc):
    op, src = resolve(args, 'original')
    pg.click(op[0], op[1])
    time.sleep(1.5)
    print(f'  ✅ 已点击原创开关 {op} [{src}]（{"目标：开启" if args.on else "点击即切换状态"}）')


def cmd_save_draft(args, pg, pc):
    dp, src = resolve(args, 'draft')
    pg.click(dp[0], dp[1])
    time.sleep(3.0)
    print(f'  ✅ 已点击保存草稿 {dp} [{src}]')


def cmd_publish(args, pg, pc):
    # 优先 OCR 找「发表」按钮（窗口/分辨率变化也能命中）
    pub, psrc = None, 'default'
    if args.dynamic != 'off':
        hit = _find_text(KEYWORDS['publish'])
        if hit:
            pub = (int(hit[0]), int(hit[1]))
            psrc = f'ocr[{hit[2]}]'
    if pub is None:
        # OCR 未命中：回退「保存草稿右侧第3个按钮」经验位
        dp, _ = resolve(args, 'draft')
        pub = (dp[0] + 260, dp[1])
        psrc = 'default(+260)'
    pg.click(pub[0], pub[1])
    time.sleep(2.0)
    pg.click(pub[0], pub[1])
    time.sleep(2.5)
    print(f'  ↪ 已点击发表按钮 {pub} [{psrc}]')
    cp, csrc = resolve(args, 'publish_confirm', kw='confirm')
    pg.click(cp[0], cp[1])
    time.sleep(5.0)
    print(f'  ✅ 已点击发表弹窗确认 {cp} [{csrc}]')


def cmd_full_flow(args, pg, pc):
    print('===== 公众号发布全流程开始（动态定位） =====')
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
    p = argparse.ArgumentParser(description='公众号发布统一入口（动态定位版）')
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
    p.add_argument('--dynamic', default='on', choices=['on', 'off'],
                   help='OCR 文字动态定位（默认 on；off=纯坐标模式）')
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
