#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""7坛 BBS 帖子发布后验收 —— 纯 HTTP 断言，输出 PASS / FAIL（不靠人眼读页面）

为什么有这个脚本：
    以前每次发完帖，要由 AI 亲自读页面 HTML、逐条打印、再口头汇报"已核对"。
    这种"自己查自己"的形式会漏：报过体积但没量、留了旧截图、首页缓存没清。
    这里把可以机器判定的项目全部固化成断言，一条命令出结论。

不依赖：
    不连数据库、不需要服务器密码，只从游客视角抓公开页面。

用法：
    python tools/bbs_verify.py 84149
    python tools/bbs_verify.py 84149 --from-article D:\\7tan\\dsh-workspace\\article-zcy
    python tools/bbs_verify.py 84149 --expect expect.json
    python tools/bbs_verify.py 84149 --json result.json
    python tools/bbs_verify.py 84149 --no-lists           # 只验帖子页，不抓列表/首页/主页

退出码：
    0 = 无 FAIL（可能有 SKIP）
    1 = 有 FAIL
    2 = 参数或抓取异常，无法判定
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = 'https://www.7tan.com'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')

# 铁律：这些词不该出现在正文里
BAD_AI = ['综上所述', '总而言之', '不难看出', '毋庸置疑', '由此可见',
          '值得一提的是', '在这个背景下', '不得不说']
# 文章不能"按图片写"
BAD_IMG = ['如上图', '按图片', '由图可见', '图中可以看到', '从图上',
           '配图', '图源', '如图所示', '根据截图', '从截图来看']
# 未替换的 UBB 标签
UBB_TAGS = ['title', 'subtitle', 'caption', 'divider', 'hl', 'b', 'img', 'url']
# PHP 报错特征
PHP_ERR = ['Warning:', 'Notice:', 'Fatal error', 'Deprecated:', 'Parse error']


# ---------------------------------------------------------------- 抓取

def fetch(url: str, method: str = 'GET', timeout: int = 30, retries: int = 3):
    """返回 (status, headers, bytes)。4xx/5xx 不抛异常，直接返回状态码。"""
    err = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, method=method,
                                         headers={'User-Agent': UA,
                                                  'Accept-Language': 'zh-CN,zh;q=0.9'})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = b'' if method == 'HEAD' else r.read()
                return r.status, dict(r.headers), body
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers or {}), b''
        except Exception as e:                                  # 超时/连接重置
            err = e
            if i < retries - 1:
                time.sleep(0.8)
    raise err  # type: ignore[misc]


def fetch_text(url: str, timeout: int = 30) -> tuple[int, str]:
    st, _, body = fetch(url, timeout=timeout)
    return st, body.decode('utf-8', 'ignore')


# ---------------------------------------------------------------- 解析

def strip_scripts(html: str) -> str:
    """去掉 <script> 与 <style>。

    站点会把 UBB 原文塞进内联 JSON（可见 15 处字面 [title]），
    不去掉的话"UBB 残留"这项会假阳性。
    """
    h = re.sub(r'<script\b.*?</script>', '', html, flags=re.S | re.I)
    h = re.sub(r'<style\b.*?</style>', '', h, flags=re.S | re.I)
    return h


def strip_tags(html: str) -> str:
    t = re.sub(r'<[^>]+>', '', html)
    t = (t.replace('&#91;', '[').replace('&#93;', ']')
          .replace('&#42;', '*').replace('&amp;', '&')
          .replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' '))
    return t


def squeeze(s: str) -> str:
    """去掉所有空白，用于中文串比对（站内换行位置不可控）。"""
    return re.sub(r'\s+', '', s)


def cn_len(s: str) -> int:
    return len(re.findall(r'[\u4e00-\u9fff]', s))


def jsonld_blocks(html: str) -> list[dict]:
    out = []
    for m in re.finditer(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>',
                         html, re.S | re.I):
        try:
            out.append(json.loads(m.group(1)))
        except Exception:
            continue
    return out


