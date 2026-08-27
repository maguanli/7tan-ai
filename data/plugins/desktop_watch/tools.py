# -*- coding: utf-8 -*-
"""
desktop_watch 插件 —— P1 桌面连续监控 + P3 观察流水落盘检索

工具：
1. desktop_watch        帧差监控：按间隔截屏比对，画面变化时存截图+写观察流水(SQLite)，
                        可选关键词触发检测（变化帧跑OCR匹配关键词，命中标记 keyword 事件）
2. desktop_watch_log    查询观察流水（最近N条 / 按关键词 / 按事件类型过滤）
3. desktop_watch_status 流水库状态统计（总数/各类型/时间范围/库大小）

设计说明：
- 帧差用 320px 宽灰度缩略图算像素差异比例（毫秒级、省CPU），阈值默认 0.05
- 关键词检测复用桌面机器人 CLI（tools/desktop_bot/desktop_do.py ocr --engine auto）
- 所有观察写入 data/desktop_watch.db，截图存 data/watch_shots/
"""
import os
import sys
import time
import sqlite3
import subprocess

from src.tools.registry import register_tool

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
# 项目根：data/plugins/desktop_watch/tools.py -> 上三级
ROOT = os.path.abspath(os.path.join(PLUGIN_DIR, '..', '..', '..'))
DATA_DIR = os.path.join(ROOT, 'data')
WATCH_DIR = os.path.join(DATA_DIR, 'watch_shots')
DB_PATH = os.path.join(DATA_DIR, 'desktop_watch.db')

CREATE_NO_WINDOW = 0x08000000


