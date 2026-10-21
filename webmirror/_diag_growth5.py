import re, urllib.request, hashlib, collections, json, os

def fetch(u, n=500000):
    req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0) Chrome/124.0'})
    return urllib.request.urlopen(req, timeout=25).read(n).decode('utf-8', 'ignore')

linkpat = re.compile(r'href\s*=\s*"([^"]+)"', re.I)
idpat = re.compile(r'id_([A-Za-z0-9]{12})\.html')

tests = [
    'http://youbian.293.net/a_110100.html',
    'http://youbian.293.net/010010.html',
    'http://youbian.293.net/quhao_010.html',
]
for u in tests:
    try:
        a = fetch(u); b = fetch(u)
        la = [m.group(1) for m in idpat.finditer(a)]
        lb = [m.group(1) for m in idpat.finditer(b)]
        print('=== ', u)
        print('   hash_equal', hashlib.md5(a.encode()).hexdigest() == hashlib.md5(b.encode()).hexdigest())
        print('   run1 ids', len(la), 'unique', len(set(la)), 'run2 ids', len(lb), 'unique', len(set(lb)))
        print('   exact overlap', len(set(la) & set(lb)), '/', len(set(la) | set(lb)))
        print('   lower overlap', len(set(x.lower() for x in la) & set(x.lower() for x in lb)),
              '/', len(set(x.lower() for x in la) | set(x.lower() for x in lb)))
        print('   run1 sample', la[:6])
        print('   run2 sample', lb[:6])
        # pagination links
        pag = sorted(set(re.findall(r'href="([^"]*_\d+\.html)"', a)))[:12]
        print('   pagination sample', pag)
        # all links with page numbers
        nums = [int(x) for x in re.findall(r'_(\d+)\.html', a)]
        print('   page-number links max', max(nums) if nums else None, 'count', len(nums))
    except Exception as e:
        print('=== ERR', u, e)
