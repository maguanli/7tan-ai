# -*- coding: utf-8 -*-
import io, sys, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymysql
conn = pymysql.connect(host='127.0.0.1', user='tanapp', password='r9wDeVjegCswFuxtmCztzpL3rGay',
                       database='7tan_cn', charset='utf8mb4', autocommit=True)
cur = conn.cursor()
cur.execute("SHOW INDEX FROM ll_lt")
names = set(r[2] for r in cur.fetchall())
if 'idx_ll_useid_id' in names:
    print('IDX=exists')
else:
    t0 = time.time()
    cur.execute("ALTER TABLE ll_lt ADD INDEX idx_ll_useid_id (ll_useid, id)")
    print('IDX=created %.2fs' % (time.time() - t0))
cur.execute("SHOW INDEX FROM ll_lt")
print('IDX_NOW=', 'idx_ll_useid_id' in set(r[2] for r in cur.fetchall()))
cur.execute("""
EXPLAIN SELECT t.id FROM ll_lt t
 WHERE t.ll_useid=1 AND t.id<>84008 AND IFNULL(t.ll_or,0)=0
 ORDER BY (t.ll_idd=18) DESC, t.id DESC LIMIT 6
""")
r = cur.fetchone()
print('PLAN table=%s type=%s key=%s rows=%s extra=%s' % (r[2], r[3], r[5], r[9], r[10]))
t0 = time.time()
for _ in range(20):
    cur.execute("""
    SELECT t.id, t.ll_biaoti, t.ll_idd, IFNULL(t.ll_rc,0), DATE_FORMAT(t.ll_time1,'%Y-%m-%d'), c.ll_title
      FROM ll_lt t LEFT JOIN ll_class c ON t.ll_idd=c.id
     WHERE t.ll_useid=1 AND t.id<>84008 AND IFNULL(t.ll_or,0)=0
     ORDER BY (t.ll_idd=18) DESC, t.id DESC LIMIT 6
    """)
    cur.fetchall()
print('PERF=20 次 %.1f ms' % ((time.time()-t0)*1000))
conn.close()
