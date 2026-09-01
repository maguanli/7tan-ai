# -*- coding: utf-8 -*-
"""顺序下载 Wikimedia Commons 图片（带浏览器UA + 间隔，避免限流）"""
import requests, time, os

DEST = r'data/gzh_render/塞班游戏站捡漏'
os.makedirs(DEST, exist_ok=True)

FILES = [
    ('https://upload.wikimedia.org/wikipedia/commons/1/17/Playing_with_smartphone.jpg', 'img3_play_game.jpg'),
    ('https://upload.wikimedia.org/wikipedia/commons/a/ab/Business_agreement_handshake_at_coffee_shop.jpg', 'img4_handshake.jpg'),
    ('https://upload.wikimedia.org/wikipedia/commons/f/f3/Digital_nomad_telecommuting_work_on_laptop_computer.jpg', 'img5_laptop.jpg'),
    ('https://upload.wikimedia.org/wikipedia/commons/1/1f/StrappedCurrency.jpg', 'img6_money.jpg'),
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
}

for url, name in FILES:
    try:
        r = requests.get(url, headers=HEADERS, timeout=40)
        if r.status_code == 200:
            path = os.path.join(DEST, name)
            with open(path, 'wb') as f:
                f.write(r.content)
            print('OK', name, len(r.content), 'bytes')
        else:
            print('FAIL', name, 'HTTP', r.status_code)
    except Exception as e:
        print('ERR', name, repr(e))
    time.sleep(10)

print('DONE')
