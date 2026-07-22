"""
HTTP 客户端插件 — 发送 API 请求、测试接口、查看响应
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool
import json as _json


@register_tool(
    name="http_request",
    description="发送 HTTP 请求（GET/POST/PUT/DELETE/PATCH），支持 JSON、Header、认证。用于测试 API 接口。",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "请求 URL"},
            "method": {"type": "string", "description": "HTTP 方法: GET/POST/PUT/DELETE/PATCH", "default": "GET"},
            "headers": {"type": "string", "description": "JSON 格式的请求头，如 '{\"Authorization\":\"Bearer xxx\"}'", "default": "{}"},
            "body": {"type": "string", "description": "请求体（JSON 字符串）", "default": ""},
            "timeout": {"type": "integer", "description": "超时秒数", "default": 30},
        },
        "required": ["url"]
    },
    category="api"
)
def http_request(url: str, method: str = "GET", headers: str = "{}",
                 body: str = "", timeout: int = 30) -> str:
    """发送 HTTP 请求"""
    import urllib.request
    import urllib.error

    method = method.upper()
    if method not in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"):
        return f"不支持的 HTTP 方法: {method}"

    try:
        hdrs = _json.loads(headers) if headers else {}
    except _json.JSONDecodeError:
        return f"Headers JSON 解析失败: {headers[:100]}"

    try:
        data = body.encode("utf-8") if body else None
        req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            resp_headers = dict(resp.headers)
            resp_body = resp.read().decode("utf-8", errors="replace")

        result = [f"📡 {method} {url}"]
        result.append(f"   状态: {status}")
        result.append(f"   响应头: {_json.dumps(dict(list(resp_headers.items())[:5]), ensure_ascii=False, indent=2)}")

        # 尝试格式化 JSON
        try:
            parsed = _json.loads(resp_body)
            result.append(f"\n📦 响应体 ({len(resp_body)} bytes, JSON):")
            result.append(_json.dumps(parsed, ensure_ascii=False, indent=2)[:2000])
        except (_json.JSONDecodeError, ValueError):
            result.append(f"\n📦 响应体 ({len(resp_body)} bytes):")
            result.append(resp_body[:1500])

        if len(resp_body) > 2000:
            result.append(f"\n... 响应被截断 (共 {len(resp_body)} bytes)")
        return "\n".join(result)

    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")[:500] if e.fp else ""
        return f"❌ HTTP {e.code}: {e.reason}\n{err_body}"
    except urllib.error.URLError as e:
        return f"❌ 连接失败: {e.reason}"
    except Exception as e:
        return f"❌ 请求失败: {e}"


@register_tool(
    name="test_api_endpoint",
    description="快速测试 API 端点：发送常见 HTTP 方法组合，报告每个请求的状态码和响应时间。",
    parameters={
        "type": "object",
        "properties": {
            "base_url": {"type": "string", "description": "API 基础 URL，如 http://localhost:9800"},
            "endpoints": {"type": "string", "description": "测试端点列表（逗号分隔），如 /api/health,/api/version", "default": "/api/health"},
        },
        "required": ["base_url"]
    },
    category="api"
)
def test_api_endpoint(base_url: str, endpoints: str = "/api/health") -> str:
    """测试 API 端点"""
    import urllib.request
    import time as _time

    eps = [e.strip() for e in endpoints.split(",") if e.strip()]
    results = [f"🧪 API 测试: {base_url}\n"]

    for ep in eps:
        full_url = base_url.rstrip("/") + "/" + ep.lstrip("/")
        start = _time.time()
        try:
            req = urllib.request.Request(full_url, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                elapsed = (_time.time() - start) * 1000
                results.append(f"  ✅ {ep:30s} → {resp.status} ({elapsed:.0f}ms)")
        except urllib.error.HTTPError as e:
            elapsed = (_time.time() - start) * 1000
            results.append(f"  ⚠️ {ep:30s} → {e.code} ({elapsed:.0f}ms)")
        except urllib.error.URLError:
            results.append(f"  ❌ {ep:30s} → 无法连接")
        except Exception as e:
            results.append(f"  ❌ {ep:30s} → {e}")

    return "\n".join(results)


@register_tool(
    name="openapi_explore",
    description="读取并解析 OpenAPI/Swagger 文档，列出所有可用 API 端点及其方法和参数。",
    parameters={
        "type": "object",
        "properties": {
            "spec_url": {"type": "string", "description": "OpenAPI JSON/YAML 文档 URL 或文件路径"},
        },
        "required": ["spec_url"]
    },
    category="api"
)
def openapi_explore(spec_url: str) -> str:
    """解析 OpenAPI 文档"""
    import urllib.request

    # 读取文档
    try:
        if spec_url.startswith("http"):
            with urllib.request.urlopen(spec_url, timeout=15) as resp:
                content = resp.read().decode("utf-8")
        elif os.path.exists(spec_url):
            with open(spec_url, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            return f"无法访问: {spec_url}"
    except Exception as e:
        return f"读取失败: {e}"

    try:
        spec = _json.loads(content)
    except _json.JSONDecodeError:
        # 尝试 YAML
        try:
            import yaml
            spec = yaml.safe_load(content)
        except ImportError:
            return "请安装 pyyaml: pip install pyyaml"
        except Exception:
            return "无法解析文档（非 JSON/YAML）"

    title = spec.get("info", {}).get("title", "Unknown")
    version = spec.get("info", {}).get("version", "?")
    paths = spec.get("paths", {})

    results = [f"📖 {title} v{version}"]
    results.append(f"   API 端点: {len(paths)} 个\n")

    for path, methods in sorted(paths.items()):
        for method in ["get", "post", "put", "delete", "patch"]:
            if method in methods:
                op = methods[method]
                summary = op.get("summary", "")
                results.append(f"  {method.upper():7s} {path:35s} {summary}")

    return "\n".join(results[:80])


import os
