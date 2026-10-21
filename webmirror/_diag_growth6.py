import re, urllib.request, hashlib

def fetch(u, n=500000):
    req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0) Chrome/124.0'})
    r = urllib.request.urlopen(req, timeout=25)
    return r.status, r.read(n).decode('utf-8', 'ignore')

idpat = re.compile(r'id_([A-Za-z0-9]{12})\.html')

print('=== pagination validity test ===')
for base in ['a_110100', '010010', 'quhao_010']:
    for pg in ['1', '2', '5', '20', '50', '500', '5000']:
        u = 'http://youbian.293.net/%s_%s.html' % (base, pg)
        try:
            st, t = fetch(u)
            ids = [m.group(1) for m in idpat.finditer(t)]
            title = re.search(r'<title>(.*?)</title>', t, re.S)
            nonascii = sum(1 for c in t if ord(c) > 127)
            print('  %-22s status=%s size=%6d ids=%2d nonascii=%5d' % (base + '_' + pg, st, len(t), len(ids), nonascii))
        except Exception as e:
            print('  %-22s ERR %s' % (base + '_' + pg, e))

print('=== homepage ===')
try:
    st, t = fetch('http://youbian.293.net/')
    print('status', st, 'size', len(t))
    m = re.findall(r'([0-9]{3,})\s*(?:个|条|万)', t)
    print('number+unit found', m[:20])
except Exception as e:
    print('ERR', e)

print('=== random id probe (does arbitrary id yield real page?) ===')
import random, string
for _ in range(6):
    rid = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(12))
    u = 'http://youbian.293.net/id_%s.html' % rid
    try:
        st, t = fetch(u, 300000)
        title = re.search(r'<title>(.*?)</title>', t, re.S)
        has_cn = any('\u4e00' <= c <= '\u9fff' for c in t)
        print('  id_%s status=%s size=%6d hasCN=%s title=%s' % (rid, st, len(t), has_cn, (title.group(1)[:40] if title else 'NA')))
    except Exception as e:
        print('  id_%s ERR %s' % (rid, e))
