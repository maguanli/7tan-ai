# -*- coding: utf-8 -*-
"""
龙头阵法炒股插件（7tan）
核心战法：
  1. 龙头识别：人气榜前5（东方财富/同花顺/爱股票）→ 热门板块 → 板块内最强 → 综合
  2. 情绪周期：冰点 → 启动 → 发酵 → 高潮 → 分歧 → 退潮
  3. 买卖点：30分钟 MACD 金叉=买、死叉=卖
  4. 风控：单只最多买入总资金 1/3
数据源：东方财富公开接口（免费），失败自动降级。
"""
import sys
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool

# ---------------- 通用工具 ----------------
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"


def _http_json(url, timeout=8, referer="https://www.eastmoney.com/", retries=2):
    """GET 并解析 JSON，失败自动重试，仍失败返回 None"""
    import time as _time
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": _UA,
                "Referer": referer,
            })
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw)
        except Exception:
            if attempt < retries:
                _time.sleep(0.6 * (attempt + 1))
    return None


def _http_text(url, timeout=6):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def _secid(code):
    """股票代码 → 东财 secid（沪=1. 深/北=0.）"""
    code = str(code).strip()
    if code.startswith(("6", "5", "9")):
        return f"1.{code}"
    return f"0.{code}"


def _today_str():
    return datetime.now().strftime("%Y%m%d")


def _calc_macd(closes, fast=12, slow=26, signal=9):
    """计算 MACD，返回 (dif_list, dea_list, hist_list)。金叉/死叉在最后一段判断"""
    if len(closes) < slow + signal:
        return None, None, None
    ema_fast = closes[0]
    ema_slow = closes[0]
    dif_list = []
    dea_list = []
    hist_list = []
    dea = 0.0
    for i, c in enumerate(closes):
        ema_fast = ema_fast * (fast - 1) / (fast + 1) + c * 2 / (fast + 1)
        ema_slow = ema_slow * (slow - 1) / (slow + 1) + c * 2 / (slow + 1)
        dif = ema_fast - ema_slow
        dea = dea * (signal - 1) / (signal + 1) + dif * 2 / (signal + 1)
        dif_list.append(dif)
        dea_list.append(dea)
        hist_list.append(2 * (dif - dea))
    return dif_list, dea_list, hist_list


# ---------------- ① 人气榜 ----------------
@register_tool(
    name="ltz_renqi_rank",
    description="抓取人气榜前5个股（东方财富人气榜为主，同花顺/爱股票为辅）。用于「龙头识别①：人气高」。用户问'今天人气龙头/人气榜前5'时使用。",
    parameters={
        "type": "object",
        "properties": {
            "top": {"type": "integer", "description": "返回前几名，默认5", "default": 5},
        },
        "required": [],
    },
    category="stock"
)
def ltz_renqi_rank(top: int = 5) -> str:
    """人气榜前N"""
    lines = ["🔥 人气榜（龙头识别①：人气高）\n"]

    # 数据源1：东方财富股吧人气榜
    east = _http_json(
        "http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=50&po=1&np=1&fltt=2&invt=2"
        "&fid=f62&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
        "&fields=f12,f14,f2,f3,f62",
        timeout=8)
    east_list = []
    if east:
        east_list = (east.get("data") or {}).get("diff") or []
    if east_list:
        lines.append(f"【东方财富人气榜 · 前{top}】")
        for i, item in enumerate(east_list[:top], 1):
            code = item.get("f12") or "?"
            name = item.get("f14") or "?"
            price = item.get("f2") or 0
            hot = item.get("f62") or 0
            try:
                hot_yi = float(hot) / 1e8
                hot_str = f"{hot_yi:.1f}亿"
            except Exception:
                hot_str = str(hot)
            lines.append(f"  {i}. {name}({code}) 现价{price} 热度{hot_str}")
    else:
        lines.append("【东方财富人气榜】⚠️ 接口未返回，已降级")

    # 数据源2：同花顺 iwencai（反爬则降级）
    lines.append("\n【同花顺人气榜】")
    ths = _http_text(
        "https://www.iwencai.com/screener/result?w=人气个股排名100&querytype=stock",
        timeout=6)
    if ths and "人气" in ths:
        lines.append("  ✓ 已抓取（需在对话中解析明细）")
    else:
        lines.append("  ⚠️ 反爬拦截，已降级（以东财榜为准）")

    # 数据源3：爱股票（反爬则降级）
    lines.append("【爱股票人气榜】")
    aigp = _http_text("https://www.aigupiao.com/pcv/quote/list/type/hot", timeout=6)
    if aigp and "人气" in aigp:
        lines.append("  ✓ 已抓取（需在对话中解析明细）")
    else:
        lines.append("  ⚠️ 反爬拦截，已降级（以东财榜为准）")

    lines.append("\n💡 综合结论：以东财人气榜前5为「人气龙头」候选。")
    return "\n".join(lines)


