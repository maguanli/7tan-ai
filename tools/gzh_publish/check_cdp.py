# -*- coding: utf-8 -*-
"""检查常见CDP调试端口"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import urllib.request
import json

def check(port):
    url = 'http://127.0.0.1:%d/json' % port
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode('utf-8', errors='replace'))
            print('PORT %d OPEN, tabs: %d' % (port, len(data)))
            for t in data[:10]:
                print('  -', t.get('type'), '|', t.get('title', '')[:60], '|', t.get('url', '')[:80])
            return True
    except Exception as e:
        print('PORT %d closed: %s' % (port, str(e)[:80]))
        return False

def main():
    for port in [9222, 9223, 9224, 9225, 9333, 9515, 17889, 17891]:
        check(port)

if __name__ == '__main__':
    main()
