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

# ---------------------------------------------------------------
# RapidOCR 离线引擎（PP-OCRv4，中文识别精度高，作为 Windows OCR 的补充/兜底）
# ---------------------------------------------------------------
_rapid_engine = None


def _get_rapid_engine():
    """懒加载 RapidOCR 单例（onnxruntime 离线推理，无需联网）"""
    global _rapid_engine
    if _rapid_engine is not None:
        return _rapid_engine
    try:
        from rapidocr_onnxruntime import RapidOCR
        _rapid_engine = RapidOCR()
        return _rapid_engine
    except Exception as e:
        print(f'  ⚠️ RapidOCR 不可用: {e}')
        return None


def _ocr_screen_rapid(region=None, scale=1.0):
    """RapidOCR 识别屏幕，返回 [{text, cx, cy}]（屏幕坐标）。离线、中文精度高。"""
    eng = _get_rapid_engine()
    if eng is None:
        return []
    try:
        import mss
        from PIL import Image
        import numpy as np
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
        if scale != 1.0:
            img = img.resize((max(1, int(img.width * scale)),
                              max(1, int(img.height * scale))), Image.LANCZOS)
        arr = np.array(img.convert('RGB'))
        result, _ = eng(arr)
        ox, oy = (0, 0)
        if region:
            ox, oy = int(region.split(',')[0]), int(region.split(',')[1])
        lines = []
        if result:
            for box, text, score in result:
                if not text or not str(text).strip():
                    continue
                t = str(text).strip()
                xs = [p[0] for p in box]
                ys = [p[1] for p in box]
                cx = (min(xs) + max(xs)) / 2 / scale + ox
                cy = (min(ys) + max(ys)) / 2 / scale + oy
                lines.append({'text': t, 'cx': cx, 'cy': cy, 'engine': 'rapid'})
        return lines
    except Exception as e:
        print(f'  ⚠️ RapidOCR 出错: {e}')
        return []


def _ocr_garbage_ratio(lines):
    """估算 OCR 文本乱码比例（行级）：含异常字符（拉丁扩展符号 ø«Æﬂ©®、生僻扩展区、私用区、字母连字）
    的行占比。深色UI/复杂界面 Windows OCR 常输出这类乱码符号，干净界面几乎为 0。"""
    import re
    if not lines:
        return 1.0
    # ø(\u00F8) «(\u00AB) Æ(\u00C6) ﬂ(\uFB02) ©(\u00A9) 等：正常中文界面不会出现
    bad_pat = re.compile(r'[\u00A2-\u02AF\uFB00-\uFBFF\u3400-\u4DBF\uE000-\uF8FF\uF900-\uFAFF]')
    bad_lines = sum(1 for ln in lines if bad_pat.search(ln['text']))
    return bad_lines / len(lines)


def _merge_ocr_lines(win_lines, rapid_lines):
    """双引擎结果按中心点距离+文本相似度去重合并：距离<20px 且编辑距离≤2 视为同一行（保留更长者）；
    距离近但文本完全不同（可能是相邻两行）则都保留，避免误合并丢字。"""
    merged = []
    for ln in (win_lines or []) + (rapid_lines or []):
        dup = False
        for m in merged:
            if abs(m['cx'] - ln['cx']) < 20 and abs(m['cy'] - ln['cy']) < 20:
                if _edit_distance(m['text'], ln['text']) <= 2:
                    if len(ln['text']) > len(m['text']):
                        m['text'] = ln['text']
                    dup = True
                    break
        if not dup:
            merged.append(dict(ln))
    return merged


def _ocr_screen(region=None, engine='auto'):
    """全屏/区域 OCR 入口：auto=Windows OCR 优先、空则 RapidOCR 兜底；
    win=仅 Windows OCR；rapid=仅 RapidOCR；fusion=双引擎融合去重。"""
    if engine == 'rapid':
        return _ocr_screen_rapid(region)
    if engine == 'fusion':
        win_lines = _ocr_screen(region, engine='win')
        # RapidOCR 半分辨率识别：全屏 35s → ~25s，坐标已在 _ocr_screen_rapid 内按 scale 还原
        rapid_lines = _ocr_screen_rapid(region, scale=0.5)
        return _merge_ocr_lines(win_lines, rapid_lines)
    if engine == 'smart':
        # 自适应：仅当 Windows OCR 几乎完美（无坏字符、无碎片、行数充足）才直接用（秒出）；
        # 否则自动融合 RapidOCR（准）。判定从严，宁可多花时间也要准确。
        win_lines = _ocr_screen_win(region)
        if win_lines and len(win_lines) >= 20:
            ratio = _ocr_garbage_ratio(win_lines)
            frag = sum(1 for ln in win_lines if len(ln['text']) <= 2) / len(win_lines)
            if ratio < 0.06 and frag < 0.15:
                return win_lines
        rapid_lines = _ocr_screen_rapid(region, scale=0.5)
        return _merge_ocr_lines(win_lines, rapid_lines)
    if engine == 'win':
        return _ocr_screen_win(region)
    # auto：Windows OCR 优先，识别为空时 RapidOCR 兜底（不缓存 rapid 结果）
    lines = _ocr_screen_win(region)
    if not lines:
        lines = _ocr_screen_rapid(region)
    return lines


