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

# 各操作 OCR 关键词的排除词（防止点错：弹窗文案、提示语等）
EXCLUDES = {
    'publish': ['确定', '确认', '成功', '取消', '是否', '吗', '预览', '群发'],
    'confirm': ['是否', '成功', '完成', '取消'],
    'title':   ['副标题', '原标题', '标题党'],
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
            writer.store_async().get_results()
        stream.seek(0)

        decoder = BD.create_async(stream).get_results()
        bitmap = decoder.get_software_bitmap_async().get_results()
        result = engine.recognize_async(bitmap).get_results()

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


# ── OCR 相似字容错（与 desktop_do.py 同套）：编辑距离 ≤1 + 同音/形近字归一化 ──
_OCR_CONFUSABLES = {
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
    '谈': '坛', '谭': '坛', '弹': '坛', '潭': '坛',
    '设': '社',
    '驱': '区',
    '尤': '游',
}


def _norm_ocr_text(s):
    return ''.join(_OCR_CONFUSABLES.get(ch, ch) for ch in s)


def _edit_distance(a, b):
    """Levenshtein 编辑距离（DP）。"""
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
    """t 是否包含与 k 编辑距离 ≤ max_dist 的子串（仅 len(k)>=3 启用）。"""
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


def _find_text(keywords, lines=None, exclude=None, region=None, fuzzy=True):
    """在 OCR 结果中找关键词，返回 (cx, cy, 命中文本) 或 None。
    - exclude: 排除词列表，命中文本含任一排除词则跳过（防误点弹窗文案）
    - region: (x1,y1,x2,y2) 屏幕坐标区域限制，只在该区域内找
    - fuzzy: OCR 相似字容错（编辑距离≤1 + 同音/形近字归一化），默认开启
    匹配规则：关键词与识别文本互为子串（长度>=2）优先，未命中启用模糊容错。"""
    if lines is None:
        lines = _ocr_screen()
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
                x1, y1, x2, y2 = region
                if not (x1 <= ln['cx'] <= x2 and y1 <= ln['cy'] <= y2):
                    continue
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
        hit = _find_text(KEYWORDS.get(kw, []), exclude=EXCLUDES.get(kw))
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


def click_paste(pg, pc, pos, text, pause=0.35):
    """双击定位 + 剪贴板粘贴（兼容中文）。pause 缩短后每次粘贴省 ~0.5s。"""
    pg.click(pos[0], pos[1])
    time.sleep(pause)
    pg.click(pos[0], pos[1])
    time.sleep(pause * 0.5)
    pc.copy(text)
    time.sleep(0.25)
    pg.hotkey('ctrl', 'v')
    time.sleep(0.5)


def _screen_size():
    """当前屏幕尺寸 (w, h)，OCR 失败时兜底 1920x1080"""
    try:
        import mss
        with mss.mss() as sct:
            m = sct.monitors[0]
            return m['width'], m['height']
    except Exception:
        return 1920, 1080


def wait_for(keywords, timeout=8.0, appear=True, exclude=None, region=None, interval=0.6):
    """智能等待：轮询 OCR 直到关键词出现/消失，替代固定 sleep。
    页面好了立刻继续（省时间），超时返回 None。OCR 不可用时不阻塞。"""
    if _get_ocr_engine() is None:
        return None
    deadline = time.time() + timeout
    while time.time() < deadline:
        hit = _find_text(keywords, exclude=exclude, region=region)
        if appear and hit:
            return hit
        if not appear and not hit:
            return None
        time.sleep(interval)
    return None


def _check_page_ready():
    """发表前安全检查：确认标题/正文占位符已消失（内容已填），防止误发空文章。
    仅在 OCR 有明确证据表明内容缺失时阻止；OCR 不可用时放行。"""
    lines = _ocr_screen()
    if not lines:
        return True
    missing = []
    if _find_text(['请在这里输入标题'], lines):
        missing.append('标题')
    if _find_text(['从这里开始写正文'], lines):
        missing.append('正文')
    if missing:
        print('  🛑 发表前安全检查未通过：' + '、'.join(missing) + ' 仍为空！')
        print('  🛑 已阻止发表，请先补全内容再重试。')
        return False
    return True


def _img_to_clipboard(path):
    """图片直写剪贴板（win32 CF_DIB，省去 PowerShell 启动 2-3s），失败回退 PowerShell。"""
    try:
        import win32clipboard
        from PIL import Image
        import io as _io
        img = Image.open(path).convert('RGB')
        buf = _io.BytesIO()
        img.save(buf, 'BMP')
        data = buf.getvalue()[14:]          # 去掉 14 字节 BMP 文件头，留 BITMAPINFOHEADER+像素
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        finally:
            win32clipboard.CloseClipboard()
        return True
    except Exception:
        try:
            cmd = ['powershell', '-NoProfile', '-Command',
                   f"Set-Clipboard -Path '{path}'"]
            subprocess.run(cmd, capture_output=True, timeout=30, shell=True)
            return True
        except Exception:
            return False


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
        # 验证：OCR 确认作者名出现在屏幕上（防"没填上"）
        if len(args.author) >= 2:
            hit = wait_for([args.author], timeout=4.0, appear=True)
            if hit:
                print(f'  ✓ 作者验证通过（OCR 识别到「{args.author}」）')
            else:
                print(f'  ⚠️ 作者验证未通过：OCR 未识别到「{args.author}」，请人工确认')
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
            if not _img_to_clipboard(path):
                print(f'  ⚠️ 图片放入剪贴板失败: {path}')
                continue
            time.sleep(0.5)
            pg.hotkey('ctrl', 'v')
            time.sleep(1.2)
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
    # 智能等待：等「保存成功」toast 出现（最多 6 秒），比固定 3 秒更快更稳
    hit = wait_for(['保存成功', '已保存'], timeout=6.0, appear=True)
    if hit:
        print(f'  ✅ 保存草稿成功（OCR 确认: {hit[2]}） @ {dp} [{src}]')
    else:
        time.sleep(1.5)
        print(f'  ⚠️ 已点击保存草稿 {dp} [{src}]（未识别到成功提示，请人工确认）')


def cmd_publish(args, pg, pc):
    # 0) 发表前安全检查：标题/正文必须已填，防止误发不完整文章
    if not _check_page_ready():
        return
    # 1) 优先 OCR 找「发表」按钮（排除弹窗文案误匹配）
    pub, psrc = None, 'default'
    if args.dynamic != 'off':
        hit = _find_text(KEYWORDS['publish'], exclude=EXCLUDES.get('publish'))
        if hit:
            pub = (int(hit[0]), int(hit[1]))
            psrc = f'ocr[{hit[2]}]'
    if pub is None:
        # OCR 未命中：回退「保存草稿右侧第3个按钮」经验位
        dp, _ = resolve(args, 'draft')
        pub = (dp[0] + 260, dp[1])
        psrc = 'default(+260)'
    pg.click(pub[0], pub[1])
    time.sleep(1.2)
    # 2) 弹窗出现后，在屏幕右下方区域找「确定/发表」确认按钮（避免点弹窗文案中心）
    sw, sh = _screen_size()
    confirm_found = _find_text(KEYWORDS['confirm'],
                               exclude=EXCLUDES.get('confirm'),
                               region=(int(sw * 0.4), int(sh * 0.3), sw, sh))
    if confirm_found:
        cp = (int(confirm_found[0]), int(confirm_found[1]))
        print(f'  ↪ 已点击发表按钮 {pub} [{psrc}]，弹窗确认 @ {cp} [ocr:{confirm_found[2]}]')
    else:
        cp, csrc = resolve(args, 'publish_confirm', kw='confirm')
        print(f'  ↪ 已点击发表按钮 {pub} [{psrc}]，未识别弹窗，用经验坐标 {cp} [{csrc}]')
    pg.click(cp[0], cp[1])
    # 3) 智能等待发表成功提示（最多 10 秒），确认真的发出去了
    done = wait_for(['发表成功', '群发成功', '已发表'], timeout=10.0, appear=True)
    if done:
        print(f'  ✅ 发表成功（OCR 确认: {done[2]}）')
    else:
        time.sleep(2.0)
        print('  ⚠️ 已点击发表确认，但未识别到成功提示，请人工确认后台状态')


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