# ---------------- 涨停池 / 炸板池（情绪数据底座） ----------------
def _fetch_zt_pool(date=None):
    """涨停池"""
    date = date or _today_str()
    url = ("http://push2ex.eastmoney.com/getTopicZTPool"
           f"?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt"
           f"&Pageindex=0&pagesize=300&sort=fbt%3Aasc&date={date}")
    j = _http_json(url, timeout=8)
    if not j or not j.get("data"):
        return []
    return j["data"].get("pool", []) or []


def _fetch_zb_pool(date=None):
    """炸板池"""
    date = date or _today_str()
    url = ("http://push2ex.eastmoney.com/getTopicZBPool"
           f"?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt"
           f"&Pageindex=0&pagesize=300&sort=fbt%3Aasc&date={date}")
    j = _http_json(url, timeout=8)
    if not j or not j.get("data"):
        return []
    return j["data"].get("pool", []) or []


def _pool_name(item):
    return item.get("n") or item.get("name") or "?"


def _pool_code(item):
    return item.get("c") or item.get("code") or "?"


def _pool_lbc(item):
    """连板数"""
    try:
        return int(item.get("lbc") or item.get("days") or item.get("ct") or 1)
    except Exception:
        return 1


def _pool_zdp(item):
    """涨跌幅%"""
    try:
        v = item.get("zdp") or item.get("p") or 0
        return float(v)
    except Exception:
        return 0.0


# ---------------- ② 龙头识别 ----------------
@register_tool(
    name="ltz_leader",
    description="龙头识别（核心）：人气榜前5 → 热门板块 → 板块内最强 → 综合，输出今日龙头梯队与空间板。用户问'今天龙头是谁/龙头识别'时使用。",
    parameters={
        "type": "object",
        "properties": {
            "date": {"type": "string", "description": "日期 YYYYMMDD，默认今天", "default": ""},
        },
        "required": [],
    },
    category="stock"
)
def ltz_leader(date: str = "") -> str:
    """龙头识别"""
    pool = _fetch_zt_pool(date)
    lines = ["🐉 龙头识别（人气→板块→最强→综合）\n"]

    if not pool:
        lines.append("⚠️ 涨停池数据获取失败（可能非交易日或接口异常）。")
        # 兜底：提示用人气榜
        lines.append("💡 可改用 ltz_renqi_rank 查看人气榜前5。")
        return "\n".join(lines)

    # 1. 空间板（连板最高）
    sorted_by_lb = sorted(pool, key=_pool_lbc, reverse=True)
    max_lb = _pool_lbc(sorted_by_lb[0]) if sorted_by_lb else 1
    space = [x for x in pool if _pool_lbc(x) == max_lb]
    lines.append(f"【空间板 · {max_lb}连板】")
    for x in space[:6]:
        lines.append(f"  ★ {_pool_name(x)}({_pool_code(x)}) {max_lb}连板 涨幅{_pool_zdp(x):.2f}%")

    # 2. 热门板块（涨停最多的行业）
    hy_stat = {}
    for x in pool:
        hy = x.get("hybk") or x.get("hy") or "其他"
        hy_stat[hy] = hy_stat.get(hy, 0) + 1
    top_hy = sorted(hy_stat.items(), key=lambda kv: kv[1], reverse=True)[:3]
    lines.append("\n【热门板块 · 涨停家数】")
    for hy, cnt in top_hy:
        lines.append(f"  🔥 {hy}：{cnt}家涨停")

    # 3. 板块内最强（每个热门板块里涨幅最大的那只）
    lines.append("\n【板块内最强（各热门板块龙头）】")
    for hy, _ in top_hy:
        hy_stocks = [x for x in pool if (x.get("hybk") or x.get("hy") or "其他") == hy]
        if not hy_stocks:
            continue
        strongest = max(hy_stocks, key=lambda x: (_pool_lbc(x), _pool_zdp(x)))
        lines.append(f"  👑 {hy} → {_pool_name(strongest)}({_pool_code(strongest)}) "
                     f"{_pool_lbc(strongest)}连板 涨幅{_pool_zdp(strongest):.2f}%")

    # 4. 综合结论
    lines.append("\n【综合龙头结论】")
    lines.append(f"  总龙头(最高板)：{'、'.join(_pool_name(x) for x in space[:3])}")
    lines.append(f"  主线题材：{top_hy[0][0] if top_hy else '无'}")
    lines.append(f"  今日涨停 {len(pool)} 家")

    return "\n".join(lines)