def meta_of(html: str) -> dict:
    """从帖子里提取结构化事实：标题、板块、作者 uid、breadcrumb。"""
    info = {'title_tag': None, 'headline': None, 'h1': None,
            'board_name': None, 'board_id': None, 'author_uid': None,
            'desc': None}

    m = re.search(r'<title>(.*?)</title>', html, re.S)
    if m:
        info['title_tag'] = re.sub(r'\s+', ' ', strip_tags(m.group(1))).strip()

    m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
    if m:
        info['h1'] = re.sub(r'\s+', ' ', strip_tags(m.group(1))).strip()

    for blk in jsonld_blocks(html):
        items = blk if isinstance(blk, list) else [blk]
        for it in items:
            if not isinstance(it, dict):
                continue
            t = it.get('@type')
            if t == 'DiscussionForumPosting':
                info['headline'] = (it.get('headline') or '').strip() or None
                info['desc'] = (it.get('description') or '').strip() or None
            if t == 'BreadcrumbList':
                for el in it.get('itemListElement') or []:
                    nm, item = (el.get('name') or ''), (el.get('item') or '')
                    mb = re.search(r'/bbs/board/(\d+)/', item)
                    if mb:
                        info['board_name'] = nm.strip()
                        info['board_id'] = mb.group(1)

    m = re.search(r'/bbs/profile\.php\?id=(\d+)', html)
    if m:
        info['author_uid'] = m.group(1)
    return info


def image_urls(body: str) -> list[str]:
    return re.findall(r'https://img\.7tan\.com/uploads/images/[^\s"\'<>)\]]+', body)


def _title_from_md(text: str) -> str | None:
    """标准情况：markdown 首行是 `# 标题`。"""
    m = re.search(r'^\s*#\s+(.+?)\s*$', text, re.M)
    return m.group(1).strip() if m else None


def _title_from_html(d: Path) -> str | None:
    """md 没写标题行时，取排版 HTML 的 h1（h1 就是最终发布标题）。"""
    for name in ('公众号版.html', '排版.html'):
        f = d / name
        if not f.is_file():
            continue
        h = f.read_text(encoding='utf-8', errors='ignore')
        m = re.search(r'<h1[^>]*>(.*?)</h1>', h, re.S)
        if m:
            t = re.sub(r'\s+', ' ', strip_tags(m.group(1))).strip()
            if t:
                return t
    # 最后尝试 base64 内嵌版（体积大，放最后）
    f = d / '公众号版-可直接粘贴.html'
    if f.is_file():
        with open(f, encoding='utf-8', errors='ignore') as fh:
            head = fh.read(200000)
        m = re.search(r'<h1[^>]*>(.*?)</h1>', head, re.S)
        if m:
            t = re.sub(r'\s+', ' ', strip_tags(m.group(1))).strip()
            if t:
                return t
    return None


def _title_from_txt(d: Path) -> str | None:
    """再退一步：纯文本正文的首行，且长得像标题才采用。"""
    for name in ('文章正文.txt', 'gzh_source.txt'):
        f = d / name
        if not f.is_file():
            continue
        lines = [x.strip() for x in
                 f.read_text(encoding='utf-8', errors='ignore').splitlines() if x.strip()]
        if lines:
            first = lines[0]
            if len(first) <= 60 and ('测评' in first or first.startswith('《')):
                return first
    return None


def _resolve_title(md_text: str, d: Path) -> tuple[str | None, str | None]:
    t = _title_from_md(md_text)
    if t:
        return t, 'markdown 的 # 行'
    t = _title_from_html(d)
    if t:
        return t, '公众号版 html 的 h1'
    t = _title_from_txt(d)
    if t:
        return t, '正文 txt 首行'
    return None, None


def expect_from_article(folder: str) -> dict:
    """从文章目录的 markdown 源推导期望值，实现「源文件 → 线上页面」闭环。"""
    d = Path(folder)
    if not d.is_dir():
        raise SystemExit('不是目录: %s' % folder)
    md = None
    for name in ('gzh_source.md', 'article.md', '文章正文.md', '正文.md'):
        if (d / name).is_file():
            md = d / name
            break
    if md is None:
        cands = [p for p in sorted(d.glob('*.md')) if not p.name.startswith('载入中')]
        if not cands:
            raise SystemExit('目录里找不到 markdown 正文: %s' % folder)
        md = cands[0]

    text = md.read_text(encoding='utf-8', errors='ignore')
    title, title_from = _resolve_title(text, d)
    return {
        'title': title,
        'title_from': title_from,
        'images': len(re.findall(r'^\s*!\s*\[', text, re.M)),
        'sections': len(re.findall(r'^##\s+\S', text, re.M)),
        'source_md': str(md),
        'source_chars': cn_len(text),
    }


# ---------------------------------------------------------------- 结果收集

