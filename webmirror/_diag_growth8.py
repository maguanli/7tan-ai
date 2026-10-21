import os, json, re, collections

D = r'D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb'
m = os.path.join(D, '_mirror_manifest.ndjson')

sizes = collections.Counter()
statuses = collections.Counter()
id_lower = collections.Counter()
small = []
n = 0
idpages = 0
idpat = re.compile(r'/id_([A-Za-z0-9]{12})\.html$')

with open(m, encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        n += 1
        sz = o.get('size', -1)
        st = o.get('status', -1)
        statuses[st] += 1
        bucket = ('<200' if sz < 200 else '200-1k' if sz < 1000 else '1k-5k' if sz < 5000 else '5k-20k' if sz < 20000 else '>=20k')
        sizes[bucket] += 1
        u = o.get('url', '')
        mt = idpat.search(u)
        if mt:
            idpages += 1
            id_lower[mt.group(1).lower()] += 1
        if sz < 200:
            small.append((sz, st, u))

print('manifest rows', n, 'id pages', idpages)
print('statuses', statuses.most_common())
print('size buckets', sizes.most_common())
print('empty/small pages (<200B)', len(small))
print('  sample', small[:8])

dups = sum(1 for k, v in id_lower.items() if v > 1)
extra = sum(v - 1 for v in id_lower.values() if v > 1)
print('id lower-dup groups', dups, 'extra records', extra)
print('unique id lower', len(id_lower))
