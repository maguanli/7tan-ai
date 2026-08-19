# -*- coding: utf-8 -*-
"""解密 ai_configs 表中 pro/flash 的 api_key，用于配置 DeepSeek Harness"""
import sys, sqlite3
sys.path.insert(0, r'D:\7tan\7tanAI')
from src.database.db import decrypt_password

conn = sqlite3.connect(r'D:\7tan\7tanAI\data\games.db')
rows = conn.execute(
    "SELECT id, config_key, model, api_key, is_active FROM ai_configs "
    "WHERE model LIKE '%pro%' OR config_key LIKE '%pro%' OR model LIKE '%flash%'"
).fetchall()
for r in rows:
    print('ID:', r[0], '| key:', r[1], '| model:', r[2], '| active:', r[4], '| api_key_len:', len(r[3] or ''))
    if r[3]:
        try:
            dec = decrypt_password(r[3])
            print('  DECRYPTED:', dec)
        except Exception as e:
            print('  DECRYPT_ERR:', e)
