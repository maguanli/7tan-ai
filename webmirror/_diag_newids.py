import sys, re, json, os, random, collections, urllib.request
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

D = r'D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb'

print('=== report head ===')
try:
    t = open(os.path.join(D, '_mirror_report.txt'), encoding='utf-8', errors='replace').read()
    print(t[:1200])
except Exception as e:
    print('ERR', e)

# load queued ids + all listing urls
idpat = re.compile(r'/id_([A-Za-z0-9]{12})\.html$')
queued_ids = set()
listing = []
with open(os.path.join(D, '_mirror_queue.ndjson'), encoding='utf-8') as f:
    for l in f:
        l = l.rstrip('\n')
        if not l:
            continue
        p = l.split('\t')
        if len(p) >= 3 and p[1] == 'page':
            u = p[2]
            mt = idpat.search(u)
            if mt:
                queued_ids.add(mt.group(1).lower())
            else:
                listing.append(u)

# fetched set
fetched = set()
with open(os.path.join(D, '_mirror_manifest.ndjson'), encoding='utf-8') as f:
    for l in f:
        try:
            o = json.loads(l)
        except Exception:
            continue
        fetched.add(o.get('url', ''))

pending_listing = [u for u in listing if u not in fetched]
print('listing urls total', len(listing), 'pending listing', len(pending_listing))

random.seed(3)
sample = random.sample(pending_listing, min(20, len(pending_listing)))
print('=== sample pending LISTING pages: how many NEW ids do they expose? ===')
tot_new = 0
tot_ids = 0
for u in sample:
    try:
        req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req, timeout=25).read(400000).decode('utf-8', 'ignore')
        ids = [m.group(1).lower() for m in idpat.finditer(html) if True]
        ids = list(set(re.findall(r'id_([A-Za-z0-9]{12})\.html', html)))
        new = [i for i in ids if i.lower() not in queued_ids]
        tot_new += len(new)
        tot_ids += len(ids)
        print('  %-46s ids=%2d  new=%2d' % (u[:46], len(ids), len(new)))
    except Exception as e:
        print('  %-46s ERR %s' % (u[:46], e))
print('TOTAL ids_on_page=%d  brand_new=%d  (%.1f%% new)' % (tot_ids, tot_new, 100.0 * tot_new / max(1, tot_ids)))

# estimate: unique path-space size
print('=== id space stats ===')
print('queued unique ids(lower)', len(queued_ids))
