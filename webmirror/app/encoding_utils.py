"""
字符编码工具：检测 + 统一为 UTF-8。

设计原则
--------
镜像的所有文本文件**一律以 UTF-8 落盘**。既然如此，磁盘上残留的编码声明
（`<meta charset="gbk">`、`@charset "gbk"`、`<?xml encoding="gbk"?>`）就必须
同步改写成 UTF-8，否则浏览器会拿旧编码去解析 UTF-8 字节 → 整页乱码。
"""
from __future__ import annotations

import codecs
import posixpath
import re

# 不可信的“通用”编码声明：不少服务器把 text/html 一律声明成 latin-1，
# 内容其实是 UTF-8 或 GBK。遇到这些一律降级，交给探测处理。
GENERIC_CHARSETS = {
    "", "ascii", "us-ascii", "iso-8859-1", "iso8859-1", "iso_8859-1",
    "latin-1", "latin1", "cp1252", "windows-1252", "iso-8859-15",
    "binary", "unknown-8bit", "none",
}

# 没有可用声明时，按此顺序尝试（中文站点优先）
FALLBACK_ENCODINGS = ["utf-8", "gb18030", "big5", "shift_jis", "euc-kr",
                      "euc-jp", "cp1252", "latin-1"]

# 高频汉字表：样本很短时 charset_normalizer 会在 GBK / Big5 / Shift-JIS 之间
# 摇摆（几个候选评分完全相同），这时用“解码出来的是不是常用字”来投票最有效。
# 正确的解码必然得到常用字；错误解码（如把 GBK 按 Big5 解）只会得到生僻字。
COMMON_HANZI = frozenset(
    "的一是了在人有我他这个们中来上大为和国地到以说时要就出会可也你对生能而"
    "子那得于着下自之年过发后作里用道行所然家种事成方多经去法学如都同现当没"
    "动面起看定天分还进好小部其些主样理心她本前开但因只从想实日军者意无它与"
    "长把机十民第公此已工使情明性知全三又关点正业外将两高间由问很最重并物手"
    "应战向头文体政美相见被利什二等产或新己制身果加西斯月话合回特代内信表化"
    "老给世位次度门任常先海通教儿原东声提立及比员解水名真论处走义各入几口认"
    "条平系气题活尔更别打女变四神总何电数安少报才结反受目太量再感建务做接必"
    "场件计管期市直德资命山金指克许统区保至队形社便空决治展马科司五基眼书非"
    "则听白却界达光放强即像难且权思王象完设式色路记南品住告类求据程北边死张"
    "该交规万取拉格望觉术领共确传师观清今切院让识候带导争运笑飞风步改收根干"
    "造言联持组每济车亲极林服快办议往元英士证近失转夫令准布始怎呢存未远叫台"
    "单影具罗字爱击流备兵连调深商算质团集百需价花党华城石级整府离况亚请技际"
    "约示复病息究线似官火断精满支视消越器容照须九增研写称企八功吗包片史委乎"
    "查轻易早曾除农找装广显吧阿李标谈吃图念六引历首医局突专费号尽另周较注语"
    "仅考落青随选列武红响虽推势参希古众构房半节土投某案黑维革划敌致陈律足态"
    "护七兴派孩验责营星够章音跟志底站严巴例防族供效续施留讲型料终答紧黄绝奇"
    "察母京段依批群项故按河米围江织害斗双境客纪采举杀攻父苏密低朝友诉止细愿"
    "千值仍男钱破网热助倒育属坐帝限船脸职速刻乐否刚威毛状率甚独球般普怕弹校"
    "苦创假久错承印晚兰试股拿脑预谁益阳若哪微尼继送急血惊伤素药适波夜省初喜"
    "卫源食险待述陆习置居劳财环排福纳欢雷警获模充负云停木游龙树疑层冷洲冲射"
    "略范竟句室异激汉村哈策演简卡罪判担州静退既衣您宗积余痛检差富灵协角占配"
    "征修皮挥胜降阶审沉坚善妈刘读啊超免压银买皇养伊怀执副乱抗犯追帮宣佛岁航"
    "优怪香著田铁控税左右份穿艺背阵草脚概恶块顿敢守酒岛托央户烈洋哥索胡款靠"
    "评版宝座释景顾弟登货互付伯慢欧换闻危忙核暗姐介坏讨丽良序升监临亮露永呼"
    "味野架域沙掉括舰鱼杂误湾吉减编楚肯测败屋跑梦散温困剑渐封救贵枪缺楼县尚"
    "毫移娘朋画班智亦耳恩短掌恐遗固席松秘谢鲁遇康虑幸均销钟诗藏赶剧票损忽巨"
    "炮旧端探湖录叶春乡附吸予礼港雨呀板庭妇归睛饭额含顺输摇招婚脱补谓督毒油"
    "疗旅泽材灭逐莫笔亡鲜词圣择寻厂睡博勒烟授诺伦岸奥唐卖俄炸载洛健堂旁宫喝"
    "借君禁阴园谋宋避抓荣姑孙逃牙束跳顶玉镇雪午练迫爷篇肉嘴馆遍凡础洞卷坦牛"
    "宁纸诸训私庄祖丝翻暴森塔默握戏隐熟骨访弱蒙歌店鬼软典欲萨伙遭盘爸扩盖弄"
    "雄稳忘亿刺拥徒姆杨齐赛趣曲刀床迎冰虚玩析窗醒妻透购替塞努休虎扬途侵刑绿"
    "兄迅套贸毕唯谷轮库迹尤竞街促延震弃甲伟麻川申缓潜闪售灯针哲络抵朱埃抱鼓"
    "植纯夏忍页杰筑折郑贝尊吴秀混臣雅振染盛怒舞圆搞狂措姓残秋培迷诚宽宇猛摆"
    "梅毁伸摩盟末龟"
)

