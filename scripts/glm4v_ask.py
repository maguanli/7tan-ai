# -*- coding: utf-8 -*-
"""调用 GLM-4V 视觉大模型分析截图"""
import sys, os, base64, json, urllib.request
sys.stdout.reconfigure(encoding='utf-8')

img_path = sys.argv[1] if len(sys.argv) > 1 else 'data/screenshots/wechat_after_click.png'
question = sys.argv[2] if len(sys.argv) > 2 else '请描述这张屏幕截图中微信窗口的位置和布局，微信聊天输入框在什么位置(像素坐标)。'

api_key = os.environ.get('VISION_API_KEY') or os.environ.get('GLM_API_KEY') or os.environ.get('ZHIPU_API_KEY', '')
if not api_key:
    # 尝试从配置读取
    for cfg in ['config.yaml', 'config.yml']:
        if os.path.exists(cfg):
            import yaml
            with open(cfg, encoding='utf-8') as f:
                data = yaml.safe_load(f)
            for k in ('VISION_API_KEY', 'vision_api_key', 'api_key'):
                if k in (data or {}):
                    api_key = str(data[k])
                    break
            if api_key:
                break
print('api_key found:', bool(api_key))

with open(img_path, 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()

payload = {
    "model": "glm-4v-flash",
    "messages": [{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            {"type": "text", "text": question}
        ]
    }]
}

req = urllib.request.Request(
    'https://open.bigmodel.cn/api/paas/v4/chat/completions',
    data=json.dumps(payload).encode(),
    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
)
try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    print('RESPONSE:', data['choices'][0]['message']['content'])
except Exception as e:
    print('ERR:', e)
    try:
        print(e.read().decode() if hasattr(e, 'read') else '')
    except Exception:
        pass