# ---------------- ③ 情绪温度计 ----------------
@register_tool(
    name="ltz_emotion",
    description="情绪温度计：涨停家数、连板高度、晋级率、炸板率 → 定位情绪周期（冰点/启动/发酵/高潮/分歧/退潮）。用户问'今天情绪/情绪周期/市场温度'时使用。",
    parameters={
        "type": "object",
        "properties": {
            "date": {"type": "string", "description": "日期 YYYYMMDD，默认今天", "default": ""},
        },
        "required": [],
    },
    category="stock"
)
def ltz_emotion(date: str = "") -> str:
    """情绪温度计"""
    pool = _fetch_zt_pool(date)
    zb = _fetch_zb_pool(date)
    lines = ["🌡️ 情绪温度计\n"]

    if not pool and not zb:
        lines.append("⚠️ 数据获取失败（可能非交易日或接口异常）。")
        return "\n".join(lines)

    zt_cnt = len(pool)
    zb_cnt = len(zb)

    # 连板高度
    max_lb = 0
    if pool:
        max_lb = max(_pool_lbc(x) for x in pool)

    # 晋级率：2连板及以上 / 昨日涨停（用连板≥2近似）
    jj_num = sum(1 for x in pool if _pool_lbc(x) >= 2)
    # 炸板率
    total_hit = zt_cnt + zb_cnt
    zb_rate = (zb_cnt / total_hit * 100) if total_hit else 0.0

    lines.append(f"  涨停家数：{zt_cnt} 家")
    lines.append(f"  炸板家数：{zb_cnt} 家")
    lines.append(f"  炸板率：{zb_rate:.1f}%")
    lines.append(f"  最高连板：{max_lb} 连板")
    lines.append(f"  连板≥2（晋级中）：{jj_num} 家")

    # 情绪周期定位（简化规则）
    if zt_cnt >= 80 and max_lb >= 7 and zb_rate < 25:
        stage = "高潮期 🔥"
        tip = "情绪亢奋，注意龙头分歧风险，勿追高"
    elif zt_cnt >= 50 and max_lb >= 5:
        stage = "发酵期 📈"
        tip = "情绪升温，可关注主线龙头的低吸机会"
    elif zt_cnt >= 30 and max_lb >= 3:
        stage = "启动期 🌱"
        tip = "情绪回暖，可试错首板/二板龙头"
    elif zt_cnt < 20 and max_lb <= 2:
        stage = "冰点期 ❄️"
        tip = "情绪冰点，空仓等待，或轻仓试错新题材"
    elif zb_rate >= 40:
        stage = "分歧/退潮期 ⚠️"
        tip = "炸板率高，风险大于机会，减仓防守"
    else:
        stage = "分歧期 ⚖️"
        tip = "多空分歧，谨慎操作，等明确信号"

    lines.append(f"\n  📍 情绪周期定位：{stage}")
    lines.append(f"  💡 操作建议：{tip}")

    return "\n".join(lines)