class Report:
    def __init__(self, pid: str, url: str):
        self.pid = pid
        self.url = url
        self.items: list[dict] = []

    def add(self, status: str, name: str, detail: str = ''):
        assert status in ('PASS', 'FAIL', 'SKIP', 'WARN')
        self.items.append({'status': status, 'name': name, 'detail': detail})

    def ok(self, name, detail=''):
        self.add('PASS', name, detail)

    def bad(self, name, detail=''):
        self.add('FAIL', name, detail)

    def skip(self, name, detail=''):
        self.add('SKIP', name, detail)

    def warn(self, name, detail=''):
        self.add('WARN', name, detail)

    def check(self, cond, name, ok_detail='', bad_detail=''):
        (self.ok if cond else self.bad)(name, ok_detail if cond else bad_detail)
        return bool(cond)

    @property
    def n_fail(self):
        return sum(1 for i in self.items if i['status'] == 'FAIL')

    @property
    def n_pass(self):
        return sum(1 for i in self.items if i['status'] == 'PASS')

    @property
    def n_skip(self):
        return sum(1 for i in self.items if i['status'] == 'SKIP')

    @property
    def n_warn(self):
        return sum(1 for i in self.items if i['status'] == 'WARN')

    def render(self):
        line = '─' * 74
        print('╔' + '═' * 72 + '╗')
        print('║ 7坛帖子验收  pid=%s' % self.pid)
        print('║ %s' % self.url)
        print('╚' + '═' * 72 + '╝')
        icon = {'PASS': '✅', 'FAIL': '❌', 'SKIP': '⏭ ', 'WARN': '⚠️ '}
        for idx, it in enumerate(self.items, 1):
            head = '%s %2d. %-30s' % (icon[it['status']], idx, it['name'])
            if it['detail']:
                print('%s %s' % (head, it['detail']))
            else:
                print(head)
        print(line)
        verdict = 'PASS' if self.n_fail == 0 else 'FAIL'
        print(' 共 %d 项：%d PASS / %d FAIL / %d WARN / %d SKIP   =>  %s %s'
              % (len(self.items), self.n_pass, self.n_fail, self.n_warn,
                 self.n_skip, icon[verdict], verdict))
        print(line)
        return verdict

    def to_json(self):
        return {'pid': self.pid, 'url': self.url,
                'verdict': 'PASS' if self.n_fail == 0 else 'FAIL',
                'counts': {'pass': self.n_pass, 'fail': self.n_fail,
                           'warn': self.n_warn, 'skip': self.n_skip},
                'items': self.items}


# ---------------------------------------------------------------- 主流程