def _wait_async(op):
    """等待 WinRT 异步操作完成，兼容 winrt/winsdk 新旧版本。

    - 旧版 winsdk/winrt: op.get()
    - winsdk 1.x 部分操作: op.get_results() 可用
    - winsdk 1.x 部分操作（如 BitmapDecoder.create_async）必须真正 await
    """
    if hasattr(op, 'get'):
        return op.get()
    try:
        return op.get_results()
    except Exception:
        pass
    # winsdk 1.x：必须在事件循环中 await（新线程避免阻塞调用线程）
    import asyncio
    import threading

    box = {}

    async def _await_op(o):
        return await o

    def _run():
        box['v'] = asyncio.run(_await_op(op))

    t = threading.Thread(target=_run)
    t.start()
    t.join()
    return box['v']


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


def _ocr_screen_win(region=None):
    """Windows OCR 全屏/区域识别，返回 [{text, cx, cy}]（屏幕坐标）。3 秒缓存。"""
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

        decoder = _wait_async(BD.create_async(stream))
        bitmap = _wait_async(decoder.get_software_bitmap_async())
        result = _wait_async(engine.recognize_async(bitmap))

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


# ── OCR 相似字容错：编辑距离 ≤1 + 同音/形近字归一化 ──
_OCR_CONFUSABLES = {
    # 形近字（OCR 常见混淆，键=易错字，值=规范字）
    '圪': '坛', '圢': '坛', '坥': '坛',
    '汊': '汉', '汗': '汉',
    '千': '干', '于': '干',
    '太': '大', '犬': '大',
    '入': '人', '八': '人',
    '己': '已', '巳': '已',
    '未': '末', '末': '未',
    '晴': '睛', '睛': '晴',
    '没': '设', '投': '设',
    '乌': '鸟', '免': '兔',
    '日': '曰', '目': '日',
    '王': '玉', '主': '王',
    '天': '夫', '夭': '天',
    '午': '牛', '土': '士', '士': '土',
    # 同音字（高频）
    '谈': '坛', '谭': '坛', '弹': '坛', '潭': '坛',  # tán
    '设': '社',  # shè
    '驱': '区',  # qū
    '尤': '游',  # yóu
}


def _norm_ocr_text(s):
    """把 OCR 易错字归一化为规范字，提升模糊匹配命中率。"""
    return ''.join(_OCR_CONFUSABLES.get(ch, ch) for ch in s)


def _edit_distance(a, b):
    """Levenshtein 编辑距离（DP，O(mn)）。"""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if la > lb:
        a, b = b, a
        la, lb = lb, la
    if lb - la > 4:
        return 99
    prev = list(range(la + 1))
    for j in range(1, lb + 1):
        cur = [j] + [0] * la
        cb = b[j - 1]
        for i in range(1, la + 1):
            cur[i] = min(prev[i] + 1, cur[i - 1] + 1, prev[i - 1] + (a[i - 1] != cb))
        prev = cur
    return prev[la]


def _fuzzy_contains(k, t, max_dist=1):
    """t 是否包含与 k 编辑距离 ≤ max_dist 的子串（仅 len(k)>=3 时启用，防短词误报）。"""
    if len(k) < 3:
        return False
    if abs(len(t) - len(k)) <= max_dist and _edit_distance(k, t) <= max_dist:
        return True
    lk = len(k)
    for i in range(len(t) - (lk - 1) + 1):
        for wlen in (lk - 1, lk, lk + 1):
            if wlen <= 0 or i + wlen > len(t):
                continue
            sub = t[i:i + wlen]
            if _edit_distance(k, sub) <= max_dist:
                return True
    return False


def _find_text(keywords, exclude=None, region=None, lines=None, fuzzy=True):
    """在 OCR 结果中找关键词，返回 (cx, cy, 命中文本) 或 None。
    - fuzzy=True（默认）：OCR 相似字容错 —— 精确子串优先；未命中时启用
      编辑距离 ≤1 容错（关键词 ≥3 字）与同音/形近字归一化匹配，
      解决「坛→圪」「你好→钧好」等 OCR 识别偏差导致的误拦截/误报。"""
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
            matched = (k in t or t in k)
            if not matched and fuzzy and len(k) >= 3:
                matched = (_fuzzy_contains(k, t)
                           or _fuzzy_contains(_norm_ocr_text(k), _norm_ocr_text(t)))
            if not matched:
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
                   f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Clipboard]::SetText('{esc}')"]
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