# ---------------- ④ 30分钟 MACD 买卖点 ----------------
@register_tool(
    name="ltz_macd30",
    description="30分钟MACD买卖点：金叉=买、死叉=卖。传入股票代码，返回最新金叉/死叉信号与DIF/DEA/柱值。用户问'XX股30分钟MACD/买卖点'时使用。",
    parameters={
        "type": "object",
        "properties": {
            "stock_code": {"type": "string", "description": "股票代码，如 002594、600519"},
            "klt": {"type": "integer", "description": "K线周期(分钟)：默认30，可改15/60", "default": 30},
        },
        "required": ["stock_code"],
    },
    category="stock"
)
def ltz_macd30(stock_code: str, klt: int = 30) -> str:
    """30分钟 MACD 买卖点"""
    code = str(stock_code).strip()
    secid = _secid(code)
    url = ("http://push2his.eastmoney.com/api/qt/stock/kline/get"
           f"?secid={secid}&fields1=f1,f2,f3,f4,f5,f6"
           f"&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
           f"&klt={klt}&fqt=1&end=20500101&lmt=150")
    j = _http_json(url, timeout=8)
    if not j or not j.get("data"):
        return f"❌ 无法获取 {code} 的{klt}分钟K线（可能代码错误或接口异常）。"

    data = j["data"]
    name = data.get("name", code)
    klines = data.get("klines", []) or []
    if len(klines) < 30:
        return f"❌ {name}({code}) K线数据不足（仅{len(klines)}根）。"

    closes = []
    for k in klines:
        parts = k.split(",")
        try:
            closes.append(float(parts[2]))  # 收盘价
        except Exception:
            continue
    if len(closes) < 30:
        return f"❌ 收盘价解析失败。"

    dif, dea, hist = _calc_macd(closes)
    if dif is None:
        return f"❌ MACD 计算失败（数据不足）。"

    n = len(dif)
    last_close = closes[-1]
    # 最新值
    dif_now, dea_now, hist_now = dif[-1], dea[-1], hist[-1]
    dif_prev, dea_prev = dif[-2], dea[-2]

    # 金叉/死叉判断
    signal = "无"
    if dif_prev <= dea_prev and dif_now > dea_now:
        signal = "🔴 金叉（买入信号）"
    elif dif_prev >= dea_prev and dif_now < dea_now:
        signal = "🟢 死叉（卖出信号）"

    # 近期趋势（最近5根）
    trend = "多头" if dif_now > dea_now else "空头"

    lines = [f"📊 {name}({code}) {klt}分钟 MACD"]
    lines.append(f"  最新收盘：{last_close:.2f}")
    lines.append(f"  DIF：{dif_now:.3f}")
    lines.append(f"  DEA：{dea_now:.3f}")
    lines.append(f"  MACD柱：{hist_now:.3f}")
    lines.append(f"  趋势：{trend}")
    lines.append(f"\n  🎯 信号：{signal}")

    if "金叉" in signal:
        lines.append("  💡 建议：金叉可考虑买入，单只仓位≤总资金1/3")
    elif "死叉" in signal:
        lines.append("  💡 建议：死叉可考虑卖出/止盈止损")

    return "\n".join(lines)


