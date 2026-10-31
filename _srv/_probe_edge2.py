# -*- coding: utf-8 -*-
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymysql, json
conn = pymysql.connect(host='127.0.0.1', user='tanapp', password='r9wDeVjegCswFuxtmCztzpL3rGay',
                       database='7tan_cn', charset='utf8mb4')
cur = conn.cursor()
out = {}
cur.execute("""
  SELECT t.id, COUNT(h.id) c FROM ll_lt t JOIN ll_lthf h ON h.ll_id=t.id
   WHERE IFNULL(t.ll_or,0)=0 GROUP BY t.id HAVING c BETWEEN 3 AND 15 ORDER BY c DESC LIMIT 1
""")
out['some_replies'] = cur.fetchone()
cur.execute("""
  SELECT t.id, COUNT(h.id) c FROM ll_lt t JOIN ll_lthf h ON h.ll_id=t.id
   WHERE IFNULL(t.ll_or,0)=0 GROUP BY t.id HAVING c > 25 ORDER BY c DESC LIMIT 1
""")
out['many_replies'] = cur.fetchone()
print('JSON=' + json.dumps(out, ensure_ascii=False, default=str))
conn.close()
