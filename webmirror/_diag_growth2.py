import json, os, collections, re

D = r'D:\7tan\7tanAI\webmirror\downloads\20261011-063926-4ba5eb'
q = os.path.join(D, '_mirror_queue.ndjson')
m = os.path.join(D, '_mirror_manifest.ndjson')

def tsv_rows(p):
    rows = []
    with open(p, encoding='utf-8') as f:
        for l in f:
            l = l.rstrip('\n')
            if not l:
                continue
            parts = l.split('\t')
            if len(parts) >= 3:
                rows.append(parts)
            else:
                rows.append([l])
    return rows

rows = tsv_rows(q)
print('queue rows', len(rows))
types = collections.Counter(r[1] if len(r) >= 3 else '?' for r in rows)
print('types', types.most_common())

pages = [r[2] for r in rows if len(r) >= 3 and r[1] == 'page']
assets = [r[2] for r in rows if len(r) >= 3 and r[1] == 'asset']
print('page urls', len(pages), 'unique', len(set(pages)))
print('asset urls', len(assets), 'unique', len(set(assets)))

idpat = re.compile(r'id_([A-Za-z0-9]+)\.html$')
ids = [idpat.search(u).group(1) for u in pages if idpat.search(u)]
print('id pages', len(ids))
print('id length dist', collections.Counter(len(i) for i in ids).most_common())
print('unique ids', len(set(ids)), 'unique lower', len(set(i.lower() for i in ids)))

# depth dist for pages
dep = collections.Counter(r[0] for r in rows if len(r) >= 3 and r[1] == 'page')
print('depth dist', sorted(dep.items(), key=lambda x: int(x[0]))[:20])

# other page shapes
other = [u for u in pages if not idpat.search(u)]
print('non-id page urls', len(other), 'sample', other[:10])
os_shape = collections.Counter(re.sub(r'\d+', 'N', u.split('293.net', 1)[-1]) for u in other)
print('non-id shapes', os_shape.most_common(20))

# manifest
mrows = tsv_rows(m)
print('manifest rows', len(mrows))
print('manifest sample', mrows[:3])