def main(argv=None):
    ap = argparse.ArgumentParser(description='7坛帖子发布后验收（纯 HTTP 断言）')
    ap.add_argument('pid', help='帖子 id，如 84149')
    ap.add_argument('--expect', help='期望值 JSON 路径')
    ap.add_argument('--from-article', dest='from_article',
                    help='从文章 markdown 目录推导期望值（标题/图数/小节数）')
    ap.add_argument('--board', help='期望板块名，如 游戏交流')
    ap.add_argument('--uid', help='期望作者 uid，默认 1（老马）')
    ap.add_argument('--author', help='期望作者昵称')
    ap.add_argument('--images', type=int, help='期望图片数（覆盖推导值）')
    ap.add_argument('--no-lists', action='store_true',
                    help='跳过 board 列表 / 首页 / 作者主页收录检查')
    ap.add_argument('--json', dest='json_out', help='把结果写入 JSON 文件')
    ap.add_argument('--timeout', type=int, default=30)
    args = ap.parse_args(argv)

    pid = str(args.pid).strip()
    if not pid.isdigit():
        print('pid 必须是数字: %r' % pid, file=sys.stderr)
        return 2

    # ---- 汇总期望值
    exp: dict = {}
    src_note = []
    if args.from_article:
        auto = expect_from_article(args.from_article)
        exp.update({k: v for k, v in auto.items() if v is not None})
        src_note.append('来自 %s' % Path(auto['source_md']).name)
    if args.expect:
        exp.update(json.loads(Path(args.expect).read_text(encoding='utf-8')))
        src_note.append('来自 %s' % Path(args.expect).name)
    if args.images is not None:
        exp['images'] = args.images
    if args.board:
        exp['board'] = args.board
    exp.setdefault('uid', args.uid or '1')
    if args.author:
        exp['author'] = args.author

    url = '%s/bbs/%s/' % (BASE, pid)
    rep = Report(pid, url)
    if src_note:
        print('期望值来源：' + ' + '.join(src_note))
        for k in ('title', 'images', 'sections', 'source_chars'):
            if k in exp:
                print('   %-13s %s' % (k, exp[k]))
        if exp.get('title_from'):
            print('   %-13s %s' % ('标题出处', exp['title_from']))
        if not exp.get('title'):
            print('   %-13s %s' % ('标题', '(源里没找到，跳过标题比对)'))
        print()

    # ---- 0. 抓帖子页
    try:
        st, html = fetch_text(url, timeout=args.timeout)
    except Exception as e:
        print('抓取失败：%r' % (e,), file=sys.stderr)
        return 2

    if not rep.check(st == 200, 'HTTP 状态',
                     '200  %s bytes' % format(len(html), ','),
                     '返回 %s（期望 200）' % st):
        rep.render()
        if args.json_out:
            Path(args.json_out).write_text(
                json.dumps(rep.to_json(), ensure_ascii=False, indent=2), encoding='utf-8')
        return 1

    body = strip_scripts(html)
    plain = strip_tags(body)
    plain_sq = squeeze(plain)
    meta = meta_of(html)

    # ---- 1. 标题三处一致
    if meta['title_tag'] is None:
        rep.bad('页面 <title>', '缺失')
    else:
        rep.ok('页面 <title>', meta['title_tag'][:60])

    if meta['headline'] and meta['h1']:
        rep.check(squeeze(meta['headline']) == squeeze(meta['h1']),
                  'h1 与 JSON-LD headline 一致',
                  meta['h1'][:60],
                  'h1=%r  headline=%r' % (meta['h1'][:40], meta['headline'][:40]))
    else:
        rep.skip('h1 与 JSON-LD headline 一致', '结构化数据或 h1 缺失')

    page_title = meta['h1'] or meta['headline'] or meta['title_tag'] or ''
    if exp.get('title'):
        want = squeeze(exp['title'])
        got = squeeze(page_title)
        rep.check(want == got, '标题与文章源一致',
                  page_title[:60],
                  '页面=%r  期望=%r' % (page_title[:50], exp['title'][:50]))
    else:
        rep.skip('标题与文章源一致', '未提供 --from-article / --expect')

    # ---- 2. 标题红线（用户铁律：标题不写"实测"）
    rep.check('实测' not in page_title, '标题不含"实测"', 'OK',
              '标题出现"实测"：%s' % page_title[:50])

    # ---- 3. 正文体量
    n_cn = cn_len(plain)
    rep.check(n_cn >= 300, '正文字数', '%d 汉字' % n_cn, '仅 %d 汉字，疑似正文缺失' % n_cn)

    # ---- 4. 组件计数
    n_bg = body.count('background-image')
    n_cap = body.count('ubb-caption')
    n_title = body.count('ubb-title')
    n_sub = body.count('ubb-subtitle')
    urls = image_urls(body)
    n_img = len(urls)

    rep.check(n_img > 0, '正文图片数', '%d 张' % n_img, '页面里没有 img.7tan.com 图片')
    rep.check(n_bg == n_img, 'background-image 与图片数一致',
              '均 %d' % n_img, 'background-image=%d  图片=%d' % (n_bg, n_img))
    rep.check(n_cap == n_img, '图注数与图片数一致',
              '均 %d' % n_img, '图注=%d  图片=%d' % (n_cap, n_img))

    if exp.get('images'):
        rep.check(n_img == int(exp['images']), '图片数与文章源一致',
                  '均 %d' % n_img, '页面 %d 张  源文件 %s 张' % (n_img, exp['images']))
    else:
        rep.skip('图片数与文章源一致', '未知期望图数')

    if exp.get('sections'):
        rep.check(n_title == int(exp['sections']), '小标题数与文章源一致',
                  '均 %d' % n_title, '页面 %d 个  源文件 %s 个' % (n_title, exp['sections']))
    else:
        rep.check(n_title >= 1, '小标题数', '%d 个' % n_title, '没有 ubb-title')

    rep.check(n_sub >= 0, '副标题块', '存在 %d 个' % n_sub if n_sub else '未使用')

    # ---- 5. 图片可访问性（并发 HEAD）
    uniq = list(dict.fromkeys(urls))
    bad_img = []

    def head(u):
        try:
            s, h, _ = fetch(u, method='HEAD', timeout=args.timeout, retries=2)
            return u, s, h.get('Content-Length')
        except Exception as e:
            return u, 'ERR:%r' % (e,), None

    with ThreadPoolExecutor(max_workers=8) as pool:
        for u, s, cl in pool.map(head, uniq):
            if s != 200 or (cl is not None and int(cl) <= 0):
                bad_img.append('%s -> %s CL=%s' % (u.rsplit('/', 1)[-1], s, cl))
    rep.check(not bad_img, '图片全部可访问',
              '%d/%d HEAD 200' % (len(uniq), len(uniq)),
              '%d 张异常：%s' % (len(bad_img), '; '.join(bad_img[:4])))

    # ---- 6. UBB 残留（已剔除 script）
    left = {}
    for t in UBB_TAGS:
        c = body.count('[%s]' % t) + body.count('[/%s]' % t)
        if c:
            left[t] = c
    rep.check(not left, 'UBB 标签已全部渲染',
              '无残留', '发现未渲染标签：%s' % left)
    rep.check('{%' not in body and not re.search(r'\{IMG\d+\}', body),
              '图片占位符已替换', '无残留',
              '仍有未替换占位符：%s' % re.findall(r'\{\w+\}', body)[:4])

    # ---- 7. PHP 报错
    php = {e: html.count(e) for e in PHP_ERR if html.count(e)}
    rep.check(not php, 'PHP 无报错', '0 条',
              '出现报错：%s' % php)

    # ---- 8. 板块与作者
    if exp.get('board'):
        rep.check(meta['board_name'] == exp['board'], '板块正确',
                  '%s (%s)' % (meta['board_name'], meta['board_id']),
                  '页面=%r  期望=%r' % (meta['board_name'], exp['board']))
    elif meta['board_name']:
        rep.ok('板块', '%s (%s)' % (meta['board_name'], meta['board_id']))
    else:
        rep.skip('板块', '面包屑里没有 board 链接')

    if meta['author_uid']:
        rep.check(meta['author_uid'] == str(exp['uid']), '作者 uid 正确',
                  'uid=%s' % meta['author_uid'],
                  '页面 uid=%s  期望 %s' % (meta['author_uid'], exp['uid']))
    else:
        rep.skip('作者 uid 正确', '页面没有 profile.php?id= 链接')

    # ---- 9. 禁串
    hit_ai = [w for w in BAD_AI if w in plain]
    rep.check(not hit_ai, '无 AI 套话', '0 命中', '命中：%s' % hit_ai)
    hit_img = [w for w in BAD_IMG if w in plain]
    rep.check(not hit_img, '无"按图写"表述', '0 命中', '命中：%s' % hit_img)

    # ---- 10. 关键串
    must = exp.get('must_contain') or []
    if must:
        miss = [k for k in must if squeeze(str(k)) not in plain_sq]
        rep.check(not miss, '关键串全部命中',
                  '%d/%d' % (len(must) - len(miss), len(must)),
                  '缺失 %d 项：%s' % (len(miss), miss[:6]))
    else:
        rep.skip('关键串全部命中', '未配置 must_contain')

    # ---- 11. 收录（列表 / 首页 / 作者主页）
    if args.no_lists:
        for nm in ('board 列表收录', '首页收录', '作者主页收录'):
            rep.skip(nm, '--no-lists')
    else:
        needle = '/bbs/%s/' % pid

        def in_page(u):
            try:
                s, t = fetch_text(u, timeout=args.timeout)
                return s, (needle in t)
            except Exception:
                return 0, False

        if meta['board_id']:
            bu = '%s/bbs/board/%s/' % (BASE, meta['board_id'])
            s, found = in_page(bu)
            rep.check(found, 'board 列表收录',
                      '/bbs/board/%s/ 已含本贴' % meta['board_id'],
                      '/bbs/board/%s/ 未含本贴（HTTP %s）' % (meta['board_id'], s))
        else:
            rep.skip('board 列表收录', '未知板块 id')

        s, found = in_page(BASE + '/')
        rep.check(found, '首页收录', '首页已含本贴',
                  '首页未含本贴（HTTP %s，检查 home 缓存是否清理）' % s)

        if meta['author_uid']:
            au = '%s/bbs/user/%s/' % (BASE, meta['author_uid'])
            s, found = in_page(au)
            rep.check(found, '作者主页收录',
                      '/bbs/user/%s/ 已含本贴' % meta['author_uid'],
                      '/bbs/user/%s/ 未含本贴（HTTP %s）' % (meta['author_uid'], s))
        else:
            rep.skip('作者主页收录', '未知作者 uid')

    # ---- 12. HTML 结构
    rep.check(body.count('<div') == body.count('</div>'), 'div 配对',
              '%d/%d' % (body.count('<div'), body.count('</div>')),
              'div 不配对：%d 开 / %d 闭' % (body.count('<div'), body.count('</div>')))

    verdict = rep.render()
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(rep.to_json(), ensure_ascii=False, indent=2), encoding='utf-8')
        print('结果已写入 %s' % args.json_out)
    return 0 if verdict == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