CHARSET_RE = re.compile(r"""charset\s*=\s*["']?([\w\-]+)""", re.I)
META_CHARSET_RE = re.compile(rb"""<meta[^>]+charset\s*=\s*["']?([\w\-]+)""", re.I)
CSS_CHARSET_RE = re.compile(r"""@charset\s+(["'])[\w\-]+\1\s*;""", re.I)
XML_DECL_RE = re.compile(r"""(<\?xml[^>]*encoding\s*=\s*["'])[\w\-]+""", re.I)

# 需要统一转成 UTF-8 的文本类资源后缀
TEXT_ASSET_EXT = {".js", ".mjs", ".cjs", ".json", ".xml", ".svg", ".txt",
                  ".csv", ".webmanifest", ".atom", ".rss", ".xsl", ".xslt",
                  ".vtt", ".map"}
TEXTUAL_CTYPE_RE = re.compile(
    r"^(text/|application/(javascript|json|xml|manifest\+json)|image/svg\+xml)",
    re.I,
)


def _norm_cs(name):
    """把编码名规范化，便于和 GENERIC_CHARSETS 比对。"""
    if not name:
        return None
    n = str(name).strip().strip("\"'").lower()
    return n or None


def _dedup(items):
    """去重并保持顺序。"""
    seen, out = set(), []
    for it in items:
        if it and it not in seen:
            seen.add(it)
            out.append(it)
    return out


def sniff_meta_charset(raw):
    """从 HTML 字节流里嗅探 <meta> 声明的字符集（只看前 4KB）。"""
    m = META_CHARSET_RE.search(raw[:4096])
    return m.group(1).decode("ascii", "ignore") if m else None


def probe_encoding(raw):
    """用 charset_normalizer 做统计探测（只分析前 256KB，够准且快）。"""
    try:
        from charset_normalizer import from_bytes
        best = from_bytes(raw[:262_144]).best()
        if best is not None and best.encoding:
            return best.encoding
    except Exception:                      # noqa: BLE001  探测失败不该影响抓取
        pass
    return None


def _hanzi_score(text):
    """
    给一段解码结果打“像不像正常中文”的分。

    :return: (高频汉字占全部汉字的比例, 汉字总数)
    """
    hanzi = 0
    hit = 0
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff":
            hanzi += 1
            if ch in COMMON_HANZI:
                hit += 1
    if not hanzi:
        return 0.0, 0
    return hit / hanzi, hanzi