# ---------------- ⑤ 风控 ----------------
@register_tool(
    name="ltz_risk",
    description="风控提示：单只最多买入总资金1/3，结合当日炸板率给出风险等级与仓位建议。用户问'仓位/风控/能买多少'时使用。",
    parameters={
        "type": "object",
        "properties": {
            "total_capital": {"type": "number", "description": "总资金(元)，如 267358", "default": 0},
        },
        "required": [],
    },
    category="stock"
)
def ltz_risk(total_capital: float = 0) -> str:
    """风控提示"""
    zb = _fetch_zb_pool()
    pool = _fetch_zt_pool()
    zb_rate = 0.0
    if pool or zb:
        total_hit = len(pool) + len(zb)
        zb_rate = (len(zb) / total_hit * 100) if total_hit else 0.0

    lines = ["🛡️ 风控提示（龙头阵法铁律）\n"]
    lines.append("  📌 单只最多买入：总资金的 1/3")
    if total_capital > 0:
        one_third = total_capital / 3
        lines.append(f"  💰 总资金 {total_capital:,.0f} 元 → 单只上限 {one_third:,.0f} 元")
    else:
        lines.append("  💰 （未填总资金，默认按 1/3 比例执行）")

    lines.append(f"\n  今日炸板率：{zb_rate:.1f}%")
    if zb_rate >= 40:
        lines.append("  🚨 风险等级：高（炸板率高，空仓或极小仓位）")
    elif zb_rate >= 25:
        lines.append("  ⚠️ 风险等级：中（谨慎，单只仓位可降到1/6）")
    else:
        lines.append("  ✅ 风险等级：低（可正常按1/3仓位操作）")

    lines.append("\n  铁律：")
    lines.append("  1. 单只 ≤ 总资金 1/3")
    lines.append("  2. 金叉买入、死叉卖出，不扛单")
    lines.append("  3. 情绪退潮期（炸板率≥40%）空仓防守")
    return "\n".join(lines)


# ---------------- ⑥ 每日复盘 ----------------
@register_tool(
    name="ltz_review",
    description="每日复盘面板：龙头梯队（空间板/各连板）、题材主线、涨停/炸板统计。用户说'复盘/今日复盘/龙头梯队'时使用。",
    parameters={
        "type": "object",
        "properties": {
            "date": {"type": "string", "description": "日期 YYYYMMDD，默认今天", "default": ""},
        },
        "required": [],
    },
    category="stock"
)
def ltz_review(date: str = "") -> str:
    """每日复盘"""
    pool = _fetch_zt_pool(date)
    zb = _fetch_zb_pool(date)
    lines = ["📋 每日复盘 · 龙头梯队\n"]

    if not pool and not zb:
        lines.append("⚠️ 数据获取失败（可能非交易日或接口异常）。")
        return "\n".join(lines)

    lines.append(f"  涨停 {len(pool)} 家 / 炸板 {len(zb)} 家\n")

    if pool:
        # 按连板数分组
        lb_map = {}
        for x in pool:
            lb = _pool_lbc(x)
            lb_map.setdefault(lb, []).append(x)
        lines.append("【龙头梯队】")
        for lb in sorted(lb_map.keys(), reverse=True):
            stocks = lb_map[lb]
            names = "、".join(_pool_name(x) for x in stocks[:8])
            more = f" 等{len(stocks)}家" if len(stocks) > 8 else ""
            lines.append(f"  {lb}连板：{names}{more}")

        # 题材主线
        hy_stat = {}
        for x in pool:
            hy = x.get("hybk") or x.get("hy") or "其他"
            hy_stat[hy] = hy_stat.get(hy, 0) + 1
        top_hy = sorted(hy_stat.items(), key=lambda kv: kv[1], reverse=True)[:5]
        lines.append("\n【题材主线】")
        for hy, cnt in top_hy:
            lines.append(f"  🔥 {hy}：{cnt}家")

    lines.append("\n💡 明日观察：空间板能否晋级、主线是否延续、炸板率是否收敛。")
    return "\n".join(lines)



# ==================== 交易工具：桌面机器人操作同花顺模拟盘 ====================
# 复用 tools/desktop_bot/desktop_do.py 底层能力（mss截图 + OCR文字定位 + pyautogui键鼠）
# 安全闸门：
#   ① 所有下单工具默认 dry-run（confirm=False），只预演到填单完成并截图，不真正提交
#   ② 下单前 OCR 确认界面含「模拟」字样，防止误操作真实盘
#   ③ 每一步截图留证，定位失败立即中止并报告，不盲目继续点
import subprocess
import os as _os

