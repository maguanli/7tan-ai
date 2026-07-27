"""Diagnostic: test refresh token flow"""
import sys
sys.path.insert(0, 'src')

from src.security.token_store import load_token
from src.security.strings import get_api_url

print("=" * 50)
print("1. Token Status")
print("=" * 50)

token_data = load_token()
print(f"Type: {type(token_data)}")
print(f"Value: {str(token_data)[:500]}")

if token_data:
    if isinstance(token_data, dict):
        token = token_data.get('token', '')
        print(f"Token type: {type(token)}")
        print(f"Token value: {str(token)[:200]}")
    else:
        print(f"Unexpected type: {type(token_data)}")