def detect_encoding(raw, *declared):
    """
    推断字节流的真实编码。顺序即优先级：

      1. BOM 最可信；
      2. 整段是合法 UTF-8 → 判定 UTF-8。中文 GBK/Big5 页面几乎不可能整段都是
         合法 UTF-8，而“声明 GBK、实际 UTF-8”的错配站点很常见，这一步一并解决；
      3. 声明的编码（响应头 → meta），跳过 latin-1 这类不可靠的通用声明；
      4. 无可靠声明时，把候选编码逐个解码，用「高频汉字命中率」投票
         （短样本下统计探测会在 GBK/Big5/Shift-JIS 之间摇摆，投票更稳）；
      5. 都看不出中文特征时，优先采信统计探测，其次按固定顺序试；
      6. 全部失败则 utf-8 + replace，保证不抛异常。

    :param raw: 原始字节
    :param declared: 候选声明编码，按可信度从高到低
    :return: 编码名
    """
    if raw.startswith(codecs.BOM_UTF8):
        return "utf-8-sig"
    if raw.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return "utf-16"
    if raw.startswith((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)):
        return "utf-32"

    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass

    # 3) 采信声明（跳过不可靠的通用声明）
    for cs in declared:
        cs = _norm_cs(cs)
        if not cs or cs in GENERIC_CHARSETS:
            continue
        try:
            codecs.lookup(cs)
        except LookupError:
            continue
        try:
            raw.decode(cs)
            return cs
        except UnicodeDecodeError:
            continue

    probed = _norm_cs(probe_encoding(raw))
    candidates = _dedup([probed] + FALLBACK_ENCODINGS)

    # 4) 用高频汉字投票挑出最像中文的解码
    best_enc, best_score = None, 0.0
    for cs in candidates:
        try:
            text = raw.decode(cs)
        except (LookupError, UnicodeDecodeError):
            continue
        ratio, hanzi = _hanzi_score(text)
        if hanzi and ratio > best_score:
            best_enc, best_score = cs, ratio
        if best_score >= 0.95:
            break
    if best_enc is not None and best_score >= 0.3:
        return best_enc

    # 5) 没有明显中文特征：优先统计探测，其次固定顺序
    for cs in candidates:
        try:
            raw.decode(cs)
            return cs
        except (LookupError, UnicodeDecodeError):
            continue

    return "utf-8"


def decode_body(resp):
    """按 BOM / 响应头 / HTML meta 推断编码，把响应体解码成 str。"""
    raw = resp.content
    m = CHARSET_RE.search(resp.headers.get("content-type", ""))
    header_cs = m.group(1) if m else None
    enc = detect_encoding(raw, header_cs, sniff_meta_charset(raw))
    try:
        return raw.decode(enc, errors="strict")
    except (LookupError, UnicodeDecodeError):
        try:
            return raw.decode(enc, errors="replace")
        except LookupError:
            return raw.decode("utf-8", errors="replace")


def normalize_html_charset(soup):
    """
    把 HTML 内的字符集声明统一改成 utf-8；完全没有声明就补一个。

    镜像文件按 UTF-8 落盘，若页面里还留着 `charset=gbk`，浏览器会拿 GBK 去解
    UTF-8 字节 → 乱码；若完全没有声明，中文 Windows 的浏览器会按本地默认编码
    （GBK）去猜 UTF-8 文件 → 同样乱码。所以必须显式声明 utf-8。

    :param soup: BeautifulSoup 对象（原地修改）
    """
    declared = False
    for meta in soup.find_all("meta"):
        if meta.get("charset") is not None:
            meta["charset"] = "utf-8"
            declared = True
        http_equiv = str(meta.get("http-equiv") or "").strip().lower()
        content = meta.get("content")
        if http_equiv == "content-type" and isinstance(content, str) \
                and CHARSET_RE.search(content):
            meta["content"] = CHARSET_RE.sub("charset=utf-8", content)
            declared = True
    if declared:
        return

    new_meta = soup.new_tag("meta")
    new_meta.attrs["charset"] = "utf-8"
    host = soup.find("head")
    if host is None:
        host = soup.find("html")
    if host is not None:
        host.insert(0, new_meta)
    else:
        soup.insert(0, new_meta)


def to_utf8_text(data, relpath, ctype=""):
    """
    把文本类资源（JS/JSON/XML/SVG 等）统一转成 UTF-8。

    HTML 已经转成 UTF-8 了，若外链的 JS/XML 仍是 GBK 字节，浏览器会按 UTF-8
    去读 → 里面的中文变乱码。已经是 UTF-8 的文件原样返回，一个字节都不改。

    :param data: 原始字节
    :param relpath: 本地相对路径（用于判断扩展名）
    :param ctype: 响应 Content-Type
    :return: 字节（UTF-8 或原样）
    """
    ext = posixpath.splitext(relpath)[1].lower()
    if ext not in TEXT_ASSET_EXT and not TEXTUAL_CTYPE_RE.match(ctype or ""):
        return data
    if b"\x00" in data[:4096]:            # 含 NUL，基本可断定不是纯文本，别动
        return data
    try:
        data.decode("utf-8")
        return data                       # 本来就是 UTF-8，原样保留
    except UnicodeDecodeError:
        pass

    enc = detect_encoding(data)
    try:
        text = data.decode(enc)
    except (LookupError, UnicodeDecodeError):
        return data
    text = XML_DECL_RE.sub(r"\1utf-8", text, count=1)
    return text.encode("utf-8")


def ensure_css_utf8_charset(css):
    """CSS 统一以 UTF-8 落盘，@charset 需同步改写（它只允许出现在文件最前面）。"""
    if CSS_CHARSET_RE.search(css[:200]):
        return CSS_CHARSET_RE.sub('@charset "utf-8";', css, count=1)
    return css