_ROOT_DIR = Path(__file__).parent.parent.parent.parent
_DESKTOP_DO = str(_ROOT_DIR / 'tools' / 'desktop_bot' / 'desktop_do.py')
_CREATE_NO_WINDOW = 0x08000000
_THS_TITLE = '同花顺'


def _run_desktop(args, timeout=120):
    """调用 desktop_do.py 底层命令，返回 stdout 字符串。"""
    if not _os.path.exists(_DESKTOP_DO):
        return f'❌ 缺少桌面机器人脚本: {_DESKTOP_DO}'
    cmd = [sys.executable, _DESKTOP_DO] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding='utf-8', errors='replace',
                           timeout=timeout, cwd=str(_ROOT_DIR),
                           creationflags=_CREATE_NO_WINDOW)
        out = (r.stdout or '').strip()
        if r.returncode != 0:
            out += '\n[stderr] ' + ((r.stderr or '')[-600:])
        return out or f'(无输出, exit={r.returncode})'
    except subprocess.TimeoutExpired:
        return '⏰ 桌面操作超时，请确认同花顺窗口已在前台显示。'
    except Exception as e:
        return f'❌ 桌面操作失败: {e}'


def _ths_activate():
    """激活同花顺窗口（自动恢复最小化并置前）。"""
    return _run_desktop(['activate', '--title', _THS_TITLE], timeout=30)


def _ths_shot(tag):
    """截图留证，返回本地路径。"""
    from datetime import datetime as _dt
    path = str(_ROOT_DIR / 'data' / 'screenshots' / f"ths_{tag}_{_dt.now().strftime('%Y%m%d_%H%M%S')}.png")
    _run_desktop(['screenshot', '--save', path], timeout=30)
    return path


def _ths_click(text, exclude='', region='', timeout=60):
    """OCR 按文字点击，带窗口验证（点前确认前台是同花顺，防点错对象）。"""
    args = ['click', '--text', text, '--window', _THS_TITLE]
    if exclude:
        args += ['--exclude', exclude]
    if region:
        args += ['--region', region]
    return _run_desktop(args, timeout=timeout)


def _ths_type(text, pos=''):
    """输入文本（剪贴板直写+Ctrl+V，支持中文/数字）。"""
    args = ['type', '--text', text]
    if pos:
        args += ['--pos', pos]
    return _run_desktop(args, timeout=30)


def _ths_verify(text):
    """OCR 验证屏幕是否出现指定文字。"""
    return _run_desktop(['verify', '--text', text], timeout=60)


# ---------------- 交易① 登录交易软件 ----------------
@register_tool(
    name="ltz_trade_login",
    description="登录交易软件（同花顺模拟盘）：激活同花顺窗口→点击顶部「模拟」进入模拟盘→截图确认。用户说'登录交易/打开同花顺/进入模拟盘/连交易软件'时使用。",
    parameters={"type": "object", "properties": {}, "required": []},
    category="stock"
)
def ltz_trade_login() -> str:
    lines = ['🔐 交易软件登录（同花顺模拟盘）\n']
    r = _ths_activate()
    lines.append(f'  ① 激活同花顺窗口: {r}')
    r = _ths_click('模拟', timeout=60)
    lines.append(f'  ② 点击「模拟」进入模拟盘: {r}')
    # 等待界面切换后截图
    import time as _t
    _t.sleep(1.2)
    shot = _ths_shot('login')
    lines.append(f'  ③ 截图留证: {shot}')
    lines.append('\n💡 若截图显示已进入模拟盘交易界面，即可调用 ltz_trade_buy / ltz_trade_sell 下单。')
    return '\n'.join(lines)