def _ensure_db():
    os.makedirs(WATCH_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS observations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        event_type TEXT NOT NULL,
        diff_ratio REAL DEFAULT 0,
        keywords_hit TEXT DEFAULT '',
        shot_path TEXT DEFAULT '',
        ocr_digest TEXT DEFAULT ''
    )''')
    conn.commit()
    return conn


def _grab_frames():
    """截屏 -> 返回 (灰度小图用于帧差, 全彩原图用于存档)"""
    import mss
    from PIL import Image
    with mss.mss() as sct:
        shot = sct.grab(sct.monitors[0])
    img = Image.frombytes('RGB', shot.size, shot.rgb)
    small = img.convert('L').resize((320, max(1, int(320 * img.height / img.width))))
    return small, img


def _diff_ratio(a, b):
    """两帧差异比例 0~1（灰度差超过24视为变化像素）"""
    try:
        import numpy as np
    except ImportError:
        return 0.0
    if a is None or b is None or a.size != b.size:
        return 1.0
    aa = np.array(a, dtype=np.int16)
    bb = np.array(b, dtype=np.int16)
    return float((np.abs(aa - bb) > 24).mean())


def _quick_ocr_text():
    """轻量OCR：子进程调桌面机器人CLI，返回纯文本（失败返回空串，不阻塞监控主循环）"""
    cli = os.path.join(ROOT, 'tools', 'desktop_bot', 'desktop_do.py')
    if not os.path.exists(cli):
        return ''
    try:
        r = subprocess.run([sys.executable, cli, 'ocr', '--engine', 'auto'],
                           capture_output=True, text=True, timeout=90,
                           encoding='utf-8', errors='replace',
                           creationflags=CREATE_NO_WINDOW, cwd=ROOT)
        return (r.stdout or '').strip()
    except Exception:
        return ''


def _record(event_type, diff_ratio=0.0, keywords_hit='', shot_path='', ocr_digest=''):
    """写一条观察记录，返回记录ID"""
    conn = _ensure_db()
    cur = conn.execute(
        'INSERT INTO observations(ts,event_type,diff_ratio,keywords_hit,shot_path,ocr_digest)'
        ' VALUES(?,?,?,?,?,?)',
        (time.strftime('%Y-%m-%d %H:%M:%S'), event_type, round(diff_ratio, 4),
         keywords_hit, shot_path, (ocr_digest or '')[:800]))
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


@register_tool(
    name="desktop_watch",
    description="桌面连续监控哨兵：按间隔截屏做帧差检测，画面变化时自动存截图并写入观察流水；可选关键词触发（变化时跑OCR匹配关键词，命中记为keyword事件）。适合：等某个弹窗出现、盯进度条走完、监视界面异常。返回事件时间线。",
    parameters={
        "type": "object",
        "properties": {
            "seconds": {"type": "integer", "description": "监控总时长（秒），默认30，上限600"},
            "interval": {"type": "number", "description": "截屏间隔（秒），默认5"},
            "threshold": {"type": "number", "description": "变化触发阈值 0~1（画面差异比例），默认0.05"},
            "keywords": {"type": "string", "description": "关键词，| 分隔（如 更新失败|错误）。留空=只记变化不做关键词检测"},
            "use_vlm": {"type": "boolean", "description": "关键词命中时是否提示可用视觉模型深入理解（默认False）", "default": False},
        },
        "required": [],
    },
    category="desktop"
)
def desktop_watch(seconds: int = 30, interval: float = 5, threshold: float = 0.05,
                  keywords: str = "", use_vlm: bool = False) -> str:
    """帧差监控主循环"""
    kws = [k.strip() for k in (keywords or '').split('|') if k.strip()]
    end_t = time.time() + max(5, min(int(seconds), 600))   # 上限10分钟防失控
    interval = max(1.0, float(interval))
    prev = None
    events, kw_hits_total = [], []
    n_checks = 0
    while time.time() < end_t:
        try:
            small, full = _grab_frames()
        except Exception as e:
            events.append(f'[警告] 截屏失败: {e}')
            break
        n_checks += 1
        if prev is not None:
            d = _diff_ratio(prev, small)
            if d >= threshold:
                ts = time.strftime('%H:%M:%S')
                shot_path = os.path.join(WATCH_DIR, f'watch_{time.strftime("%Y%m%d_%H%M%S")}.png')
                try:
                    full.save(shot_path)
                except Exception:
                    shot_path = ''
                event_type, kw_hit, digest = 'change', '', ''
                if kws:
                    txt = _quick_ocr_text()
                    hits = [k for k in kws if k in txt]
                    kw_hit = '|'.join(hits)
                    digest = txt[:500].replace('\n', ' ')
                    if hits:
                        event_type = 'keyword'
                        kw_hits_total.extend(hits)
                _record(event_type, d, kw_hit, shot_path, digest)
                line = f'[{ts}] [触发-{event_type}] 变化率{d:.1%}'
                if kw_hit:
                    line += f' 命中关键词「{kw_hit}」'
                if shot_path:
                    line += f' 截图:{os.path.basename(shot_path)}'
                events.append(line)
                if use_vlm and event_type == 'keyword':
                    events.append('   （提示: 可用 desktop_see 对该截图做视觉理解）')
        prev = small
        if time.time() + interval <= end_t + 0.5:
            time.sleep(interval)
    out = [f'监控结束: 共检查{n_checks}帧, 触发{len(events)}次事件']
    if kws:
        out.append(f'关键词: {"|".join(kws)} -> 命中 {len(kw_hits_total)} 次')
    out.extend(events[:30] if events else ['（监控期间画面无明显变化）'])
    out.append('查历史: desktop_watch_log / 库状态: desktop_watch_status')
    return '\n'.join(out)


@register_tool(
    name="desktop_watch_log",
    description="查询桌面观察流水（SQLite）：最近N条观察记录，支持按关键词/事件类型(change/keyword/manual)过滤。用于回答\"刚才屏幕上出现过什么\"\"上次弹错误窗是什么时候\"。",
    parameters={
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "返回条数，默认20", "default": 20},
            "keyword": {"type": "string", "description": "按关键词过滤（匹配关键词命中列或OCR摘要）", "default": ""},
            "event_type": {"type": "string", "description": "按事件类型过滤: change/keyword/manual", "default": ""},
        },
        "required": [],
    },
    category="desktop"
)
def desktop_watch_log(limit: int = 20, keyword: str = "", event_type: str = "") -> str:
    """查询观察流水"""
    if not os.path.exists(DB_PATH):
        return '（观察流水库为空，先运行 desktop_watch）'
    conn = sqlite3.connect(DB_PATH)
    sql = 'SELECT id,ts,event_type,diff_ratio,keywords_hit,shot_path,ocr_digest FROM observations'
    args = []
    conds = []
    if event_type:
        conds.append('event_type=?')
        args.append(event_type)
    if keyword:
        conds.append('(keywords_hit LIKE ? OR ocr_digest LIKE ?)')
        args += [f'%{keyword}%', f'%{keyword}%']
    if conds:
        sql += ' WHERE ' + ' AND '.join(conds)
    sql += ' ORDER BY id DESC LIMIT ?'
    args.append(max(1, min(int(limit), 200)))
    rows = conn.execute(sql, args).fetchall()
    conn.close()
    if not rows:
        return '（无匹配的观察记录）'
    out = [f'观察流水 {len(rows)} 条:']
    for r in rows:
        rid, ts, et, dr, kh, sp, dg = r
        line = f'#{rid} [{ts}] {et}' + (f' 差异{dr:.1%}' if dr else '')
        if kh:
            line += f' 命中「{kh}」'
        if sp:
            line += f' 图:{os.path.basename(sp)}'
        out.append(line)
        if dg and keyword:
            out.append(f'   OCR片段: {dg[:120]}')
    return '\n'.join(out)


@register_tool(
    name="desktop_watch_status",
    description="查看桌面观察流水库状态：总条数、各事件类型计数、时间范围、数据库大小。",
    parameters={"type": "object", "properties": {}, "required": []},
    category="desktop"
)
def desktop_watch_status() -> str:
    """流水库状态统计"""
    if not os.path.exists(DB_PATH):
        return f'（库不存在: {DB_PATH}，先运行 desktop_watch）'
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute('SELECT COUNT(*) FROM observations').fetchone()[0]
    by_type = conn.execute('SELECT event_type, COUNT(*) FROM observations GROUP BY event_type').fetchall()
    span = conn.execute('SELECT MIN(ts), MAX(ts) FROM observations').fetchone()
    conn.close()
    size_kb = os.path.getsize(DB_PATH) / 1024
    out = [f'观察流水库: {total} 条 | {size_kb:.1f} KB',
           f'时间范围: {span[0] or "-"} ~ {span[1] or "-"}']
    for et, c in by_type:
        out.append(f'  {et}: {c} 条')
    return '\n'.join(out)
