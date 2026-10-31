# -*- coding: utf-8 -*-
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymysql, json
conn = pymysql.connect(host='127.0.0.1', user='tanapp', password='r9wDeVjegCswFuxtmCztzpL3rGay',
                       database='7tan_cn', charset='utf8mb4')
cur = conn.cursor()
out = {}
# 只有 1 篇可见帖的作者
cur.execute("""
  SELECT ll_useid, COUNT(*) c, MIN(id) FROM ll_lt
   WHERE IFNULL(ll_or,0)=0 AND ll_useid>0
   GROUP BY ll_useid HAVING c=1 LIMIT 1
""")
out['single'] = cur.fetchone()
# 高产作者的一篇
cur.execute("SELECT id FROM ll_lt WHERE ll_useid=99901 AND IFNULL(ll_or,0)=0 ORDER BY id DESC LIMIT 1")
out['top_uid99901'] = cur.fetchone()
# 锁帖
cur.execute("SELECT id FROM ll_lt WHERE ll_lock=1 AND IFNULL(ll_or,0)=0 ORDER BY id DESC LIMIT 1")
out['locked'] = cur.fetchone()
# 匿名/useid=0 的帖
cur.execute("SELECT id FROM ll_lt WHERE ll_useid=0 AND IFNULL(ll_or,0)=0 ORDER BY id DESC LIMIT 1")
out['anon'] = cur.fetchone()
print('JSON=' + json.dumps(out, ensure_ascii=False, default=str))
conn.close()