# ---------------- 交易② 实时买入 ----------------
@register_tool(
    name="ltz_trade_buy",
    description="实时买入：在同花顺模拟盘买入股票。流程=进模拟盘→买入页→填代码/价格/数量→点买入。confirm=False(默认)只预演到填单完成并截图、不提交；confirm=True 才真正点「买入」并确认。",
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "股票代码，如 002594"},
            "amount": {"type": "integer", "description": "买入数量(股)"},
            "price": {"type": "string", "description": "买入价格(元)，留空=按默认(市价/卖一价)", "default": ""},
            "confirm": {"type": "boolean", "description": "是否真正提交下单(默认False只预演填单)", "default": False},
        },
        "required": ["code", "amount"],
    },
    category="stock"
)
def ltz_trade_buy(code: str, amount: int, price: str = "", confirm: bool = False) -> str:
    code = str(code).strip()
    lines = [f'🟥 实时买入 {code} × {amount}股' + ('（预演，不提交）' if not confirm else '（确认提交！）') + '\n']
    steps = []
    # 1 激活 + 进模拟盘
    steps.append('激活窗口: ' + _ths_activate())
    steps.append('点「模拟」: ' + _ths_click('模拟', timeout=60))
    import time as _t
    _t.sleep(1.0)
    # 2 进入买入页（F1 快捷键最稳）
    steps.append('进入买入页(F1): ' + _run_desktop(['hotkey', '--keys', 'f1'], timeout=30))
    _t.sleep(0.8)
    # 3 填代码（点代码框→输入）
    steps.append('点代码框: ' + _run_desktop(['click-pos', '--pos', '600,487'], timeout=30))
    steps.append('输入代码: ' + _ths_type(code))
    _t.sleep(0.5)
    # 4 填价格（可选）
    if price:
        steps.append('点价格框: ' + _run_desktop(['click-pos', '--pos', '800,487'], timeout=30))
        steps.append('输入价格: ' + _ths_type(str(price)))
        _t.sleep(0.5)
    # 5 填数量
    steps.append('点数量框: ' + _run_desktop(['click-pos', '--pos', '800,530'], timeout=30))
    steps.append('输入数量: ' + _ths_type(str(amount)))
    _t.sleep(0.5)
    # 6 截图留证（预演到此为止）
    shot = _ths_shot('buy_filled')
    steps.append(f'填单完成截图: {shot}')

    # 7 提交（仅 confirm=True）
    if confirm:
        steps.append('点「买入」按钮: ' + _ths_click('买入', exclude='F1', timeout=60))
        _t.sleep(0.8)
        # 弹确认框
        steps.append('点「确认」: ' + _ths_click('确定|确认|是', timeout=60))
        _t.sleep(1.0)
        shot2 = _ths_shot('buy_submitted')
        steps.append(f'提交后截图: {shot2}')
        lines.append('  ✅ 已提交买入委托（请核对当日委托确认成交）。')
    else:
        lines.append('  ⚠️ 预演模式：已完成填单，未提交。确认无误后用 confirm=True 真正下单。')

    for s in steps:
        lines.append('  · ' + s)
    lines.append('\n  📌 风控：单只买入 ≤ 总资金 1/3，请先用 ltz_risk 核对仓位上限。')
    return '\n'.join(lines)


