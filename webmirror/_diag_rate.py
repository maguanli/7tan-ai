import time, json, urllib.request

def api():
    with urllib.request.urlopen('http://127.0.0.1:8000/api/tasks/20261011-063926-4ba5eb', timeout=15) as r:
        return json.load(r)['task']['stats']

print('polling for 120s ...')
rows = []
t0 = time.time()
while time.time() - t0 < 120:
    s = api()
    rows.append((round(time.time() - t0, 1), s.get('pages_total'), s.get('pages_ok'),
                 s.get('queue_size'), s.get('visited'), round(s.get('speed_recent', 0), 2)))
    time.sleep(15)

for r in rows:
    print('t=%6.1fs pages_total=%d pages_ok=%d queue(pending)=%s visited=%s speed=%s' % r)

if len(rows) >= 2:
    dt = rows[-1][0] - rows[0][0]
    dvis = rows[-1][4] - rows[0][4]
    dque = (rows[-1][3] or 0) - (rows[0][3] or 0)
    print('---')
    print('over %.1fs: visited +%d, pending %+d' % (dt, dvis, dque))
    print('=> discovery rate = visited_delta + pending_delta = %d new URLs added' % (dvis + dque))