def _get_window_rect(hwnd):
    """获取窗口矩形 (left, top, width, height)"""
    user32 = ctypes.windll.user32
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right - r.left, r.bottom - r.top)


def _foreground_window():
    """获取前台窗口 (hwnd, title, rect) 或 (None, '', None)"""
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None, '', None
    length = user32.GetWindowTextLengthW(hwnd)
    title = ''
    if length > 0:
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
    return hwnd, title, _get_window_rect(hwnd)


def cmd_snapshot(top=12, ocr_top=25, region=None):
    """结构化桌面快照：前台窗口 + 窗口列表(标题/位置/大小/前台标记) + 前台窗口区域 OCR 摘要。

    为什么快：① 窗口元信息毫秒级（不截图）② OCR 只跑前台窗口区域（比全屏快 5~10 倍）
    ③ 输出精简 JSON，AI 一眼看懂，token 消耗小。
    """
    import json
    fg_hwnd, fg_title, fg_rect = _foreground_window()
    items = []
    for hwnd, title in _list_windows():
        try:
            x, y, w, h = _get_window_rect(hwnd)
        except Exception:
            continue
        if w < 80 or h < 80:  # 过滤托盘/极小窗口
            continue
        items.append({
            'title': title[:60],
            'x': x, 'y': y, 'w': w, 'h': h,
            'foreground': (hwnd == fg_hwnd),
        })
    items.sort(key=lambda it: (not it['foreground'], -it['w'] * it['h']))
    out = {
        'foreground': fg_title or '(无前台窗口)',
        'fg_rect': fg_rect,
        'windows': items[:top],
    }
    # 只 OCR 前台窗口区域（裁掉标题栏 ~40px，减小范围加速）
    ocr_region = region
    if ocr_region is None and fg_rect and fg_rect[2] > 100 and fg_rect[3] > 100:
        x, y, w, h = fg_rect
        ocr_region = f'{x},{y + 40},{w},{max(100, h - 40)}'
    if ocr_region:
        lines = _ocr_screen(ocr_region)
        out['fg_text'] = [
            {'text': ln['text'], 'cx': int(ln['cx']), 'cy': int(ln['cy'])}
            for ln in lines[:ocr_top]
        ]
    else:
        out['fg_text'] = []
    return json.dumps(out, ensure_ascii=False, indent=1)


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
    elif os.path.dirname(save) == '':
        # 纯文件名（未带目录）时自动归档到 data/screenshots，防止污染根目录
        save = os.path.join(SHOTS, save)
    img.save(save)
    return True, save


# ---------------------------------------------------------------
# 视觉理解（desktop_see）：本地画面分析 + 可选多模态大模型
# ---------------------------------------------------------------
_VISION_ENV_KEYS = [('VISION_API_KEY', 'api_key'), ('VISION_BASE_URL', 'base_url'), ('VISION_MODEL', 'model')]