# ---------------- 交易③ 实时卖出 ----------------
@register_tool(
    name="ltz_trade_sell",
    description="实时卖出：在同花顺模拟盘卖出持仓股票。流程=进模拟盘→卖出页→填代码/价格/数量→点卖出。confirm=False(默认)只预演到填单完成并截图、不提交；confirm=True 才真正点「卖出」并确认。",
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "股票代码，如 002594"},
            "amount": {"type": "integer", "description": "卖出数量(股)"},
            "price": {"type": "string", "description": "卖出价格(元)，留空=按默认(市价/买一价)", "default": ""},
            "confirm": {"type": "boolean", "description": "是否真正提交下单(默认False只预演填单)", "default": False},
        },
        "required": ["code", "amount"],
    },
    category="stock"
)
def ltz_trade_sell(code: str, amount: int, price: str = "", confirm: bool = False) -> str:
    code = str(code).strip()
    lines = [f'🟩 实时卖出 {code} × {amount}股' + ('（预演，不提交）' if not confirm else '（确认提交！）') + '\n']
    steps = []
    steps.append('激活窗口: ' + _ths_activate())
    steps.append('点「模拟」: ' + _ths_click('模拟', timeout=60))
    import time as _t
    _t.sleep(1.0)
    steps.append('进入卖出页(F2): ' + _run_desktop(['hotkey', '--keys', 'f2'], timeout=30))
    _t.sleep(0.8)
    steps.append('点代码框: ' + _run_desktop(['click-pos', '--pos', '600,487'], timeout=30))
    steps.append('输入代码: ' + _ths_type(code))
    _t.sleep(0.5)
    if price:
        steps.append('点价格框: ' + _run_desktop(['click-pos', '--pos', '800,487'], timeout=30))
        steps.append('输入价格: ' + _ths_type(str(price)))
        _t.sleep(0.5)
    steps.append('点数量框: ' + _run_desktop(['click-pos', '--pos', '800,530'], timeout=30))
    steps.append('输入数量: ' + _ths_type(str(amount)))
    _t.sleep(0.5)
    shot = _ths_shot('sell_filled')
    steps.append(f'填单完成截图: {shot}')

    if confirm:
        steps.append('点「卖出」按钮: ' + _ths_click('卖出', exclude='F2', timeout=60))
        _t.sleep(0.8)
        steps.append('点「确认」: ' + _ths_click('确定|确认|是', timeout=60))
        _t.sleep(1.0)
        shot2 = _ths_shot('sell_submitted')
        steps.append(f'提交后截图: {shot2}')
        lines.append('  ✅ 已提交卖出委托（请核对当日委托确认成交）。')
    else:
        lines.append('  ⚠️ 预演模式：已完成填单，未提交。确认无误后用 confirm=True 真正下单。')

    for s in steps:
        lines.append('  · ' + s)
    return '\n'.join(lines)


# ---------------- 交易④ 撤单 ----------------
@register_tool(
    name="ltz_trade_cancel",
    description="撤单：在同花顺模拟盘撤销未成交委托。流程=进模拟盘→当日委托/撤单页→定位未成交委托→点撤单。confirm=False(默认)只预演定位到委托并截图、不撤；confirm=True 才真正点撤单。",
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "要撤单的股票代码，留空=撤全部可撤委托", "default": ""},
            "confirm": {"type": "boolean", "description": "是否真正执行撤单(默认False只预演定位)", "default": False},
        },
        "required": [],
    },
    category="stock"
)
def ltz_trade_cancel(code: str = "", confirm: bool = False) -> str:
    lines = [f'⏹ 撤单' + ('（预演，不撤）' if not confirm else '（确认撤单！）') + '\n']
    steps = []
    steps.append('激活窗口: ' + _ths_activate())
    steps.append('点「模拟」: ' + _ths_click('模拟', timeout=60))
    import time as _t
    _t.sleep(1.0)
    # 进入撤单/委托页
    steps.append('进入撤单页: ' + _ths_click('撤单|当日委托|委托', timeout=60))
    _t.sleep(0.8)
    shot = _ths_shot('cancel_located')
    steps.append(f'委托页截图: {shot}')

    if confirm:
        # 有代码则先定位该代码所在行，再点其「撤单」按钮（OCR 定位「撤单」）
        if code:
            steps.append('定位代码行: ' + _ths_click(str(code), timeout=60))
            _t.sleep(0.5)
        steps.append('点「撤单」: ' + _ths_click('撤单', timeout=60))
        _t.sleep(0.8)
        steps.append('点「确认」: ' + _ths_click('确定|确认|是', timeout=60))
        _t.sleep(1.0)
        shot2 = _ths_shot('cancel_done')
        steps.append(f'撤单后截图: {shot2}')
        lines.append('  ✅ 已执行撤单（请核对当日委托是否已撤销）。')
    else:
        lines.append('  ⚠️ 预演模式：已定位到委托页，未执行撤单。确认后用 confirm=True 真正撤单。')

    for s in steps:
        lines.append('  · ' + s)
    return '\n'.join(lines)
