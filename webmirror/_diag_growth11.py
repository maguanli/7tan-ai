import os, re, json, random, collections, urllib.request

D = r'D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb'
q = os.path.join(D, '_mirror_queue.ndjson')
m = os.path.join(D, '_mirror_manifest.ndjson')

idpat = re.compile(r'/(id_[A-Za-z0-9]{12})\.html$')
queued = set()
with open(q, encoding='utf-8') as f:
    for l in f:
        l = l.rstrip('\n')
        if not l:
            continue
        p = l.split('\t')
        if len(p) >= 3 and p[1] == 'page':
            mt = idpat.search(p[2])
            if mt:
                queued.add(mt.group(1))

fetched = set()
with open(m, encoding='utf-8') as f:
    for l in f:
        try:
            o = json.loads(l)
        except Exception:
            continue
        mt = idpat.search(o.get('url', ''))
        if mt:
            fetched.add(mt.group(1))

pending_ids = sorted(queued - fetched)
print('queued', len(queued), 'fetched', len(fetched), 'pending', len(pending_ids))

random.seed(11)
sample = random.sample(pending_ids, min(30, len(pending_ids)))

def fetch(u, n=300000):
    req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
    r = urllib.request.urlopen(req, timeout=25)
    return r.status, r.read(n)

print('=== sample PENDING id pages (live fetch) ===')
buckets = collections.Counter()
ok_cn = 0
for name in sample:            # name already like id_XXXXXXXXXXXX
    u = 'http://youbian.293.net/%s.html' % name
    try:
        st, b = fetch(u)
        sz = len(b)
        has_cn = any(0x4e00 <= (b[i] << 8 | b[i + 1]) <= 0x9fff for i in range(0, min(len(b) - 1, 4000), 2)) if b else False
        bkt = ('empty133' if sz < 200 else '1k-5k' if sz < 5000 else '5k-20k' if sz < 20000 else '>=20k')
        buckets[bkt] += 1
        if has_cn:
            ok_cn += 1
        print('  %s status=%s size=%6d %s' % (name, st, sz, bkt))
    except Exception as e:
        print('  %s ERR %s' % (name, e))
print('buckets', buckets, 'cn_pages', ok_cn, '/', len(sample))

# also test that a fetched one reproduces
print('=== state file ===')
print(open(os.path.join(D, '_mirror_state.json'), encoding='utf-8').read()[:1500])
