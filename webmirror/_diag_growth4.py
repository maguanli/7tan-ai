import os, re, glob, collections, urllib.request, random

D = r'D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb'

def fetch(u, n=400000):
    req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0) Chrome/124.0'})
    return urllib.request.urlopen(req, timeout=20).read(n).decode('utf-8', 'ignore')

for u in ['http://youbian.293.net/robots.txt', 'http://youbian.293.net/sitemap.xml',
          'http://youbian.293.net/sitemap_index.xml', 'http://youbian.293.net/sitemap.txt']:
    try:
        t = fetch(u, 3000)
        print('=== OK', u, 'len', len(t))
        print(t[:800])
    except Exception as e:
        print('=== ERR', u, e)

# analyze local region listing pages
linkpat = re.compile(r'href\s*=\s*"([^"]+)"', re.I)
idpat = re.compile(r'id_[A-Za-z0-9]{12}\.html')
base = os.path.join(D, 'youbian.293.net')

def analyze(pattern, limit=8, label=''):
    files = glob.glob(os.path.join(base, pattern))
    print('--- pattern', pattern, 'count', len(files))
    for p in files[:limit]:
        html = open(p, 'rb').read().decode('utf-8', 'ignore')
        links = linkpat.findall(html)
        ids = [l for l in links if idpat.search(l)]
        print('  ', os.path.basename(p), 'size', len(html), 'links', len(links), 'idlinks', len(ids))

analyze('a_*.html')
analyze('quhao_*.html')
analyze('[0-9]*_[0-9]*.html')
analyze('[0-9]*.html')
