# -*- coding: utf-8 -*-
import json, urllib.request, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/rdap+json, application/json',
            })
            r = urllib.request.urlopen(req, timeout=30, context=ctx)
            return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            print(f'  [{i+1}] fail: {type(e).__name__}: {e}')
    return None

print('='*60)
print('1) Verisign RDAP - 7tan.com')
d = fetch('https://rdap.verisign.com/com/v1/domain/7tan.com')
if d:
    print('  handle:', d.get('handle'))
    print('  status:', d.get('status'))
    for ev in d.get('events', []):
        print('  event:', ev.get('eventAction'), '=', ev.get('eventDate'))
    for ns in d.get('nameservers', []):
        print('  ns:', ns.get('ldhName'))
    for ent in d.get('entities', []):
        roles = ent.get('roles')
        v = ent.get('vcardArray')
        name = ''
        if v and len(v) > 1:
            for item in v[1]:
                if item[0] == 'fn':
                    name = item[3]
        print('  entity:', roles, name)

print()
print('='*60)
print('2) APNIC RDAP - 47.86.169.72')
d2 = fetch('https://rdap.apnic.net/ip/47.86.169.72')
if d2:
    print('  handle:', d2.get('handle'))
    print('  name  :', d2.get('name'))
    print('  country:', d2.get('country'))
    print('  start :', d2.get('startAddress'))
    print('  end   :', d2.get('endAddress'))
    print('  type  :', d2.get('type'))
    for rem in d2.get('remarks', []):
        print('  remark:', (rem.get('description') or [''])[0][:120])
    for ent in d2.get('entities', []):
        print('  entity roles:', ent.get('roles'), ent.get('handle'))
