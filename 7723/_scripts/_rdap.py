# -*- coding: utf-8 -*-
import urllib.request, json, ssl, io
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
out = io.open(r'D:\7tan\7tanAI\7723\_scripts\_rdap.txt','w',encoding='utf-8')
for u in ['https://rdap.verisign.com/com/v1/domain/7tan.com',
          'https://rdap.verisign.com/com/v1/domain/7723.com']:
    try:
        req = urllib.request.Request(u, headers={'User-Agent':'Mozilla/5.0','Accept':'application/rdap+json'})
        j = json.loads(urllib.request.urlopen(req, timeout=30, context=ctx).read().decode('utf-8','ignore'))
        out.write('==== %s\n' % u)
        out.write('ldhName: %s\n' % j.get('ldhName'))
        for ev in j.get('events',[]):
            out.write('  event: %s %s\n' % (ev.get('eventAction'), ev.get('eventDate')))
        out.write('\n')
    except Exception as e:
        out.write('ERR %s %s\n' % (u, e))
out.close()
print('ok')
