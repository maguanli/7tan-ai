import os, re, collections, urllib.request

D = r'D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb'
q = os.path.join(D, '_mirror_queue.ndjson')

rows = []
with open(q, encoding='utf-8') as f:
    for l in f:
        l = l.rstrip('\n')
        if not l:
            continue
        p = l.split('\t')
        if len(p) >= 3:
            rows.append((p[0], p[1], p[2]))

pages = [r[2] for r in rows if r[1] == 'page']
print('total pages', len(pages))

pats = {
    'id_12char': re.compile(r'/id_[A-Za-z0-9]{12}\.html$'),
    'a_code': re.compile(r'/a_[a-z0-9_]+\.html$'),
    'quhao': re.compile(r'/quhao_[0-9a-z_]+\.html$'),
    'num6_or_pag': re.compile(r'/[0-9]{6}(_[0-9]+)?\.html$'),
}
cnt = collections.Counter()
for u in pages:
    for k, p in pats.items():
        if p.search(u):
            cnt[k] += 1
            break
    else:
        cnt['other'] += 1
print('category counts', cnt)

# analyze pagination segments
segpat = re.compile(r'/([a-z]+_[0-9]+|[0-9]{6})_([0-9]+)\.html$')
pageseg = collections.defaultdict(list)
for u in pages:
    m = segpat.search(u)
    if m:
        pageseg[m.group(1)].append(int(m.group(2)))
print('bases with pagination', len(pageseg))
allpg = [n for v in pageseg.values() for n in v]
print('pagination numbers: min %s max %s count %s' % (min(allpg), max(allpg), len(allpg)))
big = [n for n in allpg if n > 100]
print('page numbers > 100:', len(big), 'sample', sorted(set(big))[:20], '...', sorted(set(big))[-20:])
print('page numbers > 1000:', len([n for n in allpg if n > 1000]))
# how many per base
sizes = collections.Counter({k: len(v) for k, v in pageseg.items()})
print('per-base pagination counts (top)', sizes.most_common(10))
# bases of type a_ vs quhao_ vs 6-digit
tb = collections.Counter(k.split('_')[0] if '_' in k else 'num6' for k in pageseg)
print('base types', tb.most_common())

# fetch a deep pagination page to inspect its links
def fetch(u, n=400000):
    req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(req, timeout=25).read(n).decode('utf-8', 'ignore')

print('=== inspect deep pagination ===')
for u in ['http://youbian.293.net/a_110100_20.html', 'http://youbian.293.net/a_110100_5000.html']:
    t = fetch(u)
    pag = sorted(set(re.findall(r'href="([^"]*_\d+\.html)"', t)))
    ids = re.findall(r'id_([A-Za-z0-9]{12})', t)
    print(u, 'pagination links:', pag)
    print('   ids:', len(ids), ids[:4])
