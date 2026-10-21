import os, re, glob, collections, urllib.request, hashlib

D = r'D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb'

# find a local crawled id_ page
cands = glob.glob(os.path.join(D, 'youbian.293.net', 'id_*.html'))
print('local id pages', len(cands))
if not cands:
    cands = glob.glob(os.path.join(D, '**', 'id_*.html'), recursive=True)
    print('deep id pages', len(cands))

sample = cands[:5]
linkpat = re.compile(r'href\s*=\s*"([^"]+)"', re.I)
idpat = re.compile(r'id_[A-Za-z0-9]{12}\.html')

for p in sample:
    html = open(p, 'rb').read().decode('utf-8', 'ignore')
    links = linkpat.findall(html)
    ids = [l for l in links if idpat.search(l)]
    title = re.search(r'<title>(.*?)</title>', html, re.S)
    print('---', os.path.basename(p), 'size', len(html))
    print('   title:', (title.group(1).strip()[:60] if title else 'NA'))
    print('   total links', len(links), 'id links', len(ids), 'unique id links', len(set(ids)))
    print('   sample ids', [l.split('/')[-1] for l in ids[:5]])

# decisive test: fetch same URL twice, compare outbound link sets
print('=== fetch-twice test ===')
test_urls = []
for p in sample[:2]:
    nm = os.path.basename(p)
    test_urls.append('http://youbian.293.net/' + nm)
if not test_urls:
    test_urls = ['http://youbian.293.net/id_nX3YdvZqLRVN.html']

def fetch(u):
    req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(req, timeout=20).read().decode('utf-8', 'ignore')

for u in test_urls:
    try:
        a = fetch(u)
        b = fetch(u)
        la = set(l for l in linkpat.findall(a) if idpat.search(l))
        lb = set(l for l in linkpat.findall(b) if idpat.search(l))
        print('url', u)
        print('  hash_equal', hashlib.md5(a.encode()).hexdigest() == hashlib.md5(b.encode()).hexdigest())
        print('  ids_run1', len(la), 'ids_run2', len(lb), 'overlap', len(la & lb))
        print('  sample run1', [x.split('/')[-1] for x in list(la)[:5]])
        print('  sample run2', [x.split('/')[-1] for x in list(lb)[:5]])
    except Exception as e:
        print('url', u, 'ERR', e)
