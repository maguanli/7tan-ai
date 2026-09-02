import json, urllib.request, urllib.error

def post(path, body):
    url = "http://127.0.0.1:18080" + path
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read().decode("utf-8", errors="replace")[:500]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")[:500]
    except Exception as e:
        return -1, str(e)

print("== /v1/chat/completions ==")
st, body = post("/v1/chat/completions", {"messages": [{"role": "user", "content": "你好，请用一句话介绍你自己。"}], "max_tokens": 100})
print(st, body)
