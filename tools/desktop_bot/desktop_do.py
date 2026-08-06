#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
desktop_do.py — 通用桌面自动化 CLI（屏幕机器人 v1.0）🤖
====================================================================
基于 mss 截图 + Windows OCR 定位 + pyautogui 键鼠模拟 + win32 剪贴板，
把「屏幕机器人」做成通用能力：任意桌面软件（微信/QQ/任意应用）都能操作。

定位策略（与 gzh_do v2.1 同源）：
  ① OCR 文字定位（默认）：截图 → Windows OCR → 找文字坐标 → 点文字中心
  ② 显式坐标：--pos 传入时优先
  —— 窗口移动/分辨率变化都不怕，只认文字在哪

命令:
  desktop_do.py check-env                       环境检查（依赖/OCR引擎）
  desktop_do.py windows [--keyword 关键字]      列出可见窗口
  desktop_do.py activate --title 关键字         激活窗口（标题模糊匹配）
  desktop_do.py screenshot --save 路径 [--region x,y,w,h]   截图
  desktop_do.py ocr [--region x,y,w,h]          全屏/区域 OCR，输出文字+坐标
  desktop_do.py click --text 文字 [--exclude 排除词] [--region x,y,w,h]   按文字点击
  desktop_do.py click-pos --pos x,y [--double]  按坐标点击
  desktop_do.py type --text 内容 [--pos x,y]    输入文本（剪贴板直写+Ctrl+V）
  desktop_do.py paste-img --path 图片 [--pos x,y]  粘贴图片到当前焦点
  desktop_do.py hotkey --keys ctrl,f            发送组合键
  desktop_do.py verify --text 文字 [--region x,y,w,h]  验证屏幕是否出现文字
  desktop_do.py send-chat --window 窗口 --search 搜索词 --message 内容 [--hotkey ctrl,f]
                                                通用聊天发送：激活→搜索→回车→粘贴→回车→验证
