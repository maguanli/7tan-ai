# -*- coding: utf-8 -*-
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymysql
conn = pymysql.connect(host='127.0.0.1', user='tanapp', password='r9wDeVjegCswFuxtmCztzpL3rGay',
                       database='7tan_cn', charset='utf8mb4')
cur = conn.cursor()
cur.execute("SHOW INDEX FROM ll_lt")
rows = cur.fetchall()
idx = {}
for r in rows:
    idx.setdefault(r[2], []).append(r[4])
for k, v in idx.items():
    print('  %-24s %s' % (k, v))
print()
print('[EXPLAIN 推荐位查询]')
cur.execute("""
EXPLAIN SELECT t.id FROM ll_lt t
 WHERE t.ll_useid=1 AND t.id<>84008 AND IFNULL(t.ll_or,0)=0
 ORDER BY (t.ll_idd=18) DESC, t.id DESC LIMIT 6
""")
for r in cur.fetchall():
    print('  ', r[:8])
print()
print('[实测耗时]')
import time
t0=time.time()
for _ in range(5):
    cur.execute("""
    SELECT t.id, t.ll_biaoti, t.ll_idd, IFNULL(t.ll_rc,0), DATE_FORMAT(t.ll_time1,'%Y-%m-%d')
      FROM ll_lt t
     WHERE t.ll_useid=1 AND t.id<>84008 AND IFNULL(t.ll_or,0)=0
     ORDER BY (t.ll_idd=18) DESC, t.id DESC LIMIT 6
    """)
    cur.fetchall()
print('  5 次查询 %.1f ms' % ((time.time()-t0)*1000))
conn.close()
