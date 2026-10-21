import os, re, json, random, collections, urllib.request

D = r'D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb'
print('=== dir listing ===')
for fn in sorted(os.listdir(D)):
    p = os.path.join(D, fn)
    if os.path.isfile(p):
        print('  %-34s %12d' % (fn, os.path.getsize(p)))

q = os.path.join(D, '_mirror_queue.ndjson')
m = os.path.join(D, '_mirror_manifest.ndjson')

idpat = re.compile(r'/(id_[A-Za-z0-9]{12})\.html$')
queued = set()
raw = []
with open(q, encoding='utf-8') as f:
    for l in f:
        l = l.rstrip('\n')
        if not l:
            continue
        p = l.split('\t')
        if len(p) >= 3 and p[1] == 'page':
            raw.append(p[2])
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

pending_ids = list(queued - fetched)
print('queued id', len(queued), 'fetched id', len(fetched), 'pending id', len(pending_ids))

random.seed(7)
sample = random.sample(pending_ids, min(25, len(pending_ids)))

def fetch(u, n=300000):
    req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
    r = urllib.request.urlopen(req, timeout=25)
    return r.status, r.read(n)

print('=== sample PENDING id pages (fetch live) ===')
buckets = collections.Counter()
for sid in sample:
    u = 'http://youbian.293.net/id_%s.html' % sid
    try:
        st, b = fetch(u)
        sz = len(b)
        bkt = ('empty<200' if sz < 200 else '1k-5k' if sz < 5000 else '5k-20k' if sz < 20000 else '>=20k')
        buckets[bkt] += 1
        print('  id_%s status=%s size=%6d %s' % (sid, st, sz, bkt))
    except Exception as e:
        print('  id_%s ERR %s' % (sid, e))
print('buckets', buckets)
