import os, re, glob, urllib.request

D = r'D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb\youbian.293.net'

def read_gbk(p):
    b = open(p, 'rb').read()
    for enc in ('utf-8', 'gbk', 'gb18030'):
        try:
            return b.decode(enc)
        except Exception:
            continue
    return b.decode('gbk', 'ignore')

for pat in ['id_0Ajw1q4DReJ7.html', '010010.html', 'a_110100.html', 'quhao_010.html']:
    p = os.path.join(D, pat)
    if not os.path.exists(p):
        cand = glob.glob(os.path.join(D, pat))
        if not cand:
            print('missing', pat); continue
        p = cand[0]
    t = read_gbk(p)
    title = re.search(r'<title>(.*?)</title>', t, re.S)
    desc = re.search(r'<meta\s+name="description"\s+content="(.*?)"', t, re.S)
    kw = re.search(r'<meta\s+name="keywords"\s+content="(.*?)"', t, re.S)
    h1 = re.search(r'<h1[^>]*>(.*?)</h1>', t, re.S)
    print('===', pat, 'size', len(t))
    print('  title:', title.group(1).strip()[:90] if title else 'NA')
    print('  desc :', (desc.group(1).strip()[:90] if desc else 'NA'))
    print('  kw   :', (kw.group(1).strip()[:90] if kw else 'NA'))
    print('  h1   :', (re.sub('<[^>]+>', '', h1.group(1)).strip()[:80] if h1 else 'NA'))
    # visible text sample
    body = re.sub(r'<script.*?</script>', '', t, flags=re.S)
    body = re.sub(r'<style.*?</style>', '', body, flags=re.S)
    body = re.sub(r'<[^>]+>', ' ', body)
    body = re.sub(r'\s+', ' ', body)
    print('  text :', body[:260])