def _load_env_file():
    """解析项目根目录 .env（desktop_do.py 独立运行时也可靠）。"""
    env = {}
    try:
        p = os.path.join(ROOT, '.env')
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    k, v = line.split('=', 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return env


def _expand_env_ref(val):
    """展开 ${XXX} 引用：从 os.environ 或 .env 文件取值；无引用则原样返回。"""
    if not val:
        return val
    import re
    m = re.fullmatch(r'\$\{(\w+)\}', str(val).strip())
    if not m:
        return val
    name = m.group(1)
    v = os.environ.get(name)
    if not v:
        v = _load_env_file().get(name)
    return v or val


def _vision_config():
    """读取视觉模型配置：优先环境变量/.env，回退 config.yaml 的 ai.vision 段，并展开 ${XXX} 引用。"""
    cfg = {}
    envfile = _load_env_file()
    for env, key in _VISION_ENV_KEYS:
        v = os.environ.get(env) or envfile.get(env)
        if v:
            cfg[key] = v
    # 从 config.yaml 补齐缺失项（含 ${XXX} 引用展开）
    try:
        import yaml
        yp = os.path.join(ROOT, 'config', 'config.yaml')
        if os.path.exists(yp):
            with open(yp, encoding='utf-8') as f:
                d = yaml.safe_load(f) or {}
            v = (d.get('ai') or {}).get('vision') or {}
            for k in ('api_key', 'base_url', 'model'):
                if k not in cfg and v.get(k):
                    cfg[k] = _expand_env_ref(v[k])
    except Exception:
        pass
    # 最终保险：api_key 若仍是 ${XXX} 占位符，尝试展开
    if cfg.get('api_key'):
        cfg['api_key'] = _expand_env_ref(cfg['api_key'])
    return cfg


def _local_vision_summary(region=None, img=None):
    """本地画面分析：主色调 / 红绿告警块 / 亮度。不依赖外部 API，毫秒级。
    img 可传入已截取图像（避免重复截图），未传时自行截屏。"""
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        return '（缺 mss/PIL/numpy，无法本地分析）'
    try:
        if img is None:
            import mss
            with mss.mss() as sct:
                if region:
                    x, y, w, h = [int(v) for v in region.split(',')]
                    shot = sct.grab({'left': x, 'top': y, 'width': w, 'height': h})
                else:
                    shot = sct.grab(sct.monitors[0])
            img = Image.frombytes('RGB', shot.size, shot.rgb)
        small = img.resize((128, 72), Image.BILINEAR)
        arr = np.array(small).astype(np.float32)
        hsv = np.array(Image.fromarray(arr.astype(np.uint8)).convert('HSV'))
        h_, s_, v_ = hsv[..., 0].astype(np.float32), hsv[..., 1].astype(np.float32), hsv[..., 2].astype(np.float32)
        # 主色调（量化统计）
        q = small.quantize(colors=6)
        pal = q.getpalette() or []
        counts = sorted(q.getcolors(), reverse=True)[:4]
        colors = []
        for cnt, idx in counts:
            rgb = pal[idx * 3: idx * 3 + 3]
            colors.append(f'#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}({cnt * 100 // (128 * 72)}%)')
        # 红/绿告警块（HSV 色域）
        red_mask = ((h_ > 235) | (h_ < 12)) & (s_ > 100) & (v_ > 90)
        green_mask = (h_ > 55) & (h_ < 100) & (s_ > 90) & (v_ > 90)
        red_ratio = float(red_mask.mean())
        green_ratio = float(green_mask.mean())
        bright = float(v_.mean())
        out = [f'分辨率: {img.width}x{img.height}',
               f'主色调: ' + ', '.join(colors),
               f'亮度: {bright:.0f}/255（{"明亮" if bright > 140 else "中等" if bright > 70 else "偏暗"}）',
               f'红色块占比: {red_ratio * 100:.1f}%（疑似警告/错误/红色按钮）',
               f'绿色块占比: {green_ratio * 100:.1f}%（疑似成功/可用状态）']
        return '\n'.join(out)
    except Exception as e:
        return f'（本地分析出错: {e}）'


def _call_vision_api(prompt, img_path, cfg):
    """调用 OpenAI 兼容视觉模型接口（如 GLM-4V / Qwen-VL / GPT-4o），返回文本。"""
    import base64
    import requests
    base = (cfg.get('base_url') or 'https://api.deepseek.com/v1').rstrip('/')
    url = base + '/chat/completions'
    with open(img_path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    body = {
        'model': cfg.get('model') or 'glm-4.6V',
        'messages': [{'role': 'user', 'content': [
            {'type': 'text', 'text': prompt},
            {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64}'}},
        ]}],
        'temperature': 0.2,
        'max_tokens': 1024,  # 视觉输出上限（GLM-4.6V API 限制 [1,1024]）
        # 关闭思考模式：加快响应、省 token（仅对支持思考的模型生效，旧模型自动忽略）
        'thinking': {'type': 'disabled'},
    }
    import time as _time
    last_err = None
    for attempt in range(2):  # 失败重试一次（偶发 RemoteDisconnected/网络抖动）
        try:
            r = requests.post(url, json=body,
                              headers={'Authorization': f"Bearer {cfg.get('api_key')}"},
                              timeout=60)
            r.raise_for_status()
            data = r.json()
            return data['choices'][0]['message']['content']
        except Exception as e:
            last_err = e
            if attempt == 0:
                _time.sleep(1.2)
    raise last_err


def _grab_screen(region=None):
    """mss 单次截图，返回 (PIL.Image, 屏幕rect)。region: 'x,y,w,h'；全屏时 rect=(0,0,宽,高)。"""
    import mss
    from PIL import Image
    with mss.mss() as sct:
        if region:
            x, y, w, h = [int(v) for v in region.split(',')]
            shot = sct.grab({'left': x, 'top': y, 'width': w, 'height': h})
            rect = (x, y, w, h)
        else:
            shot = sct.grab(sct.monitors[0])
            rect = (0, 0, shot.width, shot.height)
    img = Image.frombytes('RGB', shot.size, shot.rgb)
    return img, rect


def _parse_vlm_json(resp):
    """容错解析视觉模型返回：剥离```json围栏/前后说明，json.loads 失败则正则提取关键字段。"""
    import json
    import re
    if not resp:
        return None
    text = resp.strip()
    m = re.search(r'```(?:json)?\s*(.*?)```', text, re.S)
    if m:
        text = m.group(1).strip()
    else:
        m = re.search(r'\{.*\}', text, re.S)
        if m:
            text = m.group(0)
    try:
        return json.loads(text)
    except Exception:
        pass
    out = {}
    m = re.search(r'"summary"\s*:\s*"([^"]*)"', text)
    if m:
        out['summary'] = m.group(1)
    els = re.findall(r'"text"\s*:\s*"([^"]*)"\s*,\s*"pos"\s*:\s*"([^"]*)"', text)
    if els:
        out['elements'] = [{'text': t, 'pos': p} for t, p in els]
    warn = re.search(r'"warnings"\s*:\s*\[(.*?)\]', text, re.S)
    if warn:
        out['warnings'] = re.findall(r'"([^"]+)"', warn.group(1))
    act = re.search(r'"actions"\s*:\s*\[(.*?)\]', text, re.S)
    if act:
        out['actions'] = re.findall(r'"([^"]+)"', act.group(1))
    return out or None


def cmd_see(region=None, save=None, engine='smart', vlm=True):
    """看懂屏幕（快+准）：一次截图 → 本地分析(毫秒级) + OCR +（已配置时）多模态模型理解。

    engine: smart=自适应（默认，干净界面秒出，乱码界面自动融合 RapidOCR）；auto=Windows OCR 优先、空则 RapidOCR 兜底（最快）；
            fusion=双引擎强制融合（最准但慢）；win=仅 Windows OCR；rapid=仅 RapidOCR。
    VLM 返回的元素坐标已换算为屏幕像素，可直接用于点击。
    """
    import time as _t
    from PIL import Image
    # 🔧 快看模式修复：vlm=False 时强制 auto 引擎，跳过 smart 融合（避免乱码界面触发 RapidOCR 25s+）
    if not vlm and engine == 'smart':
        engine = 'auto'
    t0 = _t.time()
    try:
        img, rect = _grab_screen(region)
    except Exception as e:
        return f'❌ 截图失败: {e}'
    ox, oy, sw, sh = rect
    if not save:
        save = os.path.join(SHOTS, f'desktop_{time.strftime("%Y%m%d_%H%M%S")}.png')
    elif os.path.dirname(save) == '':
        save = os.path.join(SHOTS, save)
    try:
        img.save(save)
    except Exception as e:
        return f'❌ 截图保存失败: {e}'
    out = []
    out.append('【画面信息】')
    out.append(f'截图: {save}')
    out.append(f'区域: {ox},{oy},{sw},{sh}')
    out.append(_local_vision_summary(region, img))
    lines = _ocr_screen(region, engine=engine)
    if not lines and not vlm:
        # 🔧 纯本地快看：Windows OCR 全空时用半分辨率 RapidOCR 兜底（避免全分辨率 35s+）
        lines = _ocr_screen_rapid(region, scale=0.5)
    # vlm=True 且 OCR 空：不跑 RapidOCR 兜底，语义理解交给视觉大模型（快）
    if lines:
        out.append(f'【识别文字】{len(lines)} 行:')
        for ln in lines[:80]:
            out.append(f'  ({int(ln["cx"])},{int(ln["cy"])}) {ln["text"]}')
    else:
        out.append('【识别文字】未识别到文字')
    cfg = _vision_config()
    if vlm and cfg.get('api_key'):
        out.append('【视觉理解】')
        prompt = ('你是桌面自动化视觉助手。请仔细看这张屏幕截图，用中文JSON回答：'
                  '{"summary":"一句话描述当前画面",'
                  '"elements":[{"type":"按钮/输入框/弹窗/图标/文字/其他","text":"可见文字","pos":"x,y","state":"可用/禁用/高亮/普通"}],'
                  '"warnings":["发现的异常或需要注意的地方"],'
                  '"actions":["建议下一步操作"]}。'
                  '注意：图片宽高为 {W}x{H}，元素位置请输出 0~1 归一化坐标（x=像素x/宽，y=像素y/高），'
                  '最多列 8 个关键元素。只输出JSON，不要任何解释。')
        try:
            cimg = img
            if cimg.width > 1280:
                cimg = cimg.resize((1280, max(1, int(cimg.height * 1280 / cimg.width))), Image.BILINEAR)
            cpath = os.path.join(SHOTS, 'vision_tmp.jpg')
            cimg.convert('RGB').save(cpath, 'JPEG', quality=85)
            # 用 replace 而非 format：prompt 内含 JSON 花括号，format 会误解析报 KeyError
            resp = _call_vision_api(
                prompt.replace('{W}', str(cimg.width)).replace('{H}', str(cimg.height)),
                cpath, cfg)
            parsed = _parse_vlm_json(resp)
            if parsed:
                for el in parsed.get('elements') or []:
                    p = el.get('pos', '')
                    if ',' in p:
                        try:
                            px, py = [float(v) for v in p.split(',')[:2]]
                            el['pos'] = f'{int(ox + px * sw)},{int(oy + py * sh)}'
                        except Exception:
                            pass
                out.append('[结构化]')
                out.append(f"  画面: {parsed.get('summary', '')}")
                for el in (parsed.get('elements') or [])[:10]:
                    out.append(f"  - {el.get('type', '?')}「{el.get('text', '')}」 pos=({el.get('pos', '?')}) {el.get('state', '')}")
                if parsed.get('warnings'):
                    out.append(f"  ⚠️ 注意: {'; '.join(parsed['warnings'])}")
                if parsed.get('actions'):
                    out.append(f"  ➡️ 建议: {'; '.join(parsed['actions'])}")
            else:
                out.append(resp)
        except Exception as e:
            out.append(f'（视觉模型调用失败: {e}）')
    elif vlm:
        out.append('【视觉理解】未配置视觉模型 → 仅本地分析+OCR。')
        out.append('  启用方法：在 .env 设置 VISION_API_KEY / VISION_BASE_URL / VISION_MODEL')
        out.append('  （如智谱 GLM-4V-Flash: base=https://open.bigmodel.cn/api/paas/v4 model=glm-4v-flash）')
    out.append(f'⏱️ 耗时: {_t.time() - t0:.1f}s')
    return '\n'.join(out)


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
    try:
        __import__('rapidocr_onnxruntime')
        out.append('  ✅ RapidOCR 离线引擎（中文识别增强，双引擎兜底）')
    except ImportError:
        out.append('  ⚠️ rapidocr_onnxruntime（未安装，中文增强不可用；pip install rapidocr_onnxruntime）')
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


def cmd_ocr(region, engine='auto'):
    lines = _ocr_screen(region, engine=engine)
    if not lines:
        return '（屏幕上未识别到文字）'
    out = [f'识别到 {len(lines)} 行文字:']
    for ln in lines[:60]:
        out.append(f'  ({int(ln["cx"])},{int(ln["cy"])}) {ln["text"]}')
    return '\n'.join(out)


def cmd_click_text(text, exclude, region, double, window=None):
    keywords = [k.strip() for k in text.split('|') if k.strip()]
    exs = [k.strip() for k in exclude.split('|') if k.strip()] if exclude else None
    # 🔒 点击前快照确认：验证前台窗口正是期望的窗口，防止点错对象
    if window:
        fg_hwnd, fg_title, _ = _foreground_window()
        if not fg_title or window.lower() not in fg_title.lower():
            return (f'❌ 点击前验证失败：期望在「{window}」窗口操作，'
                    f'但当前前台窗口是「{fg_title or "无"}」。已取消点击（防误点）。')
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


def cmd_uia(title=None, depth=4, top=80):
    """UI Automation 控件树：直接读原生控件（按钮/编辑框/文本），比 OCR 快 10 倍且零乱码。

    优先 pywinauto(UIA backend)，失败回退 uiautomation 库。输出 JSON：控件类型/名称/坐标。
    """
    # ---- 当前环境缺 UIA 库时，自动用系统 Python 重新执行（7Tan 内置 Python 无 uiautomation） ----
    import importlib.util
    if importlib.util.find_spec('uiautomation') is None and importlib.util.find_spec('pywinauto') is None:
        import shutil
        candidates = [
            r'C:\Program Files\Python312\python.exe',
            r'C:\Python312\python.exe',
        ]
        for cand in candidates:
            if os.path.exists(cand):
                try:
                    r = subprocess.run(
                        [cand, os.path.abspath(__file__), 'uia',
                         '--title', title or '', '--depth', str(depth), '--top', str(top)],
                        capture_output=True, text=True, encoding='utf-8', errors='replace',
                        timeout=60, creationflags=CREATE_NO_WINDOW)
                    out = r.stdout or ''
                    if r.returncode != 0 and r.stderr:
                        out += '\n[stderr] ' + r.stderr[-500:]
                    return out.strip() or f'（系统 Python 执行无输出，exit={r.returncode}）'
                except Exception as e:
                    return f'❌ 系统 Python 执行失败: {e}'
    import json
    hwnd = None
    if title:
        wins = _list_windows(title)
        if not wins:
            return json.dumps({'error': f'未找到标题含「{title}」的窗口'}, ensure_ascii=False)
        hwnd = wins[0][0]
    # ---- 优先 pywinauto UIA backend ----
    try:
        from pywinauto import Desktop
        from pywinauto.controls.uiawrapper import UIAWrapper
        if hwnd is None:
            app = Desktop(backend='uia')
            win = app.window(handle=app.active())
        else:
            app = Desktop(backend='uia')
            win = app.window(handle=hwnd)
        controls = []

        def walk(el, d):
            if len(controls) >= top or d > depth:
                return
            try:
                ctype = el.element_info.control_type or ''
            except Exception:
                ctype = ''
            if ctype and ctype not in ('Window', 'Pane'):
                name = ''
                try:
                    name = el.window_text() or ''
                except Exception:
                    pass
                try:
                    r = el.rectangle()
                    rect = [int(r.left), int(r.top), int(r.width()), int(r.height())]
                except Exception:
                    rect = None
                if name or ctype in ('Button', 'Edit', 'CheckBox', 'ComboBox', 'TabItem', 'ListItem'):
                    controls.append({'type': ctype, 'name': (name or '')[:40], 'rect': rect})
            try:
                children = el.children()
            except Exception:
                children = []
            for ch in children[:50]:
                walk(ch, d + 1)

        walk(win, 0)
        if controls:
            return json.dumps({'backend': 'pywinauto', 'count': len(controls),
                               'controls': controls[:top]}, ensure_ascii=False, indent=1)
    except Exception as e:
        pass  # 回退到 uiautomation 库
    # ---- 回退：uiautomation 库（更稳定，支持微信） ----
    try:
        import uiautomation as auto
        root = auto.ControlFromHandle(hwnd) if hwnd else auto.GetForegroundControl()
        if root is None:
            return json.dumps({'error': '无法获取目标控件（前台无窗口或无 UIA 支持）'}, ensure_ascii=False)
        controls = []

        def walk2(el, d):
            if len(controls) >= top or d > depth:
                return
            try:
                ctype = el.ControlTypeName or ''
            except Exception:
                ctype = ''
            if ctype and ctype not in ('WindowControl', 'PaneControl', 'CustomControl'):
                name = ''
                try:
                    name = el.Name or ''
                except Exception:
                    pass
                try:
                    r = el.BoundingRectangle
                    rect = [int(r.left), int(r.top), int(r.width()), int(r.height())]
                except Exception:
                    rect = None
                if name or 'Button' in ctype or 'Edit' in ctype or 'List' in ctype or 'Tab' in ctype:
                    controls.append({'type': ctype.replace('Control', ''), 'name': (name or '')[:40], 'rect': rect})
            try:
                children = el.GetChildren()
            except Exception:
                children = []
            for ch in children[:50]:
                walk2(ch, d + 1)

        walk2(root, 0)
        return json.dumps({'backend': 'uiautomation', 'count': len(controls),
                           'controls': controls[:top]}, ensure_ascii=False, indent=1)
    except ImportError as e:
        return json.dumps({'error': f'缺少 UIA 库（pywinauto/uiautomation）: {e}'}, ensure_ascii=False)


def cmd_tmatch(template, region=None, threshold=0.8, max_matches=5, save=None):
    """模板匹配：用图像模板（如发送/保存按钮图标）在屏幕中定位，比 OCR 更稳。

    cv2.matchTemplate(TM_CCOEFF_NORMED) + 非极大值抑制。
    返回所有匹配点（屏幕坐标）。阈值 0~1，默认 0.8。
    """
    import json
    if not os.path.exists(template):
        return json.dumps({'error': f'模板文件不存在: {template}'}, ensure_ascii=False)
    try:
        import mss
        import numpy as np
        import cv2
    except ImportError as e:
        return json.dumps({'error': f'缺少依赖(mss/numpy/cv2): {e}'}, ensure_ascii=False)
    try:
        with mss.mss() as sct:
            if region:
                x, y, w, h = [int(v) for v in region.split(',')]
                shot = sct.grab({'left': x, 'top': y, 'width': w, 'height': h})
                ox, oy = x, y
            else:
                shot = sct.grab(sct.monitors[0])
                ox, oy = 0, 0
        screen = np.array(shot)[:, :, :3]  # BGRA -> BGR
        tpl = cv2.imread(template)
        if tpl is None:
            return json.dumps({'error': f'无法读取模板图片（可能不是有效图片）: {template}'}, ensure_ascii=False)
        th, tw = tpl.shape[:2]
        if screen.shape[0] < th or screen.shape[1] < tw:
            return json.dumps({'error': '屏幕比模板还小，无法匹配'}, ensure_ascii=False)
        res = cv2.matchTemplate(screen, tpl, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= threshold)
        pts = list(zip(loc[1], loc[0]))
        # 非极大值抑制（按分数排序，贪心去重重叠框）
        scored = sorted(pts, key=lambda p: res[p[1], p[0]], reverse=True)
        picks = []
        for px, py in scored:
            if all(abs(px - qx) > tw // 2 and abs(py - qy) > th // 2 for qx, qy in picks):
                picks.append((px, py))
                if len(picks) >= max_matches:
                    break
        matches = [{
            'cx': int(px + tw / 2 + ox),
            'cy': int(py + th / 2 + oy),
            'x': int(px + ox), 'y': int(py + oy),
            'w': int(tw), 'h': int(th),
            'score': round(float(res[py, px]), 3),
        } for px, py in picks]
        if save and matches:
            if os.path.dirname(save) == '':
                save = os.path.join(SHOTS, save)
            vis = screen.copy()
            for m in matches:
                cv2.rectangle(vis, (m['x'] - ox, m['y'] - oy),
                              (m['x'] - ox + m['w'], m['y'] - oy + m['h']), (0, 0, 255), 2)
            cv2.imwrite(save, vis)
        return json.dumps({'count': len(matches), 'matches': matches,
                           'save': save or ''}, ensure_ascii=False, indent=1)
    except Exception as e:
        return json.dumps({'error': f'模板匹配失败: {e}'}, ensure_ascii=False)


def cmd_send_chat(window, search, message, hotkey, verify=True, require_window=True):
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
    time.sleep(0.8)
    # 4.5 🔒 防发错闸门：OCR 确认目标对象已出现在屏幕上（聊天标题/搜索候选），
    #     找不到 = 可能没进对聊天窗口，拒绝粘贴/发送！
    if require_window:
        probe = search.replace(' ', '').strip()
        hit = None
        if len(probe) >= 2:
            hit = _find_text([probe], region=None)
        if not hit:
            fg = _foreground_window()
            return (f'❌ 防发错闸门拦截：搜索「{search}」后未在屏幕确认到该名称，'
                    f'拒绝发送（当前前台窗口: {fg[1] or "未知"}）。'
                    f'可能原因：①搜索无结果/进了错误聊天 ②窗口遮挡。请人工确认后重试。')
        steps.append(f'✅ 已确认目标「{hit[2]}」在屏幕')
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
    o.add_argument('--engine', default='auto', choices=['smart', 'auto', 'fusion', 'win', 'rapid'])
    see = sub.add_parser('see')
    see.add_argument('--region', default='')
    see.add_argument('--save', default='')
    see.add_argument('--engine', default='smart', choices=['smart', 'auto', 'fusion', 'win', 'rapid'])
    see.add_argument('--no-vlm', action='store_true')
    c = sub.add_parser('click'); c.add_argument('--text', required=True)
    c.add_argument('--exclude', default=''); c.add_argument('--region', default='')
    c.add_argument('--double', action='store_true')
    c.add_argument('--window', default='', help='点击前验证前台窗口标题含此关键字，不符则拒绝点击')
    u = sub.add_parser('uia')
    u.add_argument('--title', default='', help='窗口标题关键字（留空=前台窗口）')
    u.add_argument('--depth', type=int, default=4)
    u.add_argument('--top', type=int, default=80)
    tm = sub.add_parser('tmatch')
    tm.add_argument('--template', required=True, help='模板图片路径（如发送按钮图标）')
    tm.add_argument('--region', default='')
    tm.add_argument('--threshold', type=float, default=0.8)
    tm.add_argument('--max-matches', type=int, default=5)
    tm.add_argument('--save', default='', help='标注结果保存路径')
    cp = sub.add_parser('click-pos'); cp.add_argument('--pos', required=True)
    cp.add_argument('--double', action='store_true')
    t = sub.add_parser('type'); t.add_argument('--text', required=True); t.add_argument('--pos', default='')
    pi = sub.add_parser('paste-img'); pi.add_argument('--path', required=True); pi.add_argument('--pos', default='')
    h = sub.add_parser('hotkey'); h.add_argument('--keys', required=True)
    v = sub.add_parser('verify'); v.add_argument('--text', required=True); v.add_argument('--region', default='')
    sn = sub.add_parser('snapshot')
    sn.add_argument('--top', type=int, default=12)
    sn.add_argument('--ocr-top', type=int, default=25)
    sn.add_argument('--region', default='')

    sc = sub.add_parser('send-chat')
    sc.add_argument('--window', required=True)
    sc.add_argument('--search', required=True)
    sc.add_argument('--message', required=True)
    sc.add_argument('--hotkey', default='ctrl,f')
    sc.add_argument('--no-verify', action='store_true')
    sc.add_argument('--no-window-check', action='store_true', help='关闭防发错闸门（不推荐）')

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
            print(cmd_ocr(args.region or None, engine=args.engine))
        elif cmd == 'see':
            print(cmd_see(args.region or None, args.save or None, engine=args.engine, vlm=not args.no_vlm))
        elif cmd == 'click':
            print(cmd_click_text(args.text, args.exclude, args.region or None,
                                 args.double, args.window or None))
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
        elif cmd == 'snapshot':
            print(cmd_snapshot(args.top, args.ocr_top, args.region or None))
        elif cmd == 'uia':
            print(cmd_uia(args.title or None, args.depth, args.top))
        elif cmd == 'tmatch':
            print(cmd_tmatch(args.template, args.region or None,
                             args.threshold, args.max_matches, args.save or None))
        elif cmd == 'send-chat':
            print(cmd_send_chat(args.window, args.search, args.message,
                                args.hotkey, verify=not args.no_verify,
                                require_window=not args.no_window_check))
        else:
            p.print_help()
    except KeyboardInterrupt:
        print('\n⏹ 已中断')
    except Exception as e:
        print(f'❌ 执行出错: {e}')


if __name__ == '__main__':
    main()