"""
import argparse
import ctypes
import io
import os
import subprocess
import sys
import time
from ctypes import wintypes

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))          # 7tanAI 根目录
SHOTS = os.path.join(ROOT, 'data', 'screenshots')
os.makedirs(SHOTS, exist_ok=True)

CREATE_NO_WINDOW = 0x08000000

# ---------------------------------------------------------------
# Windows OCR 引擎（winrt / winsdk 兼容，懒加载 + 复用）
# ---------------------------------------------------------------
_ocr_engine = None
_ocr_cache = {'ts': 0.0, 'lines': []}
_OCR_CACHE_TTL = 3.0
_OCR_SCALE = 0.75


def _get_ocr_engine():
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
            print('  ⚠️ OCR 不可用（缺 winrt/winsdk），文字定位将失效')
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
        print('  ⚠️ Windows OCR 引擎创建失败')
        return None
    _ocr_engine = (engine, _BD, _Stream, _Writer)
    return _ocr_engine


def _ocr_screen(region=None):
    """全屏/区域截图+OCR，返回 [{text, cx, cy}]（屏幕坐标）。3 秒缓存。"""
    if region is None and _ocr_cache['lines'] and time.time() - _ocr_cache['ts'] < _OCR_CACHE_TTL:
        return _ocr_cache['lines']
    eng = _get_ocr_engine()
    if eng is None:
        return []
    engine, BD, Stream, Writer = eng
    try:
        import mss
        from PIL import Image
    except ImportError:
        return []
    try:
        with mss.mss() as sct:
            if region:
                x, y, w, h = [int(v) for v in region.split(',')]
                shot = sct.grab({'left': x, 'top': y, 'width': w, 'height': h})
            else:
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
            writer.store_async().get_results()
        stream.seek(0)

        decoder = BD.create_async(stream).get_results()
        bitmap = decoder.get_software_bitmap_async().get_results()
        result = engine.recognize_async(bitmap).get_results()

        ox, oy = (0, 0)
        if region:
            ox, oy = int(region.split(',')[0]), int(region.split(',')[1])
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
            cx = (min(xs) + x2) / 2 / _OCR_SCALE + ox
            cy = (min(ys) + y2) / 2 / _OCR_SCALE + oy
            lines.append({'text': text, 'cx': cx, 'cy': cy})
        if region is None:
            _ocr_cache['ts'] = time.time()
            _ocr_cache['lines'] = lines
        return lines
    except Exception as e:
        print(f'  ⚠️ OCR 出错: {e}')
        return []


def _find_text(keywords, exclude=None, region=None, lines=None):
    """在 OCR 结果中找关键词，返回 (cx, cy, 命中文本) 或 None。"""
    if lines is None:
        lines = _ocr_screen(region)
    if not lines:
        return None
    exs = [e.replace(' ', '') for e in (exclude or []) if e]
    for kw in keywords:
        k = kw.replace(' ', '')
        if len(k) < 2:
            continue
        for ln in lines:
            t = ln['text']
            if not (k in t or t in k):
                continue
            if exs and any(e in t or t in e for e in exs):
                continue
            if region:
                x, y, w, h = [int(v) for v in region.split(',')]
                if not (x <= ln['cx'] <= x + w and y <= ln['cy'] <= y + h):
                    continue
            return (ln['cx'], ln['cy'], t)
    return None


# ---------------------------------------------------------------
# 剪贴板（win32clipboard 直写，毫秒级；失败回退 PowerShell）
# ---------------------------------------------------------------
def _set_clipboard_text(text):
    try:
        import win32clipboard
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        return True, ''
    except Exception as e:
        try:
            esc = text.replace("'", "''")
            cmd = ['powershell', '-NoProfile', '-Command',
                   f'Set-Clipboard -Value (Get-Content -Raw -Encoding UTF8 -LiteralPath -)'] if False else \
                  ['powershell', '-NoProfile', '-Command',
                   f"[System.Windows.Forms.Clipboard]::SetText('{esc}')"]
            r = subprocess.run(cmd, capture_output=True, timeout=15,
                               creationflags=CREATE_NO_WINDOW)
            if r.returncode == 0:
                return True, ''
            return False, f'win32clipboard+PS 均失败: {r.stderr[:200]}'
        except Exception as e2:
            return False, f'剪贴板写入失败: {e2}'


def _set_clipboard_image(path):
    try:
        import win32clipboard
        from PIL import Image
        img = Image.open(path).convert('RGB')
        buf = io.BytesIO()
        img.save(buf, 'BMP')
        data = buf.getvalue()[14:]  # 去掉 BMP 文件头，保留 DIB
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()
        return True, ''
    except Exception as e:
        return False, f'图片剪贴板失败: {e}'


# ---------------------------------------------------------------
# 窗口操作（ctypes user32，零额外依赖）
# ---------------------------------------------------------------
def _list_windows(keyword=None):
    user32 = ctypes.windll.user32
    result = []

    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        if keyword and keyword.lower() not in title.lower():
            return True
        result.append((hwnd, title))
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return result


def _activate_window(keyword):
    wins = _list_windows(keyword)
    if not wins:
        return False, f'未找到标题含「{keyword}」的窗口'
    hwnd, title = wins[0]
    user32 = ctypes.windll.user32
    try:
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.ShowWindow(hwnd, 5)      # SW_SHOW
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
    except Exception as e:
        return False, f'激活失败: {e}'
    time.sleep(0.4)
    return True, f'已激活窗口: {title}'


# ---------------------------------------------------------------
# 键鼠（pyautogui）
# ---------------------------------------------------------------
def _pyautogui():
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.05
    return pyautogui


def _screenshot(save=None, region=None):
    try:
        import mss
        from PIL import Image
    except ImportError:
        return False, '缺 mss/PIL'
    with mss.mss() as sct:
        if region:
            x, y, w, h = [int(v) for v in region.split(',')]
            shot = sct.grab({'left': x, 'top': y, 'width': w, 'height': h})
        else:
            shot = sct.grab(sct.monitors[0])
    img = Image.frombytes('RGB', shot.size, shot.rgb)
    if not save:
        save = os.path.join(SHOTS, f'desktop_{time.strftime("%Y%m%d_%H%M%S")}.png')
    img.save(save)
    return True, save


# ---------------------------------------------------------------
# 命令实现
# ---------------------------------------------------------------
def cmd_check_env():
    out = []
    for mod in ['mss', 'PIL', 'pyautogui', 'win32clipboard', 'winrt', 'winsdk']:
        try:
            __import__(mod)
            out.append(f'  ✅ {mod}')
        except ImportError:
            out.append(f'  ⚠️ {mod}（缺失，对应功能不可用）')
    if _get_ocr_engine() is not None:
        out.append('  ✅ Windows OCR 引擎（zh-Hans-CN）')
    else:
        out.append('  ⚠️ Windows OCR 引擎不可用')
    wins = _list_windows('微信')
    out.append(f'  📱 可见窗口总数: {len(_list_windows())}，含「微信」的窗口: {len(wins)}')
    return '环境检查:\n' + '\n'.join(out)


def cmd_windows(keyword):
    wins = _list_windows(keyword)
    if not wins:
        return f'未找到匹配窗口（关键字: {keyword or "全部可见"}）'
    lines = [f'{i+1}. [hwnd={hwnd}] {title}' for i, (hwnd, title) in enumerate(wins[:30])]
    return f'找到 {len(wins)} 个窗口:\n' + '\n'.join(lines)


def cmd_activate(title):
    ok, msg = _activate_window(title)
    return ('✅ ' if ok else '❌ ') + msg


def cmd_screenshot(save, region):
    ok, msg = _screenshot(save, region)
    return ('✅ 截图已保存: ' if ok else '❌ ') + msg


def cmd_ocr(region):
    lines = _ocr_screen(region)
    if not lines:
        return '（屏幕上未识别到文字）'
    out = [f'识别到 {len(lines)} 行文字:']
    for ln in lines[:60]:
        out.append(f'  ({int(ln["cx"])},{int(ln["cy"])}) {ln["text"]}')
    return '\n'.join(out)


def cmd_click_text(text, exclude, region, double):
    keywords = [k.strip() for k in text.split('|') if k.strip()]
    exs = [k.strip() for k in exclude.split('|') if k.strip()] if exclude else None
    hit = _find_text(keywords, exclude=exs, region=region)
    if not hit:
        return f'❌ 未在屏幕找到文字: {text}'
    cx, cy, found = hit
    pg = _pyautogui()
    if double:
        pg.doubleClick(cx, cy)
    else:
        pg.click(cx, cy)
    return f'✅ 已点击文字「{found}」@({int(cx)},{int(cy)})'


def cmd_click_pos(pos, double):
    x, y = [int(v) for v in pos.split(',')]
    pg = _pyautogui()
    if double:
        pg.doubleClick(x, y)
    else:
        pg.click(x, y)
    return f'✅ 已点击坐标 ({x},{y})'


def cmd_type_text(text, pos):
    pg = _pyautogui()
    if pos:
        x, y = [int(v) for v in pos.split(',')]
        pg.click(x, y)
        time.sleep(0.3)
    ok, err = _set_clipboard_text(text)
    if not ok:
        return f'❌ {err}'
    pg.hotkey('ctrl', 'v')
    return f'✅ 已粘贴文本（{len(text)} 字）'


def cmd_paste_img(path, pos):
    if not os.path.exists(path):
        return f'❌ 图片不存在: {path}'
    ok, err = _set_clipboard_image(path)
    if not ok:
        return f'❌ {err}'
    pg = _pyautogui()
    if pos:
        x, y = [int(v) for v in pos.split(',')]
        pg.click(x, y)
        time.sleep(0.3)
    pg.hotkey('ctrl', 'v')
    return f'✅ 已粘贴图片: {os.path.basename(path)}'


def cmd_hotkey(keys):
    pg = _pyautogui()
    parts = [k.strip().lower() for k in keys.split(',') if k.strip()]
    if not parts:
        return '❌ 键位为空（如 --keys ctrl,f）'
    pg.hotkey(*parts)
    return f'✅ 已发送组合键: {keys}'


def cmd_verify(text, region):
    keywords = [k.strip() for k in text.split('|') if k.strip()]
    hit = _find_text(keywords, region=region)
    if hit:
        return f'✅ 屏幕上出现文字「{hit[2]}」@({int(hit[0])},{int(hit[1])})'
    return f'❌ 屏幕未出现文字: {text}'


def cmd_send_chat(window, search, message, hotkey, verify=True):
    """通用聊天发送：激活窗口 → 搜索 → 进入聊天 → 粘贴消息 → 回车 → 验证"""
    if not message.strip():
        return '❌ 消息内容为空，拒绝发送'
    steps = []
    # 1. 激活窗口
    ok, msg = _activate_window(window)
    if not ok:
        return f'❌ {msg}'
    steps.append('激活窗口')
    time.sleep(0.4)
    # 2. 打开搜索（默认 Ctrl+F）
    pg = _pyautogui()
    try:
        parts = [k.strip().lower() for k in hotkey.split(',') if k.strip()]
        pg.hotkey(*parts)
    except Exception:
        pg.hotkey('ctrl', 'f')
    steps.append(f'打开搜索({hotkey})')
    time.sleep(0.6)
    # 3. 输入搜索词
    ok, err = _set_clipboard_text(search)
    if not ok:
        return f'❌ {err}'
    pg.hotkey('ctrl', 'v')
    steps.append(f'输入搜索词「{search}」')
    time.sleep(0.6)
    # 4. 回车进入聊天
    pg.press('enter')
    steps.append('回车进入聊天')
    time.sleep(0.6)
    # 5. 粘贴消息
    ok, err = _set_clipboard_text(message)
    if not ok:
        return f'❌ {err}'
    pg.hotkey('ctrl', 'v')
    steps.append('粘贴消息')
    time.sleep(0.3)
    # 6. 回车发送
    pg.press('enter')
    steps.append('回车发送')
    # 7. 验证上屏（可选，OCR 找消息前 6 字）
    if verify:
        time.sleep(1.0)
        probe = message.strip()[:6]
        hit = _find_text([probe])
        if hit:
            return f'✅ 发送完成（已确认消息上屏）。步骤: {"→".join(steps)}'
        return (f'⚠️ 已执行发送动作，但 OCR 未确认消息上屏（可能窗口遮挡/识别偏差）。'
                f'步骤: {"→".join(steps)}')
    return f'✅ 发送动作完成。步骤: {"→".join(steps)}'


def main():
    p = argparse.ArgumentParser(description='通用桌面自动化 CLI')
    sub = p.add_subparsers(dest='cmd')

    sub.add_parser('check-env')
    w = sub.add_parser('windows'); w.add_argument('--keyword', default='')
    a = sub.add_parser('activate'); a.add_argument('--title', required=True)
    s = sub.add_parser('screenshot'); s.add_argument('--save', default=''); s.add_argument('--region', default='')
    o = sub.add_parser('ocr'); o.add_argument('--region', default='')
    c = sub.add_parser('click'); c.add_argument('--text', required=True)
    c.add_argument('--exclude', default=''); c.add_argument('--region', default='')
    c.add_argument('--double', action='store_true')
    cp = sub.add_parser('click-pos'); cp.add_argument('--pos', required=True)
    cp.add_argument('--double', action='store_true')
    t = sub.add_parser('type'); t.add_argument('--text', required=True); t.add_argument('--pos', default='')
    pi = sub.add_parser('paste-img'); pi.add_argument('--path', required=True); pi.add_argument('--pos', default='')
    h = sub.add_parser('hotkey'); h.add_argument('--keys', required=True)
    v = sub.add_parser('verify'); v.add_argument('--text', required=True); v.add_argument('--region', default='')
    sc = sub.add_parser('send-chat')
    sc.add_argument('--window', required=True)
    sc.add_argument('--search', required=True)
    sc.add_argument('--message', required=True)
    sc.add_argument('--hotkey', default='ctrl,f')
    sc.add_argument('--no-verify', action='store_true')

    args = p.parse_args()
    cmd = args.cmd
    try:
        if cmd == 'check-env':
            print(cmd_check_env())
        elif cmd == 'windows':
            print(cmd_windows(args.keyword))
        elif cmd == 'activate':
            print(cmd_activate(args.title))
        elif cmd == 'screenshot':
            print(cmd_screenshot(args.save, args.region or None))
        elif cmd == 'ocr':
            print(cmd_ocr(args.region or None))
        elif cmd == 'click':
            print(cmd_click_text(args.text, args.exclude, args.region or None, args.double))
        elif cmd == 'click-pos':
            print(cmd_click_pos(args.pos, args.double))
        elif cmd == 'type':
            print(cmd_type_text(args.text, args.pos or None))
        elif cmd == 'paste-img':
            print(cmd_paste_img(args.path, args.pos or None))
        elif cmd == 'hotkey':
            print(cmd_hotkey(args.keys))
        elif cmd == 'verify':
            print(cmd_verify(args.text, args.region or None))
        elif cmd == 'send-chat':
            print(cmd_send_chat(args.window, args.search, args.message,
                                args.hotkey, verify=not args.no_verify))
        else:
            p.print_help()
    except KeyboardInterrupt:
        print('\n⏹ 已中断')
    except Exception as e:
        print(f'❌ 执行出错: {e}')


if __name__ == '__main__':
    main()
