# -*- coding: utf-8 -*-
"""检查数据目录与解密尝试"""
import sys, os, json, base64
sys.path.insert(0, '.')
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# 1. config.yaml storage
import yaml
cfg = yaml.safe_load(open('config/config.yaml', encoding='utf-8'))
print('storage.data_dir =', cfg.get('storage', {}).get('data_dir'))

cipher = 'gAAAAABqfGXAPalbMLQCXI9tsFAvO6jFBoCoDliQjeS6OZwtADohYysr2Bug'

# 2. 尝试文件 key
try:
    key = Path('data/.encryption_key').read_bytes()
    print('file key len:', len(key))
    print('file key:', key.decode()[:20] + '...')
    f = Fernet(key)
    print('file key decrypt:', f.decrypt(cipher.encode()).decode())
except Exception as e:
    print('file key decrypt FAILED:', type(e).__name__, e)

# 3. 尝试派生 key（machine_id + seed + salt）
try:
    from src.security.sec_config import get_encryption_seed
    seed = get_encryption_seed().decode('utf-8', 'ignore')
    print('seed:', seed[:20], '...')
except Exception as e:
    seed = ''
    print('sec_config import FAILED:', e)
salt = Path('data/.encryption_salt').read_bytes()
machine_id = os.environ.get('COMPUTERNAME', '7tan-editor')
kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480000)
derived = base64.urlsafe_b64encode(kdf.derive(f'{machine_id}::{seed}'.encode()))
print('derived key:', derived.decode()[:20] + '...')
try:
    print('derived decrypt:', Fernet(derived).decrypt(cipher.encode()).decode())
except Exception as e:
    print('derived decrypt FAILED:', type(e).__name__, e)
